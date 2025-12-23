"""
🤖 Booner Trade v2.3.35 - Multi-Bot-System
==========================================
3 spezialisierte Bots für parallele Verarbeitung:
- MarketBot: Marktdaten sammeln, Indikatoren berechnen
- SignalBot: Signale analysieren, News auswerten, Strategien
- TradeBot: Trades ausführen, Positionen überwachen, SL/TP prüfen

V2.3.35: Market Regime System integriert
- Regime-Erkennung (Trend, Range, Volatilität, News)
- Strategie-Erlaubnis-Matrix
- Prioritäts-basierte Strategie-Auswahl
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

# V2.3.35: Market Regime System importieren
try:
    from market_regime import (
        MarketRegime, 
        detect_market_regime, 
        is_strategy_allowed,
        get_highest_priority_strategy,
        check_news_window,
        STRATEGY_PRIORITY
    )
    MARKET_REGIME_AVAILABLE = True
except ImportError:
    MARKET_REGIME_AVAILABLE = False
    MarketRegime = None

# 🆕 V2.5.0: Autonomous Trading Intelligence importieren
try:
    from autonomous_trading_intelligence import (
        autonomous_trading,
        MarketState,
        StrategyCluster
    )
    from self_learning_journal import trading_journal
    AUTONOMOUS_TRADING_AVAILABLE = True
except ImportError:
    AUTONOMOUS_TRADING_AVAILABLE = False
    autonomous_trading = None

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
        # V2.3.35 FIX: Korrektes Mapping zu COMMODITIES in commodity_processor.py
        self.commodities = ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 
                           'WTI_CRUDE', 'BRENT_CRUDE', 'NATURAL_GAS',
                           'WHEAT', 'CORN', 'SOYBEANS', 'COFFEE', 'SUGAR', 'COCOA',
                           'EURUSD', 'BITCOIN']
    
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
    - Ruft automatisch News ab und wertet sie aus
    - Führt Strategie-Analysen durch
    - Generiert BUY/SELL Signale
    """
    
    def __init__(self, db_manager, settings_getter):
        super().__init__("SignalBot", interval_seconds=20)
        self.db = db_manager
        self.get_settings = settings_getter
        self.pending_signals = []  # Queue für TradeBot
        self.last_news_fetch = None
        self.cached_news = []
        self.news_fetch_interval = 300  # News alle 5 Minuten abrufen
    
    async def execute(self) -> Dict[str, Any]:
        """Signale analysieren"""
        settings = await self.get_settings()
        
        if not settings:
            return {'success': False, 'error': 'No settings'}
        
        if not settings.get('auto_trading', False):
            return {'success': True, 'message': 'Auto-trading disabled', 'signals': 0}
        
        signals_generated = 0
        analyzed_count = 0
        
        # V2.3.35: Automatischer News-Abruf
        news_impact = await self._check_news_automatically()
        
        # Hole alle Marktdaten
        market_data = await self.db.market_db.get_market_data()
        
        # Aktive Strategien ermitteln
        active_strategies = self._get_active_strategies(settings)
        
        for data in market_data:
            commodity = data.get('commodity')
            if not commodity:
                continue
            
            analyzed_count += 1
            
            # V2.3.35: Prüfe ob News dieses Asset betreffen
            asset_news_block = self._check_asset_news_block(commodity, news_impact)
            if asset_news_block:
                logger.info(f"📰 {commodity}: Trading pausiert wegen News ({asset_news_block})")
                continue
            
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
                        signal['news_checked'] = True
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
            'active_strategies': active_strategies,
            'news_status': news_impact.get('status', 'unknown') if news_impact else 'not_checked'
        }
    
    async def _check_news_automatically(self) -> Optional[Dict]:
        """
        V2.3.35: Ruft News automatisch ab (alle 5 Minuten)
        und prüft ob wichtige News das Trading beeinflussen sollten
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Prüfe ob News-Abruf nötig ist
            if self.last_news_fetch:
                elapsed = (now - self.last_news_fetch).total_seconds()
                if elapsed < self.news_fetch_interval and self.cached_news:
                    # Verwende gecachte News
                    return self._analyze_news_impact(self.cached_news)
            
            # Hole neue News
            try:
                from news_analyzer import get_current_news, check_news_for_trade
                
                news_list = await get_current_news()
                self.cached_news = news_list
                self.last_news_fetch = now
                
                if news_list:
                    logger.info(f"📰 News aktualisiert: {len(news_list)} Artikel")
                    return self._analyze_news_impact(news_list)
                else:
                    return {'status': 'no_news', 'block_trading': False}
                    
            except ImportError:
                logger.debug("News analyzer not available")
                return None
            except Exception as e:
                logger.warning(f"News fetch error: {e}")
                return None
                
        except Exception as e:
            logger.debug(f"News check error: {e}")
            return None
    
    def _analyze_news_impact(self, news_list: List[Dict]) -> Dict:
        """Analysiert die Auswirkung der News auf das Trading"""
        if not news_list:
            return {'status': 'no_news', 'block_trading': False, 'affected_assets': []}
        
        high_impact_news = []
        affected_assets = set()
        
        for news in news_list:
            impact = news.get('impact', 'low')
            if impact in ['high', 'critical']:
                high_impact_news.append(news)
                # Extrahiere betroffene Assets aus dem Titel/Inhalt
                title = (news.get('title', '') + ' ' + news.get('content', '')).upper()
                
                # Prüfe welche Assets betroffen sind
                asset_keywords = {
                    'GOLD': ['GOLD', 'XAU', 'PRECIOUS METAL'],
                    'SILVER': ['SILVER', 'XAG'],
                    'BITCOIN': ['BITCOIN', 'BTC', 'CRYPTO'],
                    'EURUSD': ['EUR', 'EURO', 'ECB', 'EUROZONE', 'USD', 'DOLLAR', 'FED', 'FEDERAL RESERVE'],
                    'WTI_CRUDE': ['OIL', 'CRUDE', 'WTI', 'BRENT', 'OPEC', 'PETROLEUM'],
                }
                
                for asset, keywords in asset_keywords.items():
                    if any(kw in title for kw in keywords):
                        affected_assets.add(asset)
        
        return {
            'status': 'checked',
            'total_news': len(news_list),
            'high_impact_count': len(high_impact_news),
            'block_trading': len(high_impact_news) > 0,
            'affected_assets': list(affected_assets),
            'high_impact_news': high_impact_news[:3]  # Max 3 für Logging
        }
    
    def _check_asset_news_block(self, commodity: str, news_impact: Optional[Dict]) -> Optional[str]:
        """Prüft ob ein bestimmtes Asset wegen News blockiert werden soll"""
        if not news_impact:
            return None
        
        affected_assets = news_impact.get('affected_assets', [])
        
        if commodity in affected_assets:
            high_impact = news_impact.get('high_impact_news', [])
            if high_impact:
                return high_impact[0].get('title', 'High-impact news')[:50]
        
        return None
    
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
    
    async def _count_mt5_positions_for_commodity(self, commodity: str) -> int:
        """V2.3.36: Zählt offene MT5-Positionen für ein Commodity"""
        from multi_platform_connector import multi_platform
        
        count = 0
        
        # Symbol-Mapping für MT5
        symbol_map = {
            'GOLD': ['XAUUSD', 'GOLD'],
            'SILVER': ['XAGUSD', 'SILVER'],
            'WTI_CRUDE': ['USOUSD', 'WTIUSD', 'CL', 'OIL'],
            'BRENT_CRUDE': ['UKOUSD', 'BRENT'],
            'NATURAL_GAS': ['NGUSD', 'NATGAS'],
            'BITCOIN': ['BTCUSD', 'BTC'],
            'EURUSD': ['EURUSD'],
            'PLATINUM': ['XPTUSD', 'PLATINUM'],
            'PALLADIUM': ['XPDUSD', 'PALLADIUM'],
            'COPPER': ['COPPER', 'HG'],
            'CORN': ['CORN', 'ZC'],
            'WHEAT': ['WHEAT', 'ZW'],
            'SOYBEANS': ['SOYBEANS', 'ZS'],
            'COFFEE': ['COFFEE', 'KC'],
            'SUGAR': ['SUGAR', 'SB'],
            'COCOA': ['COCOA', 'CC']
        }
        
        mt5_symbols = symbol_map.get(commodity, [commodity])
        
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
            try:
                positions = await multi_platform.get_open_positions(platform_name)
                for pos in positions:
                    symbol = pos.get('symbol', '')
                    if any(s in symbol for s in mt5_symbols):
                        count += 1
            except Exception:
                pass
        
        return count
    
    async def _analyze_with_strategy(self, strategy: str, commodity: str, 
                                     data: dict, settings: dict) -> Optional[Dict]:
        """
        V2.3.35: VERBESSERTE Strategie-Analyse mit Chart-Trend-Erkennung
        
        Analysiert nicht nur aktuelle Werte, sondern auch:
        - Preisverlauf der letzten 1-2 Stunden
        - Trend-Stärke und -Richtung
        - Vermeidet Trades gegen starken Trend
        """
        
        # Einfache Analyse basierend auf RSI und Trend
        rsi = data.get('rsi', 50)
        trend = data.get('trend', 'neutral')
        signal = data.get('signal', 'HOLD')
        price = data.get('price', 0)
        
        if not price:
            return None
        
        # V2.3.35: CHART-TREND-ANALYSE
        # Hole historische Preise für echte Trend-Analyse
        chart_trend = await self._analyze_price_trend(commodity, price)
        
        # Wenn starker Trend erkannt wurde, vermeide Gegenposition!
        if chart_trend:
            trend_direction = chart_trend.get('direction')  # 'UP', 'DOWN', 'SIDEWAYS'
            trend_strength = chart_trend.get('strength', 0)  # 0-100
            price_change_percent = chart_trend.get('price_change_percent', 0)
            
            logger.info(f"📈 {commodity} Chart-Trend: {trend_direction} ({trend_strength}%), Änderung: {price_change_percent:+.2f}%")
            
            # WICHTIG: Blocke Trades gegen starken Trend!
            if trend_strength > 60:  # Starker Trend
                if trend_direction == 'UP' and signal == 'SELL':
                    logger.warning(f"🛑 SELL für {commodity} blockiert - starker Aufwärtstrend ({trend_strength}%, +{price_change_percent:.2f}%)")
                    return None
                elif trend_direction == 'DOWN' and signal == 'BUY':
                    logger.warning(f"🛑 BUY für {commodity} blockiert - starker Abwärtstrend ({trend_strength}%, {price_change_percent:.2f}%)")
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
            
            # V2.3.35: Berücksichtige Chart-Trend
            if chart_trend and chart_trend.get('direction') == 'UP':
                is_bullish = True
            elif chart_trend and chart_trend.get('direction') == 'DOWN':
                is_bearish = True
            
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
            
            # V2.3.35: Chart-Trend hat Priorität
            if chart_trend:
                if chart_trend.get('direction') == 'UP' and chart_trend.get('strength', 0) > 40:
                    is_bullish = True
                    is_bearish = False
                elif chart_trend.get('direction') == 'DOWN' and chart_trend.get('strength', 0) > 40:
                    is_bearish = True
                    is_bullish = False
            
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
                'chart_trend': chart_trend,
                'reason': f'{strategy}: RSI={rsi:.1f}, Trend={trend}, ChartTrend={chart_trend.get("direction") if chart_trend else "N/A"}'
            }
        
        return None
    
    async def _analyze_price_trend(self, commodity: str, current_price: float) -> Optional[Dict]:
        """
        V2.3.35: Analysiert den Preisverlauf der letzten 1-2 Stunden
        
        Returns:
            {
                'direction': 'UP' | 'DOWN' | 'SIDEWAYS',
                'strength': 0-100,
                'price_change_percent': float,
                'candles_up': int,
                'candles_down': int,
                'trend_duration_minutes': int
            }
        """
        try:
            # Hole historische Preise aus der DB
            history = await self.db.market_db.get_price_history(commodity, limit=30)
            
            if not history or len(history) < 5:
                return None
            
            # Berechne Trend
            prices = [h.get('price', h.get('close', 0)) for h in history if h.get('price') or h.get('close')]
            
            if len(prices) < 5:
                return None
            
            # Ältester Preis (vor 1-2 Stunden) vs aktueller Preis
            oldest_price = prices[-1] if prices else current_price
            price_change = current_price - oldest_price
            price_change_percent = (price_change / oldest_price * 100) if oldest_price > 0 else 0
            
            # Zähle aufsteigende vs absteigende Kerzen
            candles_up = 0
            candles_down = 0
            for i in range(1, len(prices)):
                if prices[i-1] > prices[i]:
                    candles_up += 1
                elif prices[i-1] < prices[i]:
                    candles_down += 1
            
            # Bestimme Richtung
            if price_change_percent > 0.5:
                direction = 'UP'
            elif price_change_percent < -0.5:
                direction = 'DOWN'
            else:
                direction = 'SIDEWAYS'
            
            # Trend-Stärke (0-100)
            # Basiert auf: Preisänderung + Kerzen-Ratio
            price_strength = min(abs(price_change_percent) * 20, 50)  # Max 50 aus Preis
            
            total_candles = candles_up + candles_down
            if total_candles > 0:
                if direction == 'UP':
                    candle_strength = (candles_up / total_candles) * 50
                elif direction == 'DOWN':
                    candle_strength = (candles_down / total_candles) * 50
                else:
                    candle_strength = 25  # Neutral
            else:
                candle_strength = 25
            
            strength = min(price_strength + candle_strength, 100)
            
            return {
                'direction': direction,
                'strength': round(strength, 1),
                'price_change_percent': round(price_change_percent, 2),
                'candles_up': candles_up,
                'candles_down': candles_down,
                'oldest_price': round(oldest_price, 2),
                'current_price': round(current_price, 2),
                'data_points': len(prices)
            }
            
        except Exception as e:
            logger.debug(f"Price trend analysis error for {commodity}: {e}")
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
        """V2.3.36: Führt ein Trading-Signal aus mit verbesserter Duplicate-Prevention"""
        from multi_platform_connector import multi_platform
        
        commodity = signal.get('commodity')
        action = signal.get('action')
        strategy = signal.get('strategy', 'day_trading')
        price = signal.get('price', 0)
        confidence = signal.get('confidence', 0)
        
        if not commodity or not action or action == 'HOLD':
            return False
        
        # V2.3.37 FIX: Asset-Cooldown prüfen mit automatischer Bereinigung
        if not hasattr(self, '_asset_cooldown'):
            self._asset_cooldown = {}
        
        # Bereinige alte Cooldowns (älter als 1 Stunde) um Memory Leak zu verhindern
        now = datetime.now()
        old_cooldowns = [k for k, v in self._asset_cooldown.items() if (now - v).total_seconds() > 3600]
        for k in old_cooldowns:
            del self._asset_cooldown[k]
        
        cooldown_minutes = 2  # Min. 2 Minuten zwischen gleichen Assets
        if strategy == 'scalping':
            cooldown_minutes = 1  # Für Scalping: 1 Minute
        
        last_trade_time = self._asset_cooldown.get(commodity)
        if last_trade_time:
            elapsed = (now - last_trade_time).total_seconds()
            if elapsed < cooldown_minutes * 60:
                logger.info(f"⏱️ {commodity}: Cooldown aktiv - nur {elapsed:.0f}s seit letztem Trade (min: {cooldown_minutes*60}s)")
                return False
        
        # Prüfe Duplicate (lokale DB)
        existing_count = await self.db.trades_db.count_open_trades(
            commodity=commodity, strategy=strategy
        )
        
        max_positions = settings.get(f'{strategy}_max_positions', 3)
        if existing_count >= max_positions:
            logger.info(f"⚠️ Max positions reached for {strategy}/{commodity}: {existing_count}/{max_positions}")
            return False
        
        # V2.3.36 FIX: Prüfe auch MT5 Positionen
        try:
            mt5_count = await self._count_mt5_positions_for_commodity(commodity)
            total_count = existing_count + mt5_count
            
            # Max 2 Positionen pro Asset GESAMT
            if total_count >= 2:
                logger.info(f"⚠️ Max GESAMT-Positionen für {commodity}: {total_count}/2")
                return False
        except Exception as e:
            logger.debug(f"MT5 position check error: {e}")
        
        # V2.3.31: Verwende Risk Manager für Risiko-Bewertung
        active_platforms = settings.get('active_platforms', [])
        
        # ═══════════════════════════════════════════════════════════════════
        # 🆕 V2.5.0: AUTONOMOUS TRADING INTELLIGENCE
        # Prüft ob Trade wirklich ausgeführt werden soll (80% Threshold!)
        # ═══════════════════════════════════════════════════════════════════
        if AUTONOMOUS_TRADING_AVAILABLE and autonomous_trading:
            try:
                # Hole Preishistorie für Markt-Analyse
                price_history = signal.get('price_history', [])
                if not price_history:
                    # Fallback: Erstelle minimale Historie
                    prices = [price] * 50
                    highs = [price * 1.001] * 50
                    lows = [price * 0.999] * 50
                else:
                    prices = [p.get('price', p.get('close', price)) for p in price_history[-100:]]
                    highs = [p.get('high', price) for p in price_history[-100:]]
                    lows = [p.get('low', price) for p in price_history[-100:]]
                
                # 1. MARKT-ZUSTAND ERKENNEN
                market_analysis = autonomous_trading.detect_market_state(prices, highs, lows)
                
                # 2. PRÜFE OB STRATEGIE ZUM MARKT PASST
                # V2.3.38: Neue Logik - blockiert nicht mehr, nur loggt Warnung
                strategy_suitable, suitability_reason = autonomous_trading.is_strategy_suitable_for_market(
                    strategy.replace('_trading', ''),  # z.B. "day_trading" -> "day"
                    market_analysis
                )
                
                # V2.3.38: Nur noch loggen, nicht mehr blockieren
                # Die Strategie-Eignung wird jetzt im Universal Confidence Score berücksichtigt
                if "OPTIMAL" in suitability_reason:
                    logger.info(f"✅ AUTONOMOUS: Strategie '{strategy}' OPTIMAL für Markt '{market_analysis.state.value}'")
                elif "AKZEPTABEL" in suitability_reason:
                    logger.info(f"⚠️ AUTONOMOUS: Strategie '{strategy}' AKZEPTABEL für Markt '{market_analysis.state.value}'")
                else:
                    logger.warning(f"⚠️ AUTONOMOUS: Strategie '{strategy}' nicht optimal für Markt '{market_analysis.state.value}'")
                    logger.info(f"   → Trade wird mit Penalty im Confidence Score fortgesetzt")
                
                # 3. HOLE NEWS-SENTIMENT
                news_sentiment = "neutral"
                high_impact_pending = False
                try:
                    from news_analyzer import news_analyzer
                    news_status = await news_analyzer.get_commodity_news_status(commodity)
                    news_sentiment = news_status.get('sentiment', 'neutral')
                    high_impact_pending = news_status.get('high_impact_pending', False)
                except:
                    pass
                
                # 4. BERECHNE UNIVERSAL CONFIDENCE SCORE
                confluence_count = signal.get('confluence_count', 0)
                if confluence_count == 0:
                    # Schätze Confluence aus Signal-Daten
                    confluence_count = min(3, len(signal.get('reasons', [])))
                
                universal_score = autonomous_trading.calculate_universal_confidence(
                    strategy=strategy.replace('_trading', ''),
                    signal=action,
                    indicators=signal.get('indicators', {}),
                    market_analysis=market_analysis,
                    trend_h1=market_analysis.trend_direction,
                    trend_h4=market_analysis.trend_direction,
                    trend_d1=market_analysis.trend_direction,
                    news_sentiment=news_sentiment,
                    high_impact_news_pending=high_impact_pending,
                    confluence_count=confluence_count
                )
                
                # 5. PRÜFE OB TRADE ERLAUBT (Dynamischer Threshold)
                if not universal_score.passed_threshold:
                    dynamic_thresh = universal_score.details.get('dynamic_threshold', 65)
                    logger.warning(f"⛔ AUTONOMOUS: Universal Score {universal_score.total_score:.1f}% < {dynamic_thresh}% (Markt: {market_analysis.state.value})")
                    logger.warning(f"   Bonuses: {universal_score.bonuses}")
                    logger.warning(f"   Penalties: {universal_score.penalties}")
                    return False
                
                dynamic_thresh = universal_score.details.get('dynamic_threshold', 65)
                logger.info(f"✅ AUTONOMOUS: Trade ERLAUBT mit Score {universal_score.total_score:.1f}% >= {dynamic_thresh}%")
                
            except Exception as e:
                logger.warning(f"⚠️ Autonomous Trading Check fehlgeschlagen: {e}")
        # ═══════════════════════════════════════════════════════════════════
        
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
                free_margin = account_info.get('freeMargin', account_info.get('free_margin', 0))
                
                # =====================================================
                # V2.3.35: VEREINFACHTE PORTFOLIO-RISIKO-BERECHNUNG
                # Risiko = Gesamt-Margin / Balance × 100
                # Das ist die korrekte und einfache Berechnung!
                # =====================================================
                MAX_PORTFOLIO_RISK_PERCENT = 20.0
                
                current_risk_percent = (margin_used / balance * 100) if balance > 0 else 0
                
                logger.info(f"📊 {platform}: Balance €{balance:,.2f}, Margin €{margin_used:,.2f}, Risiko {current_risk_percent:.1f}%")
                
                # Prüfe ob bereits über 20%
                if current_risk_percent >= MAX_PORTFOLIO_RISK_PERCENT:
                    logger.warning(
                        f"🛑 TRADE BLOCKIERT - Portfolio-Risiko bereits bei {current_risk_percent:.1f}% "
                        f"(Max: {MAX_PORTFOLIO_RISK_PERCENT}%) | Margin: €{margin_used:,.2f} / Balance: €{balance:,.2f}"
                    )
                    continue
                
                # =====================================================
                # V2.3.35: BALANCE-BASIERTE RISIKOANPASSUNG
                # Bei niedriger Balance wird das Risiko automatisch reduziert
                # =====================================================
                balance_risk_multiplier = 1.0
                
                if balance < 1000:
                    balance_risk_multiplier = 0.25
                    logger.warning(f"⚠️ Niedrige Balance ({balance:.0f}€) - Risiko auf 25% reduziert")
                elif balance < 5000:
                    balance_risk_multiplier = 0.5
                    logger.info(f"📉 Balance unter 5000€ ({balance:.0f}€) - Risiko auf 50% reduziert")
                elif balance < 10000:
                    balance_risk_multiplier = 0.75
                
                # Berechne Lot Size basierend auf Risk per Trade
                risk_percent = settings.get(f'{strategy}_risk_percent', 1)
                adjusted_risk_percent = risk_percent * balance_risk_multiplier
                lot_size = self._calculate_lot_size(balance, adjusted_risk_percent, price)
                
                # =====================================================
                # V2.3.35: PRÜFE OB NEUER TRADE 20% ÜBERSCHREITEN WÜRDE
                # Schätze die zusätzliche Margin für den neuen Trade
                # =====================================================
                try:
                    # Geschätzte Margin für neuen Trade (vereinfacht: Lot × Preis / Leverage)
                    leverage = account_info.get('leverage', 100)
                    estimated_new_margin = (lot_size * price * 100) / leverage  # *100 für Standard-Lot
                    
                    new_total_margin = margin_used + estimated_new_margin
                    new_risk_percent = (new_total_margin / balance * 100) if balance > 0 else 0
                    
                    # Wenn neuer Trade 20% überschreiten würde
                    if new_risk_percent > MAX_PORTFOLIO_RISK_PERCENT:
                        # Berechne maximale erlaubte zusätzliche Margin
                        max_additional_margin = (balance * MAX_PORTFOLIO_RISK_PERCENT / 100) - margin_used
                        
                        if max_additional_margin <= 0:
                            logger.warning(f"🛑 TRADE BLOCKIERT - Kein Margin-Budget mehr verfügbar!")
                            continue
                        
                        # Berechne reduzierte Lot-Size
                        old_lot_size = lot_size
                        max_lot_size = (max_additional_margin * leverage) / (price * 100) if price > 0 else 0.01
                        lot_size = max(0.01, round(max_lot_size, 2))
                        
                        # Neuberechnung
                        estimated_new_margin = (lot_size * price * 100) / leverage
                        new_total_margin = margin_used + estimated_new_margin
                        new_risk_percent = (new_total_margin / balance * 100) if balance > 0 else 0
                        
                        # Wenn TROTZDEM über 20%, blockiere
                        if new_risk_percent > MAX_PORTFOLIO_RISK_PERCENT:
                            logger.warning(
                                f"🛑 TRADE BLOCKIERT - Auch mit minimaler Lot-Size ({lot_size}) "
                                f"würde Risiko {new_risk_percent:.1f}% > {MAX_PORTFOLIO_RISK_PERCENT}% sein!"
                            )
                            continue
                        
                        logger.warning(
                            f"📉 LOT-SIZE ANGEPASST: {old_lot_size:.2f} → {lot_size:.2f} "
                            f"(Risiko: {current_risk_percent:.1f}% → {new_risk_percent:.1f}%)"
                        )
                    
                    logger.info(
                        f"✅ Trade erlaubt: Lot {lot_size}, Risiko {current_risk_percent:.1f}% → {new_risk_percent:.1f}%"
                    )
                    
                except Exception as risk_calc_error:
                    logger.warning(f"⚠️ Risiko-Berechnung fehlgeschlagen: {risk_calc_error}")
                # =====================================================
                
                # V2.3.35: Global Drawdown Management - Auto-Reduktion
                try:
                    from risk_manager import drawdown_manager
                    drawdown_adjustment = await drawdown_manager.calculate_adjustment(platform, equity)
                    
                    # Prüfe ob Trade übersprungen werden soll (Frequenz-Reduktion)
                    if drawdown_manager.should_skip_trade(drawdown_adjustment):
                        logger.warning(f"⏸️ Trade übersprungen wegen Drawdown ({drawdown_adjustment.warning_level}): {drawdown_adjustment.reason}")
                        continue
                    
                    # Position Size anpassen
                    original_lot_size = lot_size
                    lot_size = drawdown_manager.apply_to_lot_size(lot_size, drawdown_adjustment)
                    
                    if lot_size < original_lot_size:
                        logger.info(f"📉 Lot size reduziert: {original_lot_size} → {lot_size} ({drawdown_adjustment.warning_level})")
                        
                except ImportError:
                    logger.debug("Drawdown Manager not available")
                
                # Berechne SL/TP
                sl_percent = settings.get(f'{strategy.replace("_trading", "")}_stop_loss_percent', 2)
                tp_percent = settings.get(f'{strategy.replace("_trading", "")}_take_profit_percent', 4)
                
                if action == 'BUY':
                    stop_loss = price * (1 - sl_percent / 100)
                    take_profit = price * (1 + tp_percent / 100)
                else:
                    stop_loss = price * (1 + sl_percent / 100)
                    take_profit = price * (1 - tp_percent / 100)
                
                # Trade ausführen - V2.3.34 FIX: Plattform-spezifisches Symbol
                mt5_symbol = self._get_mt5_symbol(commodity, platform)
                logger.info(f"📋 Using symbol {mt5_symbol} for {commodity} on {platform}")
                    
                trade_result = await multi_platform.execute_trade(
                    platform_name=platform,
                    symbol=mt5_symbol,
                    action=action,
                    volume=lot_size,
                    stop_loss=None,   # KI überwacht SL/TP
                    take_profit=None
                )
                
                if trade_result and trade_result.get('success'):
                    mt5_ticket = trade_result.get('ticket')
                    
                    # V2.3.32 FIX: Strategie in ticket_strategy_map speichern ZUERST
                    if mt5_ticket:
                        try:
                            await self.db.trades_db.save_ticket_strategy(
                                mt5_ticket=str(mt5_ticket),
                                strategy=strategy,
                                commodity=commodity,
                                platform=platform
                            )
                            logger.info(f"📋 Saved ticket-strategy map: {mt5_ticket} -> {strategy}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not save ticket-strategy map: {e}")
                    
                    # Trade in DB speichern - V2.3.32: Alle wichtigen Felder inkl. symbol
                    trade_id = await self.db.trades_db.insert_trade({
                        'commodity': commodity,
                        'symbol': mt5_symbol,  # V2.3.32 FIX: Symbol hinzugefügt
                        'type': action,
                        'price': price,
                        'entry_price': price,
                        'quantity': lot_size,
                        'status': 'OPEN',
                        'platform': platform,
                        'strategy': strategy,  # Strategie aus Signal
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'mt5_ticket': mt5_ticket,
                        'opened_at': datetime.now(timezone.utc).isoformat(),
                        'opened_by': 'TradeBot',
                        'strategy_signal': signal.get('reason', '')
                    })
                    
                    logger.info(f"✅ Trade created: {mt5_symbol} {action} with strategy={strategy}")
                    
                    # V2.3.38 FIX: Trade Settings mit trade_id Format speichern
                    # trade_settings_manager und _monitor_positions suchen nach diesem Format
                    trade_settings_id = f"mt5_{mt5_ticket}"
                    await self.db.trades_db.save_trade_settings(trade_settings_id, {
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'strategy': strategy,
                        'entry_price': price,
                        'platform': platform,
                        'commodity': commodity,
                        'created_by': 'TradeBot',
                        'type': action,
                        'mt5_ticket': str(mt5_ticket)  # Original Ticket für Referenz
                    })
                    
                    # V2.3.36 FIX: Setze Cooldown für dieses Asset
                    self._asset_cooldown[commodity] = datetime.now()
                    
                    logger.info(f"✅ Trade executed: {action} {commodity} @ {price:.2f} (SL: {stop_loss:.2f}, TP: {take_profit:.2f})")
                    logger.info(f"   Settings gespeichert als: {trade_settings_id}")
                    logger.info(f"🔒 Cooldown gesetzt für {commodity}")
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
                    open_price = pos.get('openPrice', pos.get('price', 0))
                    
                    # Hole Trade Settings aus DB
                    trade_settings = await self.db.trades_db.get_trade_settings(str(ticket))
                    
                    if not trade_settings:
                        # V2.3.38: Kein Settings gefunden = neuer Trade, nicht schließen!
                        logger.debug(f"⏭️ Position {ticket}: Keine Settings gefunden - übersprungen")
                        continue
                    
                    stop_loss = trade_settings.get('stop_loss')
                    take_profit = trade_settings.get('take_profit')
                    trade_type = pos.get('type', trade_settings.get('type', 'BUY'))
                    
                    if not current_price or not stop_loss or not take_profit:
                        logger.debug(f"⏭️ Position {ticket}: Unvollständige Daten (Price:{current_price}, SL:{stop_loss}, TP:{take_profit})")
                        continue
                    
                    # V2.3.38: Sicherheitscheck - Trade muss mindestens 30 Sekunden offen sein
                    trade_time = pos.get('time')
                    if trade_time:
                        try:
                            from dateutil.parser import parse as parse_date
                            opened_at = parse_date(trade_time) if isinstance(trade_time, str) else trade_time
                            age_seconds = (datetime.now(timezone.utc) - opened_at.replace(tzinfo=timezone.utc)).total_seconds()
                            if age_seconds < 30:
                                logger.debug(f"⏭️ Position {ticket}: Zu jung ({age_seconds:.0f}s < 30s) - übersprungen")
                                continue
                        except:
                            pass
                    
                    # Prüfe SL/TP
                    should_close = False
                    close_reason = None
                    
                    if trade_type in ['BUY', 'POSITION_TYPE_BUY']:
                        if current_price <= stop_loss:
                            should_close = True
                            close_reason = 'STOP_LOSS'
                            logger.info(f"🎯 BUY Position {ticket}: Price {current_price:.2f} <= SL {stop_loss:.2f}")
                        elif current_price >= take_profit:
                            should_close = True
                            close_reason = 'TAKE_PROFIT'
                            logger.info(f"🎯 BUY Position {ticket}: Price {current_price:.2f} >= TP {take_profit:.2f}")
                    else:  # SELL
                        if current_price >= stop_loss:
                            should_close = True
                            close_reason = 'STOP_LOSS'
                            logger.info(f"🎯 SELL Position {ticket}: Price {current_price:.2f} >= SL {stop_loss:.2f}")
                        elif current_price <= take_profit:
                            should_close = True
                            close_reason = 'TAKE_PROFIT'
                            logger.info(f"🎯 SELL Position {ticket}: Price {current_price:.2f} <= TP {take_profit:.2f}")
                    
                    if should_close:
                        logger.info(f"🎯 Closing position {ticket}: {close_reason} @ {current_price:.2f} (Entry: {open_price:.2f})")
                        
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
    
    def _get_mt5_symbol(self, commodity: str, platform: str = None) -> str:
        """
        Konvertiert Commodity-Name zu MT5-Symbol
        V2.3.34 FIX: Berücksichtigt jetzt die Plattform (Libertex vs ICMarkets)
        """
        # V2.3.34: Nutze COMMODITIES dict für korrekte plattform-spezifische Symbole
        try:
            import commodity_processor
            commodity_info = commodity_processor.COMMODITIES.get(commodity, {})
            
            if platform and 'ICMARKETS' in platform:
                # ICMarkets Symbol
                symbol = commodity_info.get('mt5_icmarkets_symbol')
                if symbol:
                    return symbol
            
            # Libertex oder Fallback
            symbol = commodity_info.get('mt5_libertex_symbol')
            if symbol:
                return symbol
        except Exception as e:
            logger.warning(f"Could not get symbol from COMMODITIES: {e}")
        
        # Fallback: Alte Mapping-Tabelle (hauptsächlich für Libertex)
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
            # Agrar (Libertex-Symbole)
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
