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
        V2.3.35 FIX: Verbesserte Markt-Öffnungszeiten-Prüfung mit Puffer
        
        Forex/CFD Märkte sind typischerweise:
        - Sonntag 22:00 UTC bis Freitag 22:00 UTC
        
        WICHTIG: Wir fügen einen 2-Stunden-Puffer hinzu, um Zeitzonen-Probleme zu vermeiden!
        So werden Trades auch am Sonntag ab 20:00 UTC (= 21:00 CET) verarbeitet.
        
        Returns: True wenn wahrscheinlich offen, False wenn sicher geschlossen
        """
        now = datetime.now(timezone.utc)
        
        # Samstag ist IMMER geschlossen (Tag 5)
        if now.weekday() == 5:
            return False
        
        # Sonntag: Märkte öffnen um 22:00 UTC, aber mit 2h Puffer = ab 20:00 UTC
        # V2.3.35: 2 Stunden Puffer für Zeitzonen-Unterschiede
        if now.weekday() == 6:  # Sonntag
            if now.hour < 20:  # Vor 20:00 UTC (= 21:00 CET)
                return False
            # Ab 20:00 UTC (Sonntag) erlauben wir Trades
            return True
        
        # Freitag: Märkte schließen um 22:00 UTC, mit Puffer bis 23:00 UTC
        if now.weekday() == 4 and now.hour >= 23:
            return False
        
        # Montag bis Donnerstag: Immer offen
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
        
        # 🆕 v2.3.34 FIX: Verwende _determine_strategy um die richtige Strategie für den Trade zu finden!
        # Dies prüft ZUERST die Strategie des Trades selbst (swing, day, scalping, etc.)
        strategy = self._determine_strategy(trade, global_settings)
        
        if not strategy:
            logger.warning(f"No strategy found for trade {trade.get('ticket')}, using day trading fallback")
            strategy = self._get_day_trading_strategy(global_settings)
        
        # Berechne SL/TP basierend auf Modus (Prozent ODER Euro)
        sl_mode = strategy.get('stop_loss_mode', 'percent')  # 'percent' oder 'euro'
        tp_mode = strategy.get('take_profit_mode', 'percent')  # 'percent' oder 'euro'
        
        # Stop Loss Berechnung
        sl_percent = None  # 🐛 FIX: Initialisiere für beide Modi
        if sl_mode == 'euro':
            sl_euro = strategy.get('stop_loss_euro', 15.0)  # Default €15
            # Bei X Euro Verlust: Entry - X EUR für BUY, Entry + X EUR für SELL
            if trade_type == 'BUY':
                stop_loss = entry_price - sl_euro
            else:  # SELL
                stop_loss = entry_price + sl_euro
            # Berechne Prozent für max_loss_percent (für Anzeige)
            sl_percent = abs((stop_loss - entry_price) / entry_price * 100) if entry_price > 0 else 2.0
        else:  # percent
            sl_percent = strategy.get('stop_loss_percent', 2.0)
            if trade_type == 'BUY':
                stop_loss = entry_price * (1 - sl_percent / 100)
            else:  # SELL
                stop_loss = entry_price * (1 + sl_percent / 100)
        
        # Take Profit Berechnung
        tp_percent = None  # 🐛 FIX: Initialisiere für beide Modi
        if tp_mode == 'euro':
            tp_euro = strategy.get('take_profit_euro', 30.0)  # Default €30
            # Bei X Euro Gewinn: Entry + X EUR für BUY, Entry - X EUR für SELL
            if trade_type == 'BUY':
                take_profit = entry_price + tp_euro
            else:  # SELL
                take_profit = entry_price - tp_euro
            # Berechne Prozent für Anzeige
            tp_percent = abs((take_profit - entry_price) / entry_price * 100) if entry_price > 0 else 2.5
        else:  # percent
            tp_percent = strategy.get('take_profit_percent', 2.5)  # 🐛 FIX: Default 2.5% für Day Trading
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
            'max_loss_percent': sl_percent if sl_percent else 2.0,
            'take_profit_percent': tp_percent if tp_percent else 2.5,
            'strategy': strategy.get('name', 'day'),  # 🐛 FIX: Default 'day' statt 'swing'
            'entry_price': entry_price,
            'trade_type': trade_type,
            'sl_mode': sl_mode,
            'tp_mode': tp_mode,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"✅ Calculated settings for {trade['ticket']}: SL={stop_loss:.2f}, TP={take_profit:.2f}")
        
        return settings
    
    def _get_swing_strategy(self, global_settings: Dict) -> Dict:
        """
        Swing Trading: Längere Haltezeiten, größere TP/SL
        V2.3.34: Trailing Stop IMMER AKTIV mit 1.5% Distanz
        """
        return {
            'name': 'swing',
            'stop_loss_mode': global_settings.get('swing_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('swing_stop_loss_percent', 2.0),
            'stop_loss_euro': global_settings.get('swing_stop_loss_euro', 30.0),
            'take_profit_mode': global_settings.get('swing_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('swing_take_profit_percent', 4.0),
            'take_profit_euro': global_settings.get('swing_take_profit_euro', 60.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('swing_trailing_distance', 1.5)  # 1.5% Trailing
        }
    
    def _get_day_trading_strategy(self, global_settings: Dict) -> Dict:
        """
        Day Trading: Schnelle Trades, kürzere Haltezeit
        V2.3.34: Trailing Stop IMMER AKTIV mit 1.0% Distanz
        """
        return {
            'name': 'day',
            'stop_loss_mode': global_settings.get('day_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('day_stop_loss_percent', 1.5),
            'stop_loss_euro': global_settings.get('day_stop_loss_euro', 15.0),
            'take_profit_mode': global_settings.get('day_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('day_take_profit_percent', 2.5),
            'take_profit_euro': global_settings.get('day_take_profit_euro', 30.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('day_trailing_distance', 1.0)  # 1.0% Trailing
        }
    
    def _get_scalping_strategy(self, global_settings: Dict) -> Dict:
        """
        Scalping: Ultra-schnelle Trades
        V2.3.34: Trailing Stop IMMER AKTIV mit 0.2% Distanz (sehr eng!)
        """
        return {
            'name': 'scalping',
            'stop_loss_mode': global_settings.get('scalping_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('scalping_stop_loss_percent', 0.3),
            'stop_loss_euro': global_settings.get('scalping_stop_loss_euro', 5.0),
            'take_profit_mode': global_settings.get('scalping_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('scalping_take_profit_percent', 0.5),
            'take_profit_euro': global_settings.get('scalping_take_profit_euro', 8.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('scalping_trailing_distance', 0.2)  # 0.2% Trailing (sehr eng)
        }
    
    def _get_mean_reversion_strategy(self, global_settings: Dict) -> Dict:
        """
        Mean Reversion: Rückkehr zum Mittelwert
        V2.3.34: Trailing Stop IMMER AKTIV mit 1.2% Distanz
        """
        return {
            'name': 'mean_reversion',
            'stop_loss_mode': global_settings.get('mean_reversion_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('mean_reversion_stop_loss_percent', 2.0),
            'stop_loss_euro': global_settings.get('mean_reversion_stop_loss_euro', 30.0),
            'take_profit_mode': global_settings.get('mean_reversion_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('mean_reversion_take_profit_percent', 4.0),
            'take_profit_euro': global_settings.get('mean_reversion_take_profit_euro', 60.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('mean_reversion_trailing_distance', 1.2)  # 1.2% Trailing
        }
    
    def _get_momentum_strategy(self, global_settings: Dict) -> Dict:
        """
        Momentum: Trend-Following
        V2.3.34: Trailing Stop IMMER AKTIV mit 1.8% Distanz (größer für Trends)
        """
        return {
            'name': 'momentum',
            'stop_loss_mode': global_settings.get('momentum_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('momentum_stop_loss_percent', 2.5),
            'stop_loss_euro': global_settings.get('momentum_stop_loss_euro', 40.0),
            'take_profit_mode': global_settings.get('momentum_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('momentum_take_profit_percent', 5.0),
            'take_profit_euro': global_settings.get('momentum_take_profit_euro', 80.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('momentum_trailing_distance', 1.8)  # 1.8% Trailing
        }
    
    def _get_breakout_strategy(self, global_settings: Dict) -> Dict:
        """
        Breakout: Ausbrüche aus Ranges
        V2.3.34: Trailing Stop IMMER AKTIV mit 2.0% Distanz
        """
        return {
            'name': 'breakout',
            'stop_loss_mode': global_settings.get('breakout_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('breakout_stop_loss_percent', 3.0),
            'stop_loss_euro': global_settings.get('breakout_stop_loss_euro', 50.0),
            'take_profit_mode': global_settings.get('breakout_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('breakout_take_profit_percent', 6.0),
            'take_profit_euro': global_settings.get('breakout_take_profit_euro', 100.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('breakout_trailing_distance', 2.0)  # 2.0% Trailing
        }
    
    def _get_grid_strategy(self, global_settings: Dict) -> Dict:
        """
        Grid: Grid-Trading für Seitwärtsmärkte
        V2.3.34: Trailing Stop IMMER AKTIV mit 1.0% Distanz
        """
        return {
            'name': 'grid',
            'stop_loss_mode': global_settings.get('grid_sl_mode', 'percent'),
            'stop_loss_percent': global_settings.get('grid_stop_loss_percent', 5.0),
            'stop_loss_euro': global_settings.get('grid_stop_loss_euro', 80.0),
            'take_profit_mode': global_settings.get('grid_tp_mode', 'percent'),
            'take_profit_percent': global_settings.get('grid_tp_per_level_percent', 2.0),
            'take_profit_euro': global_settings.get('grid_take_profit_euro', 40.0),
            'trailing_stop': True,  # V2.3.34: Immer aktiv
            'trailing_distance': global_settings.get('grid_trailing_distance', 1.0)  # 1.0% Trailing
        }
    
    def _determine_strategy(self, trade: Dict, global_settings: Dict) -> Optional[Dict]:
        """
        🆕 v2.3.34 FIX: Verwende die STRATEGIE DES TRADES, nicht globale Flags!
        
        Wenn ein Trade als 'swing' erstellt wurde, verwende Swing Settings.
        Wenn ein Trade als 'day' erstellt wurde, verwende Day Settings.
        """
        
        # 🆕 v2.3.34: ZUERST prüfe die Strategie des Trades selbst!
        trade_strategy = trade.get('strategy', '').lower()
        logger.info(f"🔍 Trade {trade.get('ticket')}: Strategie aus Trade = '{trade_strategy}'")
        
        # Mapping: Trade-Strategie → Settings-Getter
        if trade_strategy == 'swing':
            logger.info(f"  → Verwende SWING Settings")
            return self._get_swing_strategy(global_settings)
        
        if trade_strategy == 'day':
            logger.info(f"  → Verwende DAY Settings")
            return self._get_day_trading_strategy(global_settings)
        
        if trade_strategy == 'scalping':
            logger.info(f"  → Verwende SCALPING Settings")
            return self._get_scalping_strategy(global_settings)
        
        if trade_strategy == 'mean_reversion':
            logger.info(f"  → Verwende MEAN REVERSION Settings")
            return self._get_mean_reversion_strategy(global_settings)
        
        if trade_strategy == 'momentum':
            logger.info(f"  → Verwende MOMENTUM Settings")
            return self._get_momentum_strategy(global_settings)
        
        if trade_strategy == 'breakout':
            logger.info(f"  → Verwende BREAKOUT Settings")
            return self._get_breakout_strategy(global_settings)
        
        if trade_strategy == 'grid':
            logger.info(f"  → Verwende GRID Settings")
            return self._get_grid_strategy(global_settings)
        
        # FALLBACK: Wenn keine Strategie im Trade, verwende alte Logik
        logger.warning(f"⚠️ Trade {trade.get('ticket')} hat keine Strategie, verwende Fallback")
        
        # Prüfe globale Trading-Strategie (Legacy)
        trading_strategy = global_settings.get('trading_strategy', 'CONSERVATIVE')
        if trading_strategy == 'SCALPING':
            return self._get_scalping_strategy(global_settings)
        
        # Prüfe Day Trading (Default für neue Trades)
        if global_settings.get('day_trading_enabled', True):
            return self._get_day_trading_strategy(global_settings)
        
        # Prüfe Swing Trading
        if global_settings.get('swing_trading_enabled'):
            return self._get_swing_strategy(global_settings)
        
        # Fallback: Day Trading Default (falls nichts aktiviert)
        return {
            'name': 'day',
            'stop_loss_percent': 2.0,
            'take_profit_percent': 2.5,
            'trailing_stop': False,
            'trailing_distance': 30.0
        }
    
    async def get_or_create_settings_for_trade(
        self,
        trade: Dict,
        global_settings: Dict,
        force_update: bool = True
    ) -> Optional[Dict]:
        """
        🆕 v2.3.33: Holt oder erstellt Settings für einen Trade.
        Bei force_update=True werden SL/TP basierend auf der Strategie des Trades
        und den NEUEN globalen Settings aktualisiert.
        
        Die Strategie des Trades wird BEIBEHALTEN, aber die SL/TP-Werte werden
        basierend auf den aktuellen globalen Settings für diese Strategie NEU berechnet.
        """
        try:
            trade_id = f"mt5_{trade['ticket']}"
            
            # Prüfe ob Settings bereits existieren
            existing = await trade_settings.find_one({"trade_id": trade_id})
            
            if existing and force_update:
                # Settings existieren - aktualisiere NUR SL/TP basierend auf Strategie
                strategy_name = existing.get('strategy', 'day')
                logger.info(f"🔍 Trade {trade['ticket']}: Strategie = '{strategy_name}', force_update = {force_update}")
                
                # Hole die neue Strategie-Konfiguration basierend auf der bestehenden Strategie
                strategy_config = self._get_strategy_config_by_name(strategy_name, global_settings)
                logger.info(f"  → Strategy Config: SL={strategy_config.get('stop_loss_percent')}%, TP={strategy_config.get('take_profit_percent')}%")
                
                if not strategy_config:
                    logger.warning(f"⚠️ Unknown strategy '{strategy_name}' for trade {trade['ticket']}")
                    return existing
                
                # Berechne neue SL/TP basierend auf Entry-Price und neuer Strategie-Konfiguration
                entry_price = existing.get('entry_price') or trade.get('price_open') or trade.get('entry_price')
                if not entry_price:
                    logger.warning(f"⚠️ No entry price for trade {trade['ticket']}")
                    return existing
                
                # Trade Type - Priorität: existing DB > trade dict > Fallback
                # v2.3.33: Verbesserte Type-Erkennung für SELL Trades
                trade_type_raw = existing.get('type') or trade.get('type', 'BUY')
                trade_type_str = str(trade_type_raw).upper()
                
                if 'SELL' in trade_type_str:
                    trade_type = 'SELL'
                elif 'BUY' in trade_type_str:
                    trade_type = 'BUY'
                else:
                    # Fallback: Inferiere aus SL/TP Positionen
                    # Bei SELL ist SL > Entry, bei BUY ist SL < Entry
                    current_sl = existing.get('stop_loss', 0)
                    if current_sl and entry_price and current_sl > entry_price:
                        trade_type = 'SELL'
                        logger.debug(f"Inferred SELL type for trade {trade['ticket']} (SL > Entry)")
                    else:
                        trade_type = 'BUY'
                
                # Berechne neue SL/TP Werte
                sl_percent = strategy_config.get('stop_loss_percent', 2.0)
                tp_percent = strategy_config.get('take_profit_percent', 2.5)
                
                if trade_type == 'BUY':
                    new_sl = entry_price * (1 - sl_percent / 100)
                    new_tp = entry_price * (1 + tp_percent / 100)
                else:  # SELL
                    new_sl = entry_price * (1 + sl_percent / 100)
                    new_tp = entry_price * (1 - tp_percent / 100)
                
                # Update nur SL/TP, behalte Strategie bei
                # v2.3.33: Speichere auch type für zukünftige Updates
                updated_settings = {
                    'stop_loss': round(new_sl, 2),
                    'take_profit': round(new_tp, 2),
                    'max_loss_percent': sl_percent,
                    'take_profit_percent': tp_percent,
                    'type': trade_type,  # Speichere Type für zukünftige Updates
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                # Speichere Update in DB
                await trade_settings.update_one(
                    {"trade_id": trade_id},
                    {"$set": updated_settings}
                )
                
                logger.info(f"✅ Updated trade {trade['ticket']} ({strategy_name}): SL={new_sl:.2f}, TP={new_tp:.2f}")
                
                # Gib aktualisierte Settings zurück
                existing.update(updated_settings)
                return existing
            
            elif not existing:
                # Keine Settings vorhanden - erstelle neue
                new_settings = await self.apply_global_settings_to_trade(trade, global_settings)
                
                if new_settings:
                    await trade_settings.insert_one(new_settings)
                    logger.info(f"✅ Created settings for trade {trade['ticket']}")
                    return new_settings
            
            return existing
            
        except Exception as e:
            logger.error(f"Error in get_or_create_settings_for_trade: {e}", exc_info=True)
            return None
    
    def _get_strategy_config_by_name(self, strategy_name: str, global_settings: Dict) -> Optional[Dict]:
        """
        🆕 v2.3.33: Holt die Strategie-Konfiguration basierend auf dem Namen.
        """
        strategy_name = strategy_name.lower()
        
        # V2.3.34: Alle Strategien verwenden jetzt dedizierte Getter-Funktionen
        if strategy_name in ['day', 'day_trading']:
            return self._get_day_trading_strategy(global_settings)
        elif strategy_name in ['swing', 'swing_trading']:
            return self._get_swing_strategy(global_settings)
        elif strategy_name in ['scalping']:
            return self._get_scalping_strategy(global_settings)
        elif strategy_name in ['mean_reversion']:
            return self._get_mean_reversion_strategy(global_settings)
        elif strategy_name in ['momentum']:
            return self._get_momentum_strategy(global_settings)
        elif strategy_name in ['breakout']:
            return self._get_breakout_strategy(global_settings)
        elif strategy_name in ['grid']:
            return self._get_grid_strategy(global_settings)
        else:
            # Default: Day Trading
            logger.warning(f"Unknown strategy '{strategy_name}', using day trading defaults")
            return self._get_day_trading_strategy(global_settings)
    
    async def sync_all_trades_with_settings(self, open_positions: List[Dict]):
        """
        Wendet Settings auf ALLE offenen Trades an
        UND erkennt Trades, die in MT5 geschlossen wurden
        """
        try:
            # Hole globale Settings
            global_settings = await trading_settings.find_one({"id": "trading_settings"})
            if not global_settings:
                logger.warning("No global settings found")
                return
            
            logger.info(f"🔄 Syncing settings for {len(open_positions)} trades...")
            
            # V2.3.35: Erkennung von geschlossenen Trades
            # Hole alle Tickets der aktuell offenen MT5-Positionen
            current_mt5_tickets = set()
            for pos in open_positions:
                ticket = pos.get('id') or pos.get('ticket')
                if ticket:
                    current_mt5_tickets.add(str(ticket))
            
            # Hole alle Trades, die wir als OPEN in der DB haben
            from database import trades as trades_collection
            from database_v2 import db_manager
            
            try:
                db_open_trades = await db_manager.trades_db.get_trades(status='OPEN')
                
                # Prüfe welche DB-Trades nicht mehr in MT5 existieren
                for db_trade in db_open_trades:
                    db_ticket = db_trade.get('mt5_ticket') or db_trade.get('ticket')
                    if db_ticket and str(db_ticket) not in current_mt5_tickets:
                        # Dieser Trade wurde in MT5 geschlossen!
                        logger.info(f"🔍 Trade {db_ticket} nicht mehr in MT5 gefunden - wurde extern geschlossen")
                        
                        # Markiere als CLOSED in der DB
                        await self._mark_trade_as_closed_externally(db_trade)
                        
            except Exception as e:
                logger.warning(f"⚠️ Could not check for externally closed trades: {e}")
            
            synced_count = 0
            for trade in open_positions:
                try:
                    # V2.3.34 FIX: force_update=True damit Settings aktualisiert werden!
                    result = await self.get_or_create_settings_for_trade(
                        trade=trade,
                        global_settings=global_settings,
                        force_update=True  # IMMER updaten wenn Settings geändert wurden!
                    )
                    
                    if result:
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing trade {trade.get('ticket')}: {e}")
            
            logger.info(f"✅ Synced {synced_count}/{len(open_positions)} trades")
            
        except Exception as e:
            logger.error(f"Error in sync_all_trades_with_settings: {e}", exc_info=True)
    
    async def _mark_trade_as_closed_externally(self, trade: Dict):
        """
        V2.3.35: Markiert einen Trade als extern geschlossen (manuell in MT5)
        """
        try:
            from database import trades as trades_collection
            
            ticket = trade.get('mt5_ticket') or trade.get('ticket')
            trade_id = trade.get('id') or f"mt5_{ticket}"
            
            # Update den Trade in der DB
            update_data = {
                'status': 'CLOSED',
                'closed_at': datetime.now(timezone.utc).isoformat(),
                'close_reason': 'EXTERNAL_CLOSE',
                'closed_by': 'MT5_MANUAL'
            }
            
            # Update in DB
            await trades_collection.update_one(
                {'id': trade_id},
                {'$set': update_data}
            )
            
            logger.info(f"💾 Trade {ticket} als extern geschlossen markiert (MT5_MANUAL)")
            
        except Exception as e:
            logger.error(f"Error marking trade as externally closed: {e}", exc_info=True)
    
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
