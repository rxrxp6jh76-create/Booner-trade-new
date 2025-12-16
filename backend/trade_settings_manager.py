"""
Trade Settings Manager
Wendet globale Settings auf offene Trades an und überwacht diese
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from database import trading_settings, trade_settings

logger = logging.getLogger(__name__)


class TradeSettingsManager:
    """Verwaltet und überwacht Trade Settings"""
    
    def __init__(self):
        self.running = False
        self.monitor_interval = 10  # Sekunden
        self._last_market_closed_log = {}  # Track wann wir zuletzt "Market closed" geloggt haben
    
    def _is_market_likely_open(self) -> bool:
        """
        Einfacher Check ob Märkte wahrscheinlich geöffnet sind.
        Forex/CFD Märkte sind typischerweise:
        - Montag 00:00 bis Freitag 23:00 UTC (mit Pausen am Wochenende)
        - Täglich ca. 00:00-23:00 UTC
        
        Returns: True wenn wahrscheinlich offen, False wenn sicher geschlossen
        """
        now = datetime.now(timezone.utc)
        
        # Wochenende Check (Samstag = 5, Sonntag = 6)
        if now.weekday() in [5, 6]:
            return False
        
        # Freitag Abend nach 22:00 UTC - Märkte schließen
        if now.weekday() == 4 and now.hour >= 22:
            return False
        
        # Sonntag Abend vor 22:00 UTC - Märkte noch nicht offen
        if now.weekday() == 6 and now.hour < 22:
            return False
        
        return True
    
    async def apply_global_settings_to_trade(
        self, 
        trade: Dict, 
        global_settings: Dict
    ) -> Dict:
        """
        Berechnet SL/TP für einen Trade basierend auf globalen Settings
        """
        # WICHTIG: MT5 verwendet 'price_open' als Entry Price!
        entry_price = trade.get('price_open') or trade.get('entry_price') or trade.get('price')
        if not entry_price:
            logger.warning(f"No entry price for trade {trade.get('ticket')}")
            return {}
        
        # MT5 Type ist "POSITION_TYPE_BUY" oder "POSITION_TYPE_SELL"
        trade_type_raw = trade.get('type', 'BUY')
        if 'BUY' in str(trade_type_raw).upper():
            trade_type = 'BUY'
        elif 'SELL' in str(trade_type_raw).upper():
            trade_type = 'SELL'
        else:
            trade_type = 'BUY'  # Fallback
        
        # Für bestehende Trades: Prüfe globale Trading-Strategie
        # (KI entscheidet bei neuen Trades selbst)
        trading_strategy = global_settings.get('trading_strategy', 'CONSERVATIVE')
        
        if trading_strategy == 'SCALPING':
            strategy = self._get_scalping_strategy(global_settings)
        else:
            # Default: Day Trading für bestehende Trades
            strategy = self._get_day_trading_strategy(global_settings)
        
        if not strategy:
            logger.warning(f"No strategy found for trade {trade.get('ticket')}")
            return {}
        
        # Berechne SL/TP basierend auf Modus (Prozent ODER Euro)
        sl_mode = strategy.get('stop_loss_mode', 'percent')  # 'percent' oder 'euro'
        tp_mode = strategy.get('take_profit_mode', 'percent')  # 'percent' oder 'euro'
        
        # Stop Loss Berechnung
        if sl_mode == 'euro':
            sl_euro = strategy.get('stop_loss_euro', 2.0)
            # Bei 2 Euro Verlust: Entry - 2 EUR für BUY, Entry + 2 EUR für SELL
            if trade_type == 'BUY':
                stop_loss = entry_price - sl_euro
            else:  # SELL
                stop_loss = entry_price + sl_euro
        else:  # percent
            sl_percent = strategy.get('stop_loss_percent', 2.0)
            if trade_type == 'BUY':
                stop_loss = entry_price * (1 - sl_percent / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + sl_percent / 100)
        
        # Take Profit Berechnung
        if tp_mode == 'euro':
            tp_euro = strategy.get('take_profit_euro', 2.0)
            # Bei 2 Euro Gewinn: Entry + 2 EUR für BUY, Entry - 2 EUR für SELL
            if trade_type == 'BUY':
                take_profit = entry_price + tp_euro
            else:  # SELL
                take_profit = entry_price - tp_euro
        else:  # percent
            tp_percent = strategy.get('take_profit_percent', 2.0)  # 🐛 FIX: Default von 1.0 auf 2.0 erhöht
            if trade_type == 'BUY':
                take_profit = entry_price * (1 + tp_percent / 100)
            else:  # SELL
                take_profit = entry_price * (1 - tp_percent / 100)
        
        settings = {
            'trade_id': f"mt5_{trade['ticket']}",
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'trailing_stop': strategy.get('trailing_stop', False),
            'trailing_distance': strategy.get('trailing_distance', 50.0),
            'max_loss_percent': sl_percent,
            'strategy': strategy.get('name', 'swing'),
            'entry_price': entry_price,
            'trade_type': trade_type,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Calculated settings for {trade['ticket']}: SL={stop_loss:.2f}, TP={take_profit:.2f}")
        
        return settings
    
    def _get_day_trading_strategy(self, global_settings: Dict) -> Dict:
        """
        Holt Day Trading Settings aus globalen Settings
        Für bestehende offene Trades: IMMER Day Trading verwenden!
        """
        # Day Trading Settings mit Support für Prozent UND Euro Modus
        return {
            'name': 'day',
            'stop_loss_mode': global_settings.get('day_sl_mode', 'percent'),  # 'percent' oder 'euro'
            'stop_loss_percent': global_settings.get('day_stop_loss_percent', 2.0),  # 🐛 FIX: Default von 1.0 auf 2.0
            'stop_loss_euro': global_settings.get('day_stop_loss_euro', 15.0),  # Default €15
            'take_profit_mode': global_settings.get('day_tp_mode', 'percent'),  # 'percent' oder 'euro'
            'take_profit_percent': global_settings.get('day_take_profit_percent', 2.5),  # 🐛 FIX: Default von 0.5 auf 2.5
            'take_profit_euro': global_settings.get('day_take_profit_euro', 30.0),  # Default €30
            'trailing_stop': global_settings.get('day_trailing_stop', False),
            'trailing_distance': global_settings.get('day_trailing_distance', 30.0)
        }
    
    def _get_scalping_strategy(self, global_settings: Dict) -> Dict:
        """
        Holt Scalping Trading Settings aus globalen Settings
        Scalping: Ultra-schnelle Trades mit sehr engen TP/SL
        """
        return {
            'name': 'scalping',
            'stop_loss_mode': 'percent',  # Scalping nutzt immer Prozent
            'stop_loss_percent': 0.08,  # 0.08% = 8 Pips (sehr eng)
            'take_profit_percent': 0.15,  # 0.15% = 15 Pips (schneller Gewinn)
            'trailing_stop': False,  # Kein Trailing bei Scalping
            'max_holding_time': 300,  # 5 Minuten max
            'min_confidence': 0.6  # Höhere Mindest-Confidence
        }
    
    def _determine_strategy(self, trade: Dict, global_settings: Dict) -> Optional[Dict]:
        """
        HINWEIS: Diese Methode wird NUR von der KI bei NEUEN Trades verwendet!
        Für bestehende Trades verwenden wir immer _get_day_trading_strategy()
        
        Die KI entscheidet selbst welche Strategie sie verwendet:
        - Scalping: Ultra-schnelle Trades, sehr enge TP/SL (5-20 Pips)
        - Day Trading: Schnelle Trades, kleinere SL/TP
        - Swing Trading: Längere Haltedauer, größere SL/TP
        """
        # Diese Logik kann die KI später selbst implementieren
        # basierend auf Marktbedingungen, Volatilität, etc.
        
        # Prüfe globale Trading-Strategie
        trading_strategy = global_settings.get('trading_strategy', 'CONSERVATIVE')
        
        # Wenn SCALPING Strategie gewählt ist
        if trading_strategy == 'SCALPING':
            return self._get_scalping_strategy(global_settings)
        
        # Prüfe ob Day Trading aktiviert ist (Default für neue Trades)
        if global_settings.get('day_trading_enabled'):
            return self._get_day_trading_strategy(global_settings)
        
        # Prüfe ob Swing Trading aktiviert ist
        if global_settings.get('swing_trading_enabled'):
            return {
                'name': 'swing',
                'stop_loss_percent': global_settings.get('swing_stop_loss_percent', 2.0),
                'take_profit_percent': global_settings.get('swing_take_profit_percent', 4.0),  # 🐛 FIX: Default von 1.0 auf 4.0
                'trailing_stop': global_settings.get('swing_trailing_stop', False),
                'trailing_distance': global_settings.get('swing_trailing_distance', 50.0)
            }
        
        # Fallback: Day Trading Default
        return {
            'name': 'day',
            'stop_loss_percent': 2.0,  # 🐛 FIX: Default von 1.0 auf 2.0
            'take_profit_percent': 2.5,  # 🐛 FIX: Default von 0.5 auf 2.5
            'trailing_stop': False,
            'trailing_distance': 30.0
        }
    
    async def sync_all_trades_with_settings(self, open_positions: List[Dict]):
        """
        Wendet Settings auf ALLE offenen Trades an
        """
        try:
            # Hole globale Settings
            global_settings = await trading_settings.find_one({"id": "trading_settings"})
            if not global_settings:
                logger.warning("No global settings found")
                return
            
            logger.info(f"🔄 Syncing settings for {len(open_positions)} trades...")
            
            synced_count = 0
            for trade in open_positions:
                try:
                    trade_id = f"mt5_{trade['ticket']}"
                    
                    # Prüfe ob Settings bereits existieren
                    existing = await trade_settings.find_one({"trade_id": trade_id})
                    
                    if not existing:
                        # Berechne neue Settings
                        new_settings = await self.apply_global_settings_to_trade(
                            trade, 
                            global_settings
                        )
                        
                        if new_settings:
                            # Speichere in DB
                            await trade_settings.insert_one(new_settings)
                            synced_count += 1
                            logger.info(f"✅ Created settings for trade {trade['ticket']}")
                    else:
                        # Settings existieren bereits
                        # WICHTIG: Respektiere user-defined Strategie!
                        # Überschreibe NICHT wenn Settings manuell gesetzt wurden
                        pass
                        
                except Exception as e:
                    logger.error(f"Error syncing trade {trade.get('ticket')}: {e}")
            
            logger.info(f"✅ Synced {synced_count}/{len(open_positions)} trades")
            
        except Exception as e:
            logger.error(f"Error in sync_all_trades_with_settings: {e}", exc_info=True)
    
    async def monitor_trades(self):
        """
        Überwacht alle offenen Trades und prüft SL/TP Bedingungen
        """
        logger.info("🤖 Trade Settings Monitor gestartet")
        
        while self.running:
            try:
                # Hole alle offenen Positionen von ALLEN Plattformen
                from multi_platform_connector import multi_platform
                
                all_positions = []
                
                # Hole Positionen von jeder aktiven Plattform
                for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                    try:
                        positions = await multi_platform.get_open_positions(platform_name)
                        if positions:
                            # Füge Platform-Info hinzu
                            for pos in positions:
                                pos['platform'] = platform_name
                            all_positions.extend(positions)
                            logger.debug(f"✅ Loaded {len(positions)} positions from {platform_name}")
                    except Exception as e:
                        logger.warning(f"Could not get positions from {platform_name}: {e}")
                
                if not all_positions:
                    await asyncio.sleep(self.monitor_interval)
                    continue
                
                # Sync Settings für neue Trades
                await self.sync_all_trades_with_settings(all_positions)
                
                # Überwache jeden Trade
                logger.info(f"🔍 Checking {len(all_positions)} trades for SL/TP...")
                checked_count = 0
                for trade in all_positions:
                    await self._check_trade_conditions(trade)
                    checked_count += 1
                logger.info(f"✅ Checked {checked_count} trades")
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
            
            await asyncio.sleep(self.monitor_interval)
    
    async def _check_trade_conditions(self, trade: Dict):
        """
        Prüft ob ein Trade geschlossen werden sollte
        """
        try:
            ticket = trade.get('ticket')
            if not ticket:
                return
                
            trade_id = f"mt5_{ticket}"
            
            # Hole Settings für diesen Trade
            settings = await trade_settings.find_one({"trade_id": trade_id})
            
            if not settings:
                # Nur für EURUSD loggen (Debug)
                if trade.get('symbol') == 'EURUSD':
                    logger.warning(f"⚠️ No settings found for EURUSD trade {ticket}")
                return
            
            # MT5 gibt price_current zurück, nicht price!
            current_price = trade.get('price_current') or trade.get('price')
            if not current_price:
                if trade.get('symbol') == 'EURUSD':
                    logger.warning(f"⚠️ No price for EURUSD trade {ticket}, trade data: {trade}")
                return
            
            stop_loss = settings.get('stop_loss')
            take_profit = settings.get('take_profit')
            # MT5 Type: "POSITION_TYPE_BUY" oder "POSITION_TYPE_SELL"
            trade_type_raw = str(trade.get('type', 'BUY')).upper()
            trade_type = 'BUY' if 'BUY' in trade_type_raw else 'SELL'
            
            # Stop Loss Check
            if stop_loss:
                if trade_type == 'BUY' and current_price <= stop_loss:
                    logger.warning(f"🛑 SL Hit for {trade['ticket']}: {current_price} <= {stop_loss}")
                    await self._close_trade(trade, "STOP_LOSS")
                    return
                elif trade_type == 'SELL' and current_price >= stop_loss:
                    logger.warning(f"🛑 SL Hit for {trade['ticket']}: {current_price} >= {stop_loss}")
                    await self._close_trade(trade, "STOP_LOSS")
                    return
            
            # Take Profit Check
            if take_profit:
                if trade_type == 'BUY' and current_price >= take_profit:
                    logger.warning(f"🎯 TP Hit for {trade['ticket']}: {current_price} >= {take_profit}")
                    await self._close_trade(trade, "TAKE_PROFIT")
                    return
                elif trade_type == 'SELL' and current_price <= take_profit:
                    logger.warning(f"🎯 TP Hit for {trade['ticket']}: {current_price} <= {take_profit}")
                    await self._close_trade(trade, "TAKE_PROFIT")
                    return
                # Debug: Log wenn TP vorhanden aber nicht erreicht (nur für EURUSD)
                elif trade.get('symbol') == 'EURUSD':
                    logger.debug(f"💤 EURUSD Trade {trade['ticket']}: Type={trade_type}, Price={current_price}, TP={take_profit} - Not hit yet")
            
            # Trailing Stop Logic (optional - hier implementieren wenn gewünscht)
            
        except Exception as e:
            logger.error(f"Error checking trade {trade.get('ticket')}: {e}")
    
    async def _close_trade(self, trade: Dict, reason: str):
        """
        Schließt einen Trade auf MT5
        """
        try:
            from multi_platform_connector import multi_platform
            
            platform = trade.get('platform', 'MT5_LIBERTEX_DEMO')
            ticket = trade['ticket']
            
            # Prüfe ob Markt wahrscheinlich geöffnet ist
            if not self._is_market_likely_open():
                # Logge nur einmal pro Stunde, um Log-Spam zu vermeiden
                now = datetime.now(timezone.utc)
                last_log_key = f"{ticket}_{reason}"
                last_log_time = self._last_market_closed_log.get(last_log_key)
                
                if not last_log_time or (now - last_log_time).total_seconds() > 3600:
                    logger.info(f"⏸️ Trade {ticket} SL/TP erreicht ({reason}), aber Markt ist geschlossen - wird beim nächsten Öffnen geschlossen")
                    self._last_market_closed_log[last_log_key] = now
                
                return  # Nicht versuchen zu schließen
            
            logger.info(f"🔴 Closing trade {ticket} on {platform} - Reason: {reason}")
            
            # Schließe Position auf MT5
            success = await multi_platform.close_position(platform, ticket)
            
            if success:
                logger.info(f"✅ Trade {ticket} closed successfully")
                
                # Speichere in DB als CLOSED
                await self._save_closed_trade(trade, reason)
            else:
                logger.warning(f"⚠️ Failed to close trade {ticket} - Market might be closed")
                
        except Exception as e:
            # Spezielle Behandlung für "Market is closed" Fehler
            error_msg = str(e).lower()
            if 'market' in error_msg and 'closed' in error_msg:
                # Nur warnen, nicht als Fehler loggen (vermeidet Log-Spam)
                logger.warning(f"⏸️ Trade {ticket} kann nicht geschlossen werden - Markt geschlossen (wird beim nächsten Öffnen geschlossen)")
            else:
                logger.error(f"Error closing trade {trade.get('ticket')}: {e}", exc_info=True)
    
    async def _save_closed_trade(self, trade: Dict, reason: str):
        """
        Speichert einen geschlossenen Trade in der Datenbank
        """
        try:
            from database import trades as trades_collection
            
            # Hole die Settings um Entry Price zu bekommen
            trade_id = f"mt5_{trade['ticket']}"
            settings = await trade_settings.find_one({"trade_id": trade_id})
            
            # Berechne entry_price
            entry_price = trade.get('price_open') or trade.get('entry_price')
            if settings and not entry_price:
                entry_price = settings.get('entry_price')
            
            # Berechne exit_price (aktueller Preis)
            exit_price = trade.get('price_current') or trade.get('price')
            
            # Berechne profit/loss
            profit = trade.get('profit', 0.0)
            
            # Trade Type
            trade_type_raw = str(trade.get('type', 'BUY')).upper()
            trade_type = 'BUY' if 'BUY' in trade_type_raw else 'SELL'
            
            # Symbol -> Commodity mapping
            symbol = trade.get('symbol', '')
            commodity_map = {
                'XAUUSD': 'GOLD',
                'XAGUSD': 'SILVER', 
                'XPTUSD': 'PLATINUM',
                'XPDUSD': 'PALLADIUM',
                'WTI': 'WTI_CRUDE',
                'BRENT': 'BRENT_CRUDE',
                'NATGAS': 'NATURAL_GAS',
                'WHEAT': 'WHEAT',
                'CORN': 'CORN',
                'SOYBEAN': 'SOYBEANS',
                'COFFEE': 'COFFEE',
                'SUGAR': 'SUGAR',
                'COCOA': 'COCOA',
                'EURUSD': 'EURUSD',
                'BTCUSD': 'BITCOIN'
            }
            
            commodity = commodity_map.get(symbol, symbol)
            
            closed_trade = {
                'id': trade_id,
                'mt5_ticket': str(trade['ticket']),
                'commodity': commodity,
                'type': trade_type,
                'entry_price': entry_price or 0.0,
                'exit_price': exit_price or 0.0,
                'volume': trade.get('volume', 0.01),
                'profit_loss': profit,
                'status': 'CLOSED',
                'platform': trade.get('platform', 'MT5_LIBERTEX_DEMO'),
                'opened_at': trade.get('time', datetime.now(timezone.utc).isoformat()),
                'closed_at': datetime.now(timezone.utc).isoformat(),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'price': exit_price or 0.0,
                'strategy': settings.get('strategy', 'day') if settings else 'day',
                'close_reason': reason,
                'closed_by': 'KI_MONITOR'
            }
            
            # Speichere in DB
            await trades_collection.insert_one(closed_trade)
            logger.info(f"💾 Closed trade {trade['ticket']} saved to database - P/L: {profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error saving closed trade: {e}", exc_info=True)
    
    async def start(self):
        """Startet den Monitor"""
        self.running = True
        await self.monitor_trades()
    
    async def stop(self):
        """Stoppt den Monitor"""
        self.running = False
        logger.info("🛑 Trade Settings Monitor gestoppt")


# Global instance
trade_settings_manager = TradeSettingsManager()
