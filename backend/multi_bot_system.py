"""
🤖 Booner Trade v2.3.31 - Multi-Bot-System
==========================================
3 spezialisierte Bots für parallele Verarbeitung:
- MarketBot: Marktdaten sammeln, Indikatoren berechnen
- SignalBot: Signale analysieren, News auswerten, Strategien
- TradeBot: Trades ausführen, Positionen überwachen, SL/TP prüfen
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================================
# BASE BOT CLASS
# ============================================================================

class BaseBot(ABC):
    """Basis-Klasse für alle Trading Bots"""
    
    def __init__(self, name: str, interval_seconds: int = 10):
        self.name = name
        self.interval = interval_seconds
        self.is_running = False
        self.last_run = None
        self.run_count = 0
        self.error_count = 0
        self._task = None
        logger.info(f"🤖 {self.name} initialized (interval: {self.interval}s)")
    
    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Hauptlogik des Bots - muss implementiert werden"""
        pass
    
    async def run_once(self) -> Dict[str, Any]:
        """Einmalige Ausführung mit Error Handling"""
        try:
            start_time = datetime.now()
            result = await self.execute()
            duration = (datetime.now() - start_time).total_seconds()
            
            self.last_run = datetime.now(timezone.utc)
            self.run_count += 1
            
            result['duration_ms'] = round(duration * 1000)
            result['run_count'] = self.run_count
            
            logger.debug(f"✅ {self.name} completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ {self.name} error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def run_forever(self):
        """Endlosschleife für kontinuierliche Ausführung"""
        self.is_running = True
        logger.info(f"🚀 {self.name} started (interval: {self.interval}s)")
        
        while self.is_running:
            try:
                await self.run_once()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                logger.info(f"🛑 {self.name} cancelled")
                break
            except Exception as e:
                logger.error(f"❌ {self.name} loop error: {e}")
                await asyncio.sleep(5)  # Kurze Pause bei Fehler
        
        self.is_running = False
        logger.info(f"⏹️ {self.name} stopped")
    
    def stop(self):
        """Bot stoppen"""
        self.is_running = False
        if self._task:
            self._task.cancel()
    
    def get_status(self) -> Dict[str, Any]:
        """Bot-Status abrufen"""
        return {
            'name': self.name,
            'is_running': self.is_running,
            'interval': self.interval,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'run_count': self.run_count,
            'error_count': self.error_count
        }


# ============================================================================
# MARKET BOT - Marktdaten sammeln
# ============================================================================

class MarketBot(BaseBot):
    """
    MarketBot: Sammelt Marktdaten und berechnet Indikatoren
    - Läuft alle 5-10 Sekunden
    - Holt Preise von Yahoo Finance / Alpha Vantage
    - Berechnet technische Indikatoren (RSI, MACD, SMA, EMA)
    - Speichert in market_data.db
    """
    
    def __init__(self, db_manager, settings_getter):
        super().__init__("MarketBot", interval_seconds=8)
        self.db = db_manager
        self.get_settings = settings_getter
        self.commodities = ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 
                           'CRUDE_OIL', 'BRENT_CRUDE', 'NATURAL_GAS',
                           'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'ETHUSD']
    
    async def execute(self) -> Dict[str, Any]:
        """Marktdaten aktualisieren - V2.3.32 FIX: Nutzt commodity_processor"""
        updated_count = 0
        errors = []
        
        try:
            # V2.3.32: Nutze commodity_processor für Marktdaten
            from commodity_processor import process_single_commodity, get_commodity_config
            
            for commodity in self.commodities:
                try:
                    # Verarbeite Commodity
                    config = get_commodity_config(commodity)
                    if not config:
                        continue
                    
                    data = await process_single_commodity(commodity, config)
                    
                    if data and data.get('price'):
                        updated_count += 1
                        logger.debug(f"✅ MarketBot updated {commodity}: ${data.get('price')}")
                        
                except Exception as e:
                    errors.append(f"{commodity}: {str(e)[:50]}")
                    logger.debug(f"MarketBot error for {commodity}: {e}")
            
        except ImportError as e:
            logger.warning(f"⚠️ MarketBot: commodity_processor nicht verfügbar: {e}")
            # Fallback: Marktdaten sind bereits durch den server.py market_data_updater aktiv
            return {
                'success': True,
                'message': 'Using server.py market updater',
                'updated': 0,
                'total': len(self.commodities),
                'errors': []
            }
        except Exception as e:
            logger.error(f"❌ MarketBot general error: {e}")
            errors.append(str(e)[:100])
        
        return {
            'success': True,
            'updated': updated_count,
            'total': len(self.commodities),
            'errors': errors[:5]  # Max 5 Fehler
        }


# ============================================================================
# SIGNAL BOT - Signale analysieren
# ============================================================================

class SignalBot(BaseBot):
    """
    SignalBot: Analysiert Signale und generiert Trading-Empfehlungen
    - Läuft alle 15-30 Sekunden
    - Analysiert Marktdaten aus market_data.db
    - Wertet News aus (optional)
    - Führt Strategie-Analysen durch
    - Generiert BUY/SELL Signale
    """
    
    def __init__(self, db_manager, settings_getter):
        super().__init__("SignalBot", interval_seconds=20)
        self.db = db_manager
        self.get_settings = settings_getter
        self.pending_signals = []  # Queue für TradeBot
    
    async def execute(self) -> Dict[str, Any]:
        """Signale analysieren"""
        settings = await self.get_settings()
        
        if not settings:
            return {'success': False, 'error': 'No settings'}
        
        if not settings.get('auto_trading', False):
            return {'success': True, 'message': 'Auto-trading disabled', 'signals': 0}
        
        signals_generated = 0
        analyzed_count = 0
        
        # Hole alle Marktdaten
        market_data = await self.db.market_db.get_market_data()
        
        # Aktive Strategien ermitteln
        active_strategies = self._get_active_strategies(settings)
        
        for data in market_data:
            commodity = data.get('commodity')
            if not commodity:
                continue
            
            analyzed_count += 1
            
            # Analysiere mit jeder aktiven Strategie
            for strategy_name in active_strategies:
                try:
                    signal = await self._analyze_with_strategy(
                        strategy_name, commodity, data, settings
                    )
                    
                    if signal and signal.get('action') in ['BUY', 'SELL']:
                        # Signal zur Queue hinzufügen
                        signal['generated_at'] = datetime.now(timezone.utc).isoformat()
                        signal['commodity'] = commodity
                        signal['strategy'] = strategy_name
                        self.pending_signals.append(signal)
                        signals_generated += 1
                        
                        logger.info(f"📊 {strategy_name} Signal: {signal['action']} {commodity}")
                        
                except Exception as e:
                    logger.debug(f"Strategy {strategy_name} error for {commodity}: {e}")
        
        return {
            'success': True,
            'analyzed': analyzed_count,
            'signals_generated': signals_generated,
            'pending_signals': len(self.pending_signals),
            'active_strategies': active_strategies
        }
    
    def _get_active_strategies(self, settings: dict) -> List[str]:
        """Ermittelt aktive Strategien aus Settings - V2.3.32 FIX"""
        strategies = []
        
        # V2.3.32 FIX: Korrektes Mapping zu den tatsächlichen Setting-Keys
        strategy_map = {
            'day_trading': ['day_enabled', 'day_trading_enabled'],
            'swing_trading': ['swing_enabled', 'swing_trading_enabled'],
            'scalping': ['scalping_enabled'],
            'mean_reversion': ['mean_reversion_enabled'],
            'momentum': ['momentum_enabled'],
            'breakout': ['breakout_enabled'],
            'grid': ['grid_enabled']
        }
        
        for strategy, setting_keys in strategy_map.items():
            # Prüfe alle möglichen Keys für diese Strategie
            for key in setting_keys:
                if settings.get(key, False):
                    strategies.append(strategy)
                    logger.debug(f"✅ Strategy {strategy} enabled via {key}")
                    break
        
        # Default: Day Trading wenn keine aktiv
        if not strategies:
            strategies = ['day_trading']
            logger.warning("⚠️ No strategies enabled, using default: day_trading")
        else:
            logger.info(f"📊 Active strategies: {strategies}")
        
        return strategies
    
    async def _analyze_with_strategy(self, strategy: str, commodity: str, 
                                     data: dict, settings: dict) -> Optional[Dict]:
        """Führt Strategie-Analyse durch"""
        
        # Einfache Analyse basierend auf RSI und Trend
        rsi = data.get('rsi', 50)
        trend = data.get('trend', 'neutral')
        signal = data.get('signal', 'HOLD')
        price = data.get('price', 0)
        
        if not price:
            return None
        
        action = 'HOLD'
        confidence = 0.5
        
        # RSI-basierte Logik
        if strategy in ['mean_reversion']:
            if rsi and rsi < 30:
                action = 'BUY'
                confidence = 0.7 + (30 - rsi) / 100
            elif rsi and rsi > 70:
                action = 'SELL'
                confidence = 0.7 + (rsi - 70) / 100
                
        elif strategy in ['momentum', 'day_trading']:
            # V2.3.32 FIX: Trend-Werte sind 'UP'/'DOWN', nicht 'bullish'/'bearish'
            is_bullish = trend in ['UP', 'bullish', 'BULLISH']
            is_bearish = trend in ['DOWN', 'bearish', 'BEARISH']
            
            # Day Trading: Signal hat Priorität, Trend bestätigt
            if signal == 'BUY':
                if is_bullish:
                    action = 'BUY'
                    confidence = 0.70  # Höhere Konfidenz bei Trend-Bestätigung
                else:
                    action = 'BUY'
                    confidence = 0.55  # Niedrigere Konfidenz gegen Trend
            elif signal == 'SELL':
                if is_bearish:
                    action = 'SELL'
                    confidence = 0.70
                else:
                    action = 'SELL'
                    confidence = 0.55
                
        elif strategy in ['swing_trading']:
            # Swing: Nur mit Trend handeln
            is_bullish = trend in ['UP', 'bullish', 'BULLISH']
            is_bearish = trend in ['DOWN', 'bearish', 'BEARISH']
            
            if is_bullish and rsi and rsi < 45:
                action = 'BUY'
                confidence = 0.65
            elif is_bearish and rsi and rsi > 55:
                action = 'SELL'
                confidence = 0.65
                
        elif strategy in ['breakout']:
            # V2.3.32 FIX: Trend-Werte korrigiert
            is_bullish = trend in ['UP', 'bullish', 'BULLISH']
            is_bearish = trend in ['DOWN', 'bearish', 'BEARISH']
            
            # Breakout bei starkem RSI
            if rsi and rsi > 65 and is_bullish:
                action = 'BUY'
                confidence = 0.6
            elif rsi and rsi < 35 and is_bearish:
                action = 'SELL'
                confidence = 0.6
        
        # Mindest-Konfidenz prüfen
        min_confidence = settings.get(f'{strategy}_min_confidence', 60) / 100
        
        if confidence >= min_confidence and action != 'HOLD':
            return {
                'action': action,
                'confidence': confidence,
                'price': price,
                'rsi': rsi,
                'trend': trend,
                'reason': f'{strategy}: RSI={rsi:.1f}, Trend={trend}'
            }
        
        return None
    
    def get_pending_signals(self) -> List[Dict]:
        """Gibt pending Signals zurück und leert Queue"""
        signals = self.pending_signals.copy()
        self.pending_signals = []
        return signals


# ============================================================================
# TRADE BOT - Trades ausführen und überwachen
# ============================================================================

class TradeBot(BaseBot):
    """
    TradeBot: Führt Trades aus und überwacht Positionen
    - Läuft alle 10-15 Sekunden
    - Verarbeitet Signale von SignalBot
    - Führt Trades über MetaAPI aus
    - Überwacht SL/TP für alle offenen Positionen
    - Schließt Trades bei Erreichen von TP/SL
    """
    
    def __init__(self, db_manager, settings_getter, signal_bot: SignalBot):
        super().__init__("TradeBot", interval_seconds=12)
        self.db = db_manager
        self.get_settings = settings_getter
        self.signal_bot = signal_bot
        self.positions_checked = 0
        self.trades_executed = 0
        self.trades_closed = 0
    
    async def execute(self) -> Dict[str, Any]:
        """Trades ausführen und Positionen überwachen"""
        settings = await self.get_settings()
        
        if not settings:
            return {'success': False, 'error': 'No settings'}
        
        result = {
            'success': True,
            'signals_processed': 0,
            'trades_executed': 0,
            'positions_checked': 0,
            'positions_closed': 0
        }
        
        # 1. Signale von SignalBot verarbeiten
        if settings.get('auto_trading', False):
            pending_signals = self.signal_bot.get_pending_signals()
            result['signals_processed'] = len(pending_signals)
            
            for signal in pending_signals:
                try:
                    executed = await self._execute_signal(signal, settings)
                    if executed:
                        result['trades_executed'] += 1
                        self.trades_executed += 1
                except Exception as e:
                    logger.error(f"Signal execution error: {e}")
        
        # 2. Offene Positionen überwachen
        try:
            closed_count = await self._monitor_positions(settings)
            result['positions_closed'] = closed_count
            self.trades_closed += closed_count
        except Exception as e:
            logger.error(f"Position monitoring error: {e}")
        
        result['positions_checked'] = self.positions_checked
        
        return result
    
    async def _execute_signal(self, signal: Dict, settings: dict) -> bool:
        """Führt ein Trading-Signal aus"""
        from multi_platform_connector import multi_platform
        
        commodity = signal.get('commodity')
        action = signal.get('action')
        strategy = signal.get('strategy', 'day_trading')
        price = signal.get('price', 0)
        confidence = signal.get('confidence', 0)
        
        if not commodity or not action or action == 'HOLD':
            return False
        
        # Prüfe Duplicate
        existing_count = await self.db.trades_db.count_open_trades(
            commodity=commodity, strategy=strategy
        )
        
        max_positions = settings.get(f'{strategy}_max_positions', 3)
        if existing_count >= max_positions:
            logger.info(f"⚠️ Max positions reached for {strategy}/{commodity}: {existing_count}/{max_positions}")
            return False
        
        # V2.3.31: Verwende Risk Manager für Risiko-Bewertung
        active_platforms = settings.get('active_platforms', [])
        
        try:
            from risk_manager import risk_manager, init_risk_manager
            
            # Initialisiere Risk Manager
            if not risk_manager.connector:
                await init_risk_manager(multi_platform)
            
            # Bewerte Trade-Risiko
            assessment = await risk_manager.assess_trade_risk(
                commodity=commodity,
                action=action,
                lot_size=0.1,  # Wird später berechnet
                price=price,
                platform_names=active_platforms
            )
            
            if not assessment.can_trade:
                logger.warning(f"⚠️ Risk Manager blocked trade: {assessment.reason}")
                return False
            
            # Verwende empfohlenen Broker
            recommended_platform = assessment.recommended_broker
            if recommended_platform:
                active_platforms = [recommended_platform]
            
        except ImportError:
            logger.warning("Risk Manager not available, using legacy risk check")
        
        for platform in active_platforms:
            try:
                if 'MT5_' not in platform:
                    continue
                
                # Hole Account Info
                account_info = await multi_platform.get_account_info(platform)
                if not account_info:
                    continue
                
                balance = account_info.get('balance', 0)
                equity = account_info.get('equity', 0)
                margin_used = account_info.get('margin', 0)
                
                # V2.3.32 FIX: Portfolio-Risiko Check: Max 20%
                # Korrektes Portfolio-Risiko = verwendete Margin / Balance * 100
                used_margin_percent = (margin_used / balance * 100) if balance > 0 else 0
                
                if used_margin_percent > 20:
                    logger.warning(f"⚠️ Portfolio risk exceeded for {platform}: {used_margin_percent:.1f}% > 20% (Margin: {margin_used:.2f} / Balance: {balance:.2f})")
                    continue
                
                # Berechne Lot Size basierend auf Risk per Trade
                risk_percent = settings.get(f'{strategy}_risk_percent', 1)
                lot_size = self._calculate_lot_size(balance, risk_percent, price)
                
                # Berechne SL/TP
                sl_percent = settings.get(f'{strategy.replace("_trading", "")}_stop_loss_percent', 2)
                tp_percent = settings.get(f'{strategy.replace("_trading", "")}_take_profit_percent', 4)
                
                if action == 'BUY':
                    stop_loss = price * (1 - sl_percent / 100)
                    take_profit = price * (1 + tp_percent / 100)
                else:
                    stop_loss = price * (1 + sl_percent / 100)
                    take_profit = price * (1 - tp_percent / 100)
                
                # Trade ausführen - V2.3.32 FIX: Korrekte Methode execute_trade
                mt5_symbol = self._get_mt5_symbol(commodity)
                    
                trade_result = await multi_platform.execute_trade(
                    platform_name=platform,
                    symbol=mt5_symbol,
                    action=action,
                    volume=lot_size,
                    stop_loss=None,  # KI überwacht SL/TP
                    take_profit=None
                )
                
                if trade_result and trade_result.get('success'):
                    # Trade in DB speichern
                    trade_id = await self.db.trades_db.insert_trade({
                        'commodity': commodity,
                        'type': action,
                        'price': price,
                        'entry_price': price,
                        'quantity': lot_size,
                        'status': 'OPEN',
                        'platform': platform,
                        'strategy': strategy,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'mt5_ticket': trade_result.get('ticket'),
                        'opened_at': datetime.now(timezone.utc).isoformat(),
                        'opened_by': 'TradeBot',
                        'strategy_signal': signal.get('reason', '')
                    })
                    
                    # Trade Settings speichern
                    await self.db.trades_db.save_trade_settings(trade_id, {
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'strategy': strategy,
                        'entry_price': price,
                        'platform': platform,
                        'commodity': commodity,
                        'created_by': 'TradeBot'
                    })
                    
                    logger.info(f"✅ Trade executed: {action} {commodity} @ {price:.2f} (SL: {stop_loss:.2f}, TP: {take_profit:.2f})")
                    return True
                    
            except Exception as e:
                logger.error(f"Trade execution error on {platform}: {e}")
        
        return False
    
    async def _monitor_positions(self, settings: dict) -> int:
        """Überwacht alle offenen Positionen auf SL/TP"""
        from multi_platform_connector import multi_platform
        
        closed_count = 0
        active_platforms = settings.get('active_platforms', [])
        
        for platform in active_platforms:
            if 'MT5_' not in platform:
                continue
            
            try:
                # Hole offene Positionen von Plattform
                positions = await multi_platform.get_open_positions(platform)
                
                for pos in positions:
                    self.positions_checked += 1
                    
                    ticket = pos.get('ticket') or pos.get('id')
                    current_price = pos.get('currentPrice', pos.get('price', 0))
                    
                    # Hole Trade Settings aus DB
                    trade_settings = await self.db.trades_db.get_trade_settings(str(ticket))
                    
                    if not trade_settings:
                        continue
                    
                    stop_loss = trade_settings.get('stop_loss')
                    take_profit = trade_settings.get('take_profit')
                    trade_type = pos.get('type', 'BUY')
                    
                    if not current_price or not stop_loss or not take_profit:
                        continue
                    
                    # Prüfe SL/TP
                    should_close = False
                    close_reason = None
                    
                    if trade_type in ['BUY', 'POSITION_TYPE_BUY']:
                        if current_price <= stop_loss:
                            should_close = True
                            close_reason = 'STOP_LOSS'
                        elif current_price >= take_profit:
                            should_close = True
                            close_reason = 'TAKE_PROFIT'
                    else:  # SELL
                        if current_price >= stop_loss:
                            should_close = True
                            close_reason = 'STOP_LOSS'
                        elif current_price <= take_profit:
                            should_close = True
                            close_reason = 'TAKE_PROFIT'
                    
                    if should_close:
                        logger.info(f"🎯 Closing position {ticket}: {close_reason} @ {current_price:.2f}")
                        
                        # Position schließen
                        close_result = await multi_platform.close_position(platform, str(ticket))
                        
                        if close_result:
                            # V2.3.31: Speichere geschlossenen Trade in DB
                            closed_trade = {
                                'id': f"bot_{ticket}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                'mt5_ticket': str(ticket),
                                'commodity': pos.get('symbol', 'UNKNOWN'),
                                'type': 'BUY' if trade_type in ['BUY', 'POSITION_TYPE_BUY'] else 'SELL',
                                'entry_price': pos.get('openPrice', pos.get('price', 0)),
                                'exit_price': current_price,
                                'quantity': pos.get('volume', 0),
                                'profit_loss': pos.get('profit', 0),
                                'status': 'CLOSED',
                                'platform': platform,
                                'strategy': trade_settings.get('strategy', 'AI_BOT'),
                                'opened_at': pos.get('time', datetime.now(timezone.utc).isoformat()),
                                'closed_at': datetime.now(timezone.utc).isoformat(),
                                'closed_by': 'TradeBot',
                                'close_reason': close_reason
                            }
                            
                            try:
                                await self.db.trades_db.insert_trade(closed_trade)
                                logger.info(f"💾 ✅ Saved closed trade #{ticket} to DB (TradeBot)")
                            except Exception as e:
                                logger.error(f"❌ Failed to save closed trade: {e}")
                            
                            closed_count += 1
                            logger.info(f"✅ Position {ticket} closed: {close_reason} @ {current_price:.2f}")
                            
            except Exception as e:
                logger.error(f"Position monitoring error for {platform}: {e}")
        
        return closed_count
    
    def _calculate_lot_size(self, balance: float, risk_percent: float, price: float) -> float:
        """Berechnet Lot Size basierend auf Risiko"""
        risk_amount = balance * (risk_percent / 100)
        # Vereinfachte Berechnung - 0.01 Lot pro $100 Risk
        lot_size = max(0.01, min(1.0, risk_amount / 100))
        return round(lot_size, 2)
    
    def _get_mt5_symbol(self, commodity: str) -> str:
        """Konvertiert Commodity-Name zu MT5-Symbol - V2.3.32 erweitert"""
        symbol_map = {
            # Edelmetalle
            'GOLD': 'XAUUSD',
            'SILVER': 'XAGUSD',
            'PLATINUM': 'XPTUSD',
            'PALLADIUM': 'XPDUSD',
            # Energie
            'CRUDE_OIL': 'XTIUSD',
            'WTI_CRUDE': 'XTIUSD',
            'BRENT_CRUDE': 'XBRUSD',
            'NATURAL_GAS': 'XNGUSD',
            # Forex
            'EURUSD': 'EURUSD',
            'GBPUSD': 'GBPUSD',
            'USDJPY': 'USDJPY',
            'USDCHF': 'USDCHF',
            'AUDUSD': 'AUDUSD',
            'USDCAD': 'USDCAD',
            # Crypto
            'BTCUSD': 'BTCUSD',
            'BITCOIN': 'BTCUSD',
            'ETHUSD': 'ETHUSD',
            'ETHEREUM': 'ETHUSD',
            # Agrar - V2.3.32 FIX: Diese SIND handelbar, Markt kann nur geschlossen sein
            'WHEAT': 'WHEAT',
            'CORN': 'CORN', 
            'SOYBEANS': 'SOYBEAN',
            'COFFEE': 'COFFEE',
            'SUGAR': 'SUGAR',
            'COCOA': 'COCOA',
            'COTTON': 'COTTON',
            # Metalle
            'COPPER': 'XCUUSD',
        }
        return symbol_map.get(commodity, commodity)


# ============================================================================
# MULTI-BOT MANAGER
# ============================================================================

class MultiBotManager:
    """
    V2.3.31: Multi-Bot Manager
    Koordiniert alle 3 Bots und ermöglicht zentrale Steuerung
    """
    
    def __init__(self, db_manager, settings_getter):
        self.db = db_manager
        self.get_settings = settings_getter
        
        # Bots erstellen
        self.signal_bot = SignalBot(db_manager, settings_getter)
        self.market_bot = MarketBot(db_manager, settings_getter)
        self.trade_bot = TradeBot(db_manager, settings_getter, self.signal_bot)
        
        self._tasks = []
        self.is_running = False
        
        logger.info("🚀 MultiBotManager v2.3.31 initialized")
    
    async def start_all(self):
        """Alle Bots starten"""
        if self.is_running:
            logger.warning("Bots already running")
            return
        
        self.is_running = True
        
        # Bots als Tasks starten
        self._tasks = [
            asyncio.create_task(self.market_bot.run_forever()),
            asyncio.create_task(self.signal_bot.run_forever()),
            asyncio.create_task(self.trade_bot.run_forever())
        ]
        
        logger.info("✅ All bots started")
    
    async def stop_all(self):
        """Alle Bots stoppen"""
        self.is_running = False
        
        self.market_bot.stop()
        self.signal_bot.stop()
        self.trade_bot.stop()
        
        # Tasks abbrechen
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._tasks = []
        logger.info("⏹️ All bots stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Status aller Bots abrufen"""
        return {
            'manager_running': self.is_running,
            'bots': {
                'market_bot': self.market_bot.get_status(),
                'signal_bot': self.signal_bot.get_status(),
                'trade_bot': self.trade_bot.get_status()
            },
            'statistics': {
                'total_trades_executed': self.trade_bot.trades_executed,
                'total_trades_closed': self.trade_bot.trades_closed,
                'total_positions_checked': self.trade_bot.positions_checked,
                'pending_signals': len(self.signal_bot.pending_signals)
            }
        }
    
    async def run_single_cycle(self) -> Dict[str, Any]:
        """Führt einen einzelnen Zyklus aller Bots aus (für manuellen Trigger)"""
        results = {}
        
        results['market_bot'] = await self.market_bot.run_once()
        results['signal_bot'] = await self.signal_bot.run_once()
        results['trade_bot'] = await self.trade_bot.run_once()
        
        return results


# Export
__all__ = [
    'MultiBotManager', 'MarketBot', 'SignalBot', 'TradeBot', 'BaseBot'
]
