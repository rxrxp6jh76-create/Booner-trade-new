"""
🤖 Booner Trade v2.5.0 - Multi-Bot-System (Ultimate AI Upgrade)
================================================================
3 spezialisierte Bots für parallele Verarbeitung:
- MarketBot: Marktdaten sammeln, Indikatoren berechnen
- SignalBot: Signale analysieren, News auswerten, Strategien
- TradeBot: Trades ausführen, Positionen überwachen, SL/TP prüfen

V2.5.0: Ultimate AI Upgrade
- Asset-Class Specific Logic (Commodities, Forex, BTC)
- DXY Correlation Guard für EUR/USD
- BTC Volatility Squeeze Filter
- Anti-Cluster USD Exposure Guard
- Spread-to-Profit Ratio Guard
- Equity Curve Protection
- Pattern Blacklisting
- ATR-basierte dynamische SL/TP
"""

import asyncio
import logging
import time  # V2.5.0: Für Latency Tracking
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import numpy as np  # V2.5.0: Für ATR und Asset-Analyse

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

# 🆕 V2.3.39: Advanced Filters importieren
try:
    from advanced_filters import MasterFilter, FilterResult
    from enhanced_self_learning import enhanced_learning, TradeContext
    ADVANCED_FILTERS_AVAILABLE = True
except ImportError:
    ADVANCED_FILTERS_AVAILABLE = False
    MasterFilter = None
    enhanced_learning = None

# 🆕 V2.3.39: Market Hours importieren
try:
    from commodity_market_hours import is_market_open, DEFAULT_MARKET_HOURS
    MARKET_HOURS_AVAILABLE = True
except ImportError:
    MARKET_HOURS_AVAILABLE = False
    is_market_open = None

logger = logging.getLogger(__name__)

# 🆕 V2.5.0: macOS Process Manager importieren
try:
    from macos_process_manager import (
        CPUThrottleManager,
        ProcessKiller,
        MemoryManager,
        TimeoutWrapper,
        LatencyTracker,
        PSUTIL_AVAILABLE
    )
    MACOS_MANAGER_AVAILABLE = True
    logger.info("✅ macOS Process Manager geladen (M4 Optimierungen aktiv)")
except ImportError:
    MACOS_MANAGER_AVAILABLE = False
    PSUTIL_AVAILABLE = False
    logger.warning("⚠️ macOS Process Manager nicht verfügbar")


# ═══════════════════════════════════════════════════════════════════════════
# V2.5.0: FORCE RELOAD FUNKTION (macOS)
# ═══════════════════════════════════════════════════════════════════════════

async def force_reload_macos() -> Dict:
    """
    macOS Force Reload:
    - Beendet Zombie-Prozesse mit SIGKILL
    - Memory Cleanup
    - Garbage Collection
    """
    if not MACOS_MANAGER_AVAILABLE:
        logger.warning("⚠️ Force Reload nicht verfügbar (kein macOS Manager)")
        return {'success': False, 'reason': 'macOS Manager nicht verfügbar'}
    
    try:
        result = ProcessKiller.force_reload()
        logger.info(f"🔄 macOS Force Reload: {result}")
        return {'success': True, **result}
    except Exception as e:
        logger.error(f"Force Reload Fehler: {e}")
        return {'success': False, 'error': str(e)}


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
        
        # V2.5.0: Iteration Counter für periodische Cleanups
        iteration_count = 0
        
        while self.is_running:
            try:
                # V2.5.0: Latenz-Tracking Start
                start_time = time.time() if 'time' in dir() else None
                
                await self.run_once()
                
                # V2.5.0: Latenz-Tracking Ende
                if start_time and MACOS_MANAGER_AVAILABLE:
                    latency_ms = (time.time() - start_time) * 1000
                    LatencyTracker.record_latency(latency_ms)
                
                # V2.5.0: CPU Throttle für M4 Mac (KRITISCH!)
                if MACOS_MANAGER_AVAILABLE:
                    await CPUThrottleManager.async_throttle()
                else:
                    await asyncio.sleep(0.1)  # Fallback: 100ms Pause
                
                await asyncio.sleep(self.interval)
                
                iteration_count += 1
                
                # V2.5.0: Periodischer Memory Cleanup (alle 100 Iterationen)
                if iteration_count % 100 == 0 and MACOS_MANAGER_AVAILABLE:
                    MemoryManager.check_memory_health()
                    MemoryManager.cleanup_tracked_objects()
                    logger.debug(f"🧹 Periodic cleanup after {iteration_count} iterations")
                    
            except asyncio.CancelledError:
                logger.info(f"🛑 {self.name} cancelled")
                break
            except Exception as e:
                logger.error(f"❌ {self.name} loop error: {e}")
                # V2.5.0: Bei Fehler auch CPU Throttle
                if MACOS_MANAGER_AVAILABLE:
                    await CPUThrottleManager.async_throttle()
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
        
        # V3.0.0: Hole aktuelle 4-Säulen-Confidence-Scores
        confidence_scores = await self._get_confidence_scores(settings)
        logger.info(f"📊 4-Pillar Confidence Scores geladen: {len(confidence_scores)} Assets")
        
        # Debug: Zeige grüne Assets
        green_assets = [k for k, v in confidence_scores.items() if v.get('status') == 'green']
        if green_assets:
            logger.info(f"🟢 Grüne Assets für 4-Pillar Trading: {green_assets}")
        
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
            
            # V3.0.0: Prüfe 4-Säulen-Confidence für automatische Signal-Generierung
            confidence_data = confidence_scores.get(commodity, {})
            confidence = confidence_data.get('confidence', 0)
            confidence_status = confidence_data.get('status', 'red')
            threshold = confidence_data.get('threshold', 68)
            
            # Wenn grünes Signal (Confidence >= Threshold), generiere Trade-Signal
            if confidence_status == 'green' and confidence >= threshold:
                # Bestimme Richtung basierend auf RSI und Trend
                rsi = data.get('rsi', 50)
                trend = data.get('trend', 'NEUTRAL')
                signal_field = data.get('signal', 'HOLD')  # Signal aus Marktdaten
                
                action = None
                # V3.0.0: Nutze das berechnete Signal-Feld, das bereits die korrekte Logik enthält
                if signal_field == 'BUY':
                    action = 'BUY'
                elif signal_field == 'SELL':
                    action = 'SELL'
                # Fallback auf RSI wenn Signal HOLD ist
                elif rsi is not None and rsi < 35:  # Stark überverkauft
                    action = 'BUY'
                elif rsi is not None and rsi > 65:  # Stark überkauft
                    action = 'SELL'
                
                if action:
                    signal = {
                        'action': action,
                        'commodity': commodity,
                        'strategy': 'autonomous_4pillar',
                        'confidence': confidence / 100,  # Normalisiert 0-1
                        'price': data.get('price', 0),
                        'generated_at': datetime.now(timezone.utc).isoformat(),
                        'reason': f"4-Säulen-Score: {confidence}% (Threshold: {threshold}%)",
                        'news_checked': True,
                        # V3.0.0: Füge Indikatoren hinzu für AUTONOMOUS Check
                        'indicators': {
                            'rsi': data.get('rsi', 50),
                            'macd': data.get('macd', 0),
                            'macd_signal': data.get('macd_signal', 0),
                            'adx': data.get('adx', 25),
                            'atr': data.get('atr', 0),
                            'bollinger_upper': data.get('bollinger_upper', 0),
                            'bollinger_lower': data.get('bollinger_lower', 0),
                        },
                        # V3.0.0: Markiere als 4-Pillar verifiziert (überspringt AUTONOMOUS Check)
                        'skip_autonomous_check': True,
                        '4pillar_verified': True,
                        '4pillar_score': confidence
                    }
                    self.pending_signals.append(signal)
                    signals_generated += 1
                    logger.info(f"🟢 4-Säulen Signal: {action} {commodity} ({confidence}% >= {threshold}%)")
                    continue  # Keine weitere Strategie-Analyse nötig
            
            # Analysiere mit jeder aktiven Strategie (für nicht-grüne Signale)
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
    
    async def _get_confidence_scores(self, settings: dict) -> Dict[str, Dict]:
        """
        V3.0.0: Holt die aktuellen 4-Säulen-Confidence-Scores für alle Assets.
        Nutzt die gleiche Logik wie /api/signals/status für Konsistenz.
        """
        try:
            confidence_scores = {}
            trading_mode = settings.get('trading_mode', 'conservative')
            
            # Hole alle Marktdaten
            market_data = await self.db.market_db.get_market_data()
            logger.info(f"   _get_confidence_scores: {len(market_data) if market_data else 0} market_data Einträge")
            
            for data in market_data:
                commodity = data.get('commodity')
                if not commodity:
                    continue
                
                try:
                    # V3.0.0: Einfache Confidence-Berechnung basierend auf RSI, ADX, MACD
                    rsi = data.get('rsi', 50)
                    adx = data.get('adx', 25)
                    macd = data.get('macd', 0)
                    macd_signal = data.get('macd_signal', 0)
                    atr = data.get('atr', 0)
                    price = data.get('price', 0)
                    
                    # Basis-Score: RSI-basiert (30 = überverkauft gut für BUY, 70 = überkauft gut für SELL)
                    if rsi is None:
                        rsi = 50
                    
                    base_score = 0
                    if rsi < 35:  # Überverkauft - BUY Signal
                        base_score = 70 + (35 - rsi)  # 70-100
                    elif rsi > 65:  # Überkauft - SELL Signal
                        base_score = 70 + (rsi - 65)  # 70-100
                    else:  # Neutral
                        base_score = 40 + abs(50 - rsi) / 2  # 40-55
                    
                    # ADX Bonus (>25 = starker Trend)
                    adx_bonus = 0
                    if adx is not None and adx > 25:
                        adx_bonus = min(15, (adx - 25) / 2)
                    
                    # MACD Bonus (Divergenz)
                    macd_bonus = 0
                    if macd is not None and macd_signal is not None:
                        macd_diff = macd - macd_signal
                        if abs(macd_diff) > 0:
                            macd_bonus = min(10, abs(macd_diff) * 5)
                    
                    # ATR/Volatility Check
                    volatility_penalty = 0
                    if atr is not None and price > 0:
                        atr_percent = (atr / price) * 100
                        if atr_percent > 5:  # Sehr hohe Volatilität
                            volatility_penalty = 10
                    
                    # Gesamt-Confidence
                    confidence = min(100, max(0, base_score + adx_bonus + macd_bonus - volatility_penalty))
                    
                    # Threshold basierend auf Trading-Modus
                    if trading_mode == 'aggressive':
                        threshold = 58
                    elif trading_mode == 'conservative':
                        threshold = 72
                    else:  # standard
                        threshold = 65
                    
                    # Status bestimmen
                    if confidence >= threshold:
                        status = 'green'
                        logger.info(f"   🟢 {commodity}: conf={confidence:.0f}% >= thresh={threshold} → GREEN (RSI={rsi:.1f})")
                    elif confidence >= threshold - 10:
                        status = 'yellow'
                    else:
                        status = 'red'
                    
                    confidence_scores[commodity] = {
                        'confidence': confidence,
                        'threshold': threshold,
                        'status': status,
                        'rsi': rsi
                    }
                    
                except Exception as e:
                    logger.debug(f"Confidence calc error for {commodity}: {e}")
                    confidence_scores[commodity] = {
                        'confidence': 0,
                        'threshold': 68,
                        'status': 'red',
                        'reasons': [str(e)]
                    }
            
            return confidence_scores
            
        except Exception as e:
            logger.error(f"Error getting confidence scores: {e}")
            return {}
    
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
            'COCOA': ['COCOA', 'CC'],
            # V3.0.0: Neue Assets
            'ZINC': ['ZINC', 'ZN'],
            'USDJPY': ['USDJPY'],
            'ETHEREUM': ['ETHUSD', 'ETH'],
            'NASDAQ100': ['USTEC', 'NDX']
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
            
            logger.info(f"🔄 TradeBot: {len(pending_signals)} Signale zu verarbeiten")
            
            for signal in pending_signals:
                try:
                    logger.info(f"📤 TradeBot verarbeitet: {signal.get('commodity')} {signal.get('action')} via {signal.get('strategy')}")
                    executed = await self._execute_signal(signal, settings)
                    if executed:
                        result['trades_executed'] += 1
                        self.trades_executed += 1
                        logger.info(f"✅ Trade erfolgreich ausgeführt für {signal.get('commodity')}")
                except Exception as e:
                    logger.error(f"Signal execution error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        
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
        
        logger.info(f"🎯 _execute_signal: {commodity} {action} (strategy={strategy}, confidence={confidence})")
        
        if not commodity or not action or action == 'HOLD':
            logger.info(f"⏭️ Signal übersprungen: {commodity} {action} (kein gültiges Signal)")
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
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.3.39: MARKET HOURS CHECK - Handelszeiten aus Settings beachten
        # ═══════════════════════════════════════════════════════════════════
        settings = await self.get_settings()
        respect_market_hours = settings.get('respect_market_hours', True)
        
        if respect_market_hours and MARKET_HOURS_AVAILABLE and is_market_open:
            try:
                market_open = is_market_open(commodity)
                
                if not market_open:
                    logger.info(f"🕐 {commodity}: Markt geschlossen - kein Trade möglich")
                    logger.info("   Handelszeiten werden respektiert (respect_market_hours=True)")
                    return False
                else:
                    logger.debug(f"✅ {commodity}: Markt offen")
                    
            except Exception as e:
                logger.warning(f"⚠️ Market Hours Check Fehler für {commodity}: {e}")
                # Bei Fehler: Trade erlauben (Sicherheit)
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.3.39: STRIKTE POSITION-LIMIT PRÜFUNG
        # WICHTIG: NUR MT5 als Quelle der Wahrheit - KEIN doppelter Trade pro Asset!
        # ═══════════════════════════════════════════════════════════════════
        try:
            # Hole ALLE MT5 Positionen direkt
            mt5_positions = await self._get_all_mt5_positions()
            mt5_symbol = self._get_mt5_symbol(commodity)
            
            # Zähle existierende Positionen für dieses Symbol
            existing_positions = [p for p in mt5_positions if p.get('symbol') == mt5_symbol]
            mt5_count = len(existing_positions)
            
            # V2.3.39: STRENGES LIMIT - MAX 1 POSITION PRO ASSET!
            if mt5_count >= 1:
                logger.warning(f"⛔ POSITION-LIMIT: {commodity} ({mt5_symbol}) hat bereits {mt5_count} offene Position(en)")
                logger.warning("   → Kein neuer Trade erlaubt (Max: 1 pro Asset)")
                return False
            
            # V3.0.0: Positions-Limit aus Settings oder unbegrenzt (20% Balance-Regel gilt)
            # Das Risiko wird durch die 20% Balance-Regel pro Trade begrenzt
            total_positions = len(mt5_positions)
            MAX_TOTAL_POSITIONS = settings.get('max_positions', 50)  # Default: 50 (praktisch unbegrenzt)
            if total_positions >= MAX_TOTAL_POSITIONS:
                logger.warning(f"⛔ GESAMT-LIMIT: Bereits {total_positions}/{MAX_TOTAL_POSITIONS} Positionen offen")
                return False
                
            logger.info(f"✅ Position-Check OK: {commodity} hat 0 offene Positionen (Gesamt: {total_positions}/{MAX_TOTAL_POSITIONS})")
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Position-Check: {e}")
            # Bei Fehler: KEIN Trade - Sicherheit geht vor!
            return False
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.5.0: ASSET-CLASS SPECIFIC ANALYSIS
        # ═══════════════════════════════════════════════════════════════════
        asset_adjustment = 0
        asset_reasons = []
        prices = []  # V2.6.0 FIX: Initialisiere prices als leere Liste
        try:
            from autonomous_trading_intelligence import AssetClassAnalyzer, AssetClass
            
            # ATR berechnen wenn Preise verfügbar
            atr_ratio = 1.0
            volume_spike = False
            
            # V2.6.0 FIX: Hole historische Preise aus der Datenbank
            try:
                import database as db_module
                price_history = await db_module.market_data.find_one({"commodity": commodity})
                if price_history and 'price_history' in price_history:
                    prices = price_history.get('price_history', [])[-50:]  # Letzte 50 Preise
            except Exception:
                pass
            
            if prices and len(prices) >= 20:
                # Einfache ATR Approximation
                price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
                atr = np.mean(price_changes[-14:]) if len(price_changes) >= 14 else np.mean(price_changes)
                avg_atr = np.mean(price_changes) if price_changes else 1
                atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0
            
            # Asset-spezifische Gewichtung
            asset_adjustment, asset_reasons = AssetClassAnalyzer.apply_asset_weights(
                commodity=commodity,
                base_confidence=0,  # Wird separat berechnet
                volume_spike=volume_spike,
                atr_ratio=atr_ratio,
                strategy=strategy
            )
            
            logger.info(f"🎯 Asset-Class ({AssetClassAnalyzer.get_asset_class(commodity).value}): {asset_reasons}")
            
        except Exception as e:
            logger.debug(f"Asset-Class Analyse nicht verfügbar: {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.5.0: ADVANCED FILTERS (inkl. DXY, BTC Squeeze, Anti-Cluster)
        # ═══════════════════════════════════════════════════════════════════
        filter_result = None
        if ADVANCED_FILTERS_AVAILABLE and MasterFilter:
            try:
                from multi_platform_connector import multi_platform
                
                # Hole Bid/Ask Preise
                bid = price * 0.9995  # Approximation wenn nicht verfügbar
                ask = price * 1.0005
                
                # V2.6.0 FIX: Hole active_platforms aus settings
                current_settings = await self.get_settings()
                current_active_platforms = current_settings.get('active_platforms', ['MT5_LIBERTEX_DEMO'])
                
                # Versuche echte Bid/Ask zu holen
                try:
                    account_info = await multi_platform.get_account_info(current_active_platforms[0] if current_active_platforms else 'MT5_LIBERTEX_DEMO')
                except Exception:
                    pass
                
                # V2.5.0: Berechne dynamische SL/TP basierend auf ATR
                try:
                    from autonomous_trading_intelligence import AssetClassAnalyzer
                    atr_value = price * 0.02  # Fallback: 2% des Preises
                    if prices and len(prices) >= 20:
                        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
                        atr_value = np.mean(price_changes[-14:]) if len(price_changes) >= 14 else price * 0.02
                    
                    dynamic_sl, dynamic_tp = AssetClassAnalyzer.get_dynamic_sl_tp(
                        commodity=commodity,
                        atr=atr_value,
                        direction=action,
                        entry_price=price
                    )
                    logger.info(f"📊 Dynamische SL/TP (ATR-basiert): SL=${dynamic_sl:.2f}, TP=${dynamic_tp:.2f}")
                except Exception:
                    dynamic_sl, dynamic_tp = None, None
                
                # Führe alle Filter aus (V2.5.0 erweitert)
                filter_result = await MasterFilter.run_all_filters(
                    commodity=commodity,
                    signal=action,
                    current_price=price,
                    bid=bid,
                    ask=ask,
                    recent_prices=prices if prices else [],
                    open_positions=mt5_positions,
                    take_profit=dynamic_tp,
                    stop_loss=dynamic_sl
                )
                
                if not filter_result.passed:
                    logger.warning("⛔ ADVANCED FILTER V2.5.0 BLOCKIERT Trade:")
                    for warning in filter_result.warnings:
                        logger.warning(f"   {warning}")
                    return False
                
                logger.info(f"✅ ADVANCED FILTER V2.5.0 OK: Score {filter_result.score:.0%}")
                
                # V2.5.0: Equity Curve Protection
                from advanced_filters import EquityCurveProtection
                loss_streak = EquityCurveProtection.get_loss_streak()
                if loss_streak >= 3:
                    logger.warning(f"⚠️ EQUITY PROTECTION AKTIV: {loss_streak} Verluste in Folge")
                
            except Exception as e:
                logger.warning(f"⚠️ Advanced Filter Error (Trade wird fortgesetzt): {e}")
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.5.0: SELF-LEARNING CHECK - Erweiterte Blockierte Muster prüfen
        # ═══════════════════════════════════════════════════════════════════
        if ADVANCED_FILTERS_AVAILABLE and enhanced_learning:
            try:
                current_hour = datetime.now(timezone.utc).hour
                current_day = datetime.now(timezone.utc).weekday()
                
                # V2.5.0: Erweiterte Block-Prüfung mit Commodity
                # V2.6.0 FIX: market_analysis könnte noch nicht existieren
                market_state_value = ""
                # market_analysis wird später im AUTONOMOUS Block definiert
                # Hier einfach leer lassen
                    
                is_blocked, block_reason = enhanced_learning.is_pattern_blocked(
                    strategy=strategy,
                    commodity=commodity,
                    market_state=market_state_value,
                    hour=current_hour,
                    day=current_day
                )
                
                if is_blocked:
                    logger.warning(f"🚫 SELF-LEARNING BLOCKIERT Trade: {block_reason}")
                    return False
                    
            except Exception as e:
                logger.debug(f"Self-Learning Check Error: {e}")
                # Fehler im Self-Learning sollte Trade nicht blockieren
        
        # V2.3.31: Verwende Risk Manager für Risiko-Bewertung
        active_platforms = settings.get('active_platforms', [])
        
        # ═══════════════════════════════════════════════════════════════════
        # 🆕 V3.0.0: 4-PILLAR VERIFIED SIGNALS - VEREINFACHTE TRADE-AUSFÜHRUNG
        # ═══════════════════════════════════════════════════════════════════
        if signal.get('4pillar_verified') and signal.get('skip_autonomous_check'):
            pillar_score = signal.get('4pillar_score', 0)
            logger.info(f"✅ 4-PILLAR VERIFIED: {commodity} - Score {pillar_score}% - Direkte Trade-Ausführung")
            
            # V3.0.0 FIX: Bestimme Plattform und Lot-Size
            active_platforms = settings.get('active_platforms', ['MT5_LIBERTEX_DEMO'])
            platform = active_platforms[0] if active_platforms else 'MT5_LIBERTEX_DEMO'
            
            # Lot-Size aus Settings oder Default
            lot_size = settings.get('lot_size', 0.01)
            
            # Vereinfachte SL/TP-Berechnung für 4-Pillar Signale
            # Verwende feste Prozent-Werte basierend auf Trading-Modus
            trading_mode = settings.get('trading_mode', 'conservative')
            if trading_mode == 'aggressive':
                sl_percent = 1.5  # Engerer SL
                tp_percent = 3.0  # 2:1 R/R
            elif trading_mode == 'conservative':
                sl_percent = 3.0  # Weiterer SL
                tp_percent = 4.5  # 1.5:1 R/R
            else:  # standard
                sl_percent = 2.0
                tp_percent = 4.0
            
            if action == 'BUY':
                stop_loss = price * (1 - sl_percent / 100)
                take_profit = price * (1 + tp_percent / 100)
            else:  # SELL
                stop_loss = price * (1 + sl_percent / 100)
                take_profit = price * (1 - tp_percent / 100)
            
            logger.info(f"📊 4-Pillar SL/TP: action={action}, price={price:.2f}, SL={stop_loss:.2f} ({sl_percent}%), TP={take_profit:.2f} ({tp_percent}%)")
            logger.info(f"📊 Platform={platform}, LotSize={lot_size}")
            
            # Trade ausführen
            mt5_symbol = self._get_mt5_symbol(commodity, platform)
            logger.info(f"📋 Using symbol {mt5_symbol} for {commodity} on {platform}")
            
            trade_result = await multi_platform.execute_trade(
                platform_name=platform,
                symbol=mt5_symbol,
                action=action,
                volume=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if trade_result and trade_result.get('success'):
                mt5_ticket = trade_result.get('ticket')
                if mt5_ticket:
                    self.ticket_strategy_map[str(mt5_ticket)] = '4pillar_autonomous'
                    self.entry_prices[str(mt5_ticket)] = price
                    self.trade_count += 1
                    logger.info(f"✅ 4-PILLAR TRADE ERÖFFNET: #{mt5_ticket} {action} {commodity} @ {price:.2f}")
                    logger.info(f"   SL={stop_loss:.2f}, TP={take_profit:.2f}, Confidence={pillar_score}%")
                    return True
            
            logger.error(f"❌ 4-Pillar Trade fehlgeschlagen: {trade_result}")
            return False
        
        # ═══════════════════════════════════════════════════════════════════
        # 🆕 V2.5.0: AUTONOMOUS TRADING INTELLIGENCE (für nicht-4pillar Signale)
        # Prüft ob Trade wirklich ausgeführt werden soll (80% Threshold!)
        # ═══════════════════════════════════════════════════════════════════
        elif AUTONOMOUS_TRADING_AVAILABLE and autonomous_trading:
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
                    logger.info("   → Trade wird mit Penalty im Confidence Score fortgesetzt")
                
                # 3. HOLE NEWS-SENTIMENT
                news_sentiment = "neutral"
                high_impact_pending = False
                try:
                    from news_analyzer import news_analyzer
                    news_status = await news_analyzer.get_commodity_news_status(commodity)
                    news_sentiment = news_status.get('sentiment', 'neutral')
                    high_impact_pending = news_status.get('high_impact_pending', False)
                except Exception:
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
                # free_margin wird für zukünftige Erweiterungen gespeichert
                _ = account_info.get('freeMargin', account_info.get('free_margin', 0))
                
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
                
                # V2.6.0: Trading-Modus aus Settings holen!
                trading_mode = settings.get('trading_mode', 'neutral')
                lot_size = self._calculate_lot_size(balance, adjusted_risk_percent, price, trading_mode)
                
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
                            logger.warning("🛑 TRADE BLOCKIERT - Kein Margin-Budget mehr verfügbar!")
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
                
                # ═══════════════════════════════════════════════════════════════════
                # V2.3.39: INTELLIGENTE DYNAMISCHE SETTINGS
                # Die KI passt SL/TP basierend auf Signal-Stärke und Markt-Zustand an
                # ═══════════════════════════════════════════════════════════════════
                
                # Hole Signal-Stärke aus dem Universal Score
                signal_strength = 0.65  # Default
                if AUTONOMOUS_TRADING_AVAILABLE and autonomous_trading and 'universal_score' in dir():
                    try:
                        signal_strength = universal_score.total_score / 100.0
                    except Exception:
                        pass
                
                # Hole dynamische Settings von der KI
                dynamic_settings = None
                if AUTONOMOUS_TRADING_AVAILABLE and autonomous_trading:
                    try:
                        dynamic_settings = autonomous_trading.get_dynamic_settings_for_signal(
                            signal_strength=signal_strength,
                            market_analysis=market_analysis,
                            strategy=strategy.replace('_trading', ''),
                            base_settings=settings
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Dynamische Settings nicht verfügbar: {e}")
                
                # Verwende dynamische Settings wenn verfügbar, sonst Basis-Settings
                if dynamic_settings:
                    sl_percent = dynamic_settings['stop_loss_percent']
                    tp_percent = dynamic_settings['take_profit_percent']
                    
                    # Passe Lot-Size mit dem Multiplier an
                    pos_multiplier = dynamic_settings.get('position_size_multiplier', 1.0)
                    lot_size = round(lot_size * pos_multiplier, 2)
                    lot_size = max(0.01, min(1.0, lot_size))  # Sicherheitsgrenzen
                    
                    logger.info("🎯 DYNAMISCHE SETTINGS AKTIV:")
                    logger.info(f"   Signal-Stärke: {signal_strength:.0%}")
                    logger.info(f"   SL: {sl_percent}%, TP: {tp_percent}%")
                    logger.info(f"   Lot-Size: {lot_size} (Multiplier: {pos_multiplier}x)")
                else:
                    # Fallback: Basis-Settings
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
                logger.info(f"📊 SL/TP: action={action}, price={price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}")
                    
                # V3.0.0 FIX: SL und TP werden jetzt korrekt übergeben
                trade_result = await multi_platform.execute_trade(
                    platform_name=platform,
                    symbol=mt5_symbol,
                    action=action,
                    volume=lot_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit
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
                    await self.db.trades_db.insert_trade({
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
                    
                    # Hole Trade Settings aus DB (Format: mt5_{ticket})
                    trade_settings_id = f"mt5_{ticket}"
                    trade_settings = await self.db.trades_db.get_trade_settings(trade_settings_id)
                    
                    if not trade_settings:
                        # V2.3.38: Kein Settings gefunden = neuer Trade, nicht schließen!
                        logger.debug(f"⏭️ Position {ticket}: Keine Settings gefunden für {trade_settings_id} - übersprungen")
                        continue
                    
                    stop_loss = trade_settings.get('stop_loss')
                    take_profit = trade_settings.get('take_profit')
                    trade_type = pos.get('type', trade_settings.get('type', 'BUY'))
                    
                    if not current_price or not stop_loss or not take_profit:
                        logger.debug(f"⏭️ Position {ticket}: Unvollständige Daten (Price:{current_price}, SL:{stop_loss}, TP:{take_profit})")
                        continue
                    
                    # V2.5.1: Sicherheitscheck - Trade muss mindestens 2 MINUTEN offen sein
                    # (erhöht von 30 Sekunden um sofortiges Schließen zu verhindern)
                    trade_time = pos.get('time')
                    if trade_time:
                        try:
                            from dateutil.parser import parse as parse_date
                            opened_at = parse_date(trade_time) if isinstance(trade_time, str) else trade_time
                            age_seconds = (datetime.now(timezone.utc) - opened_at.replace(tzinfo=timezone.utc)).total_seconds()
                            if age_seconds < 120:  # 2 Minuten statt 30 Sekunden
                                logger.debug(f"⏭️ Position {ticket}: Zu jung ({age_seconds:.0f}s < 120s) - übersprungen")
                                continue
                        except Exception:
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V2.6.0: INTELLIGENTE LOT-BERECHNUNG
    # Basierend auf Signal-Stärke (Confidence), Trading-Modus und Risiko-Management
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Risiko-Stufen für jeden Trading-Modus
    # Angepasst an die jeweiligen Confidence-Thresholds
    RISK_LEVELS = {
        # KONSERVATIV: Thresholds 70-88%, Minimum 75%
        # Weniger Risiko, höhere Signal-Anforderungen
        'conservative': {
            'min_confidence': 75,      # Unter 75% = kein Trade
            'low_risk_max': 80,        # 75-80% = niedriges Risiko
            'medium_risk_max': 88,     # 80-88% = mittleres Risiko
            'low_risk': 0.005,         # 0.5%
            'medium_risk': 0.0075,     # 0.75%
            'high_risk': 0.01,         # 1.0% (max für konservativ!)
            'max_lot': 1.5             # Niedrigeres Max-Lot
        },
        # NEUTRAL: Thresholds 62-80%, Minimum 68%
        # Ausgewogenes Risiko
        'neutral': {
            'min_confidence': 68,      # Unter 68% = kein Trade
            'low_risk_max': 75,        # 68-75% = niedriges Risiko
            'medium_risk_max': 85,     # 75-85% = mittleres Risiko
            'low_risk': 0.005,         # 0.5%
            'medium_risk': 0.01,       # 1.0%
            'high_risk': 0.015,        # 1.5%
            'max_lot': 2.0             # Standard Max-Lot
        },
        # AGGRESSIV: Thresholds 55-72%, Minimum 60%
        # Höheres Risiko, mehr Trades
        'aggressive': {
            'min_confidence': 60,      # Unter 60% = kein Trade
            'low_risk_max': 68,        # 60-68% = niedriges Risiko
            'medium_risk_max': 78,     # 68-78% = mittleres Risiko
            'low_risk': 0.01,          # 1.0% (aggressiver Start!)
            'medium_risk': 0.015,      # 1.5%
            'high_risk': 0.02,         # 2.0%
            'max_lot': 2.5             # Höheres Max-Lot erlaubt
        }
    }
    
    def _calculate_lot_size_v2(
        self,
        balance: float,
        confidence_score: float,  # 0.0 - 1.0 (oder 0-100%)
        stop_loss_pips: float,
        tick_value: float = 10.0,
        symbol: str = "XAUUSD",
        trading_mode: str = "neutral"  # V2.6.0: Trading-Modus!
    ) -> float:
        """
        V2.6.0: Berechnet Lot Size basierend auf Signal-Stärke UND Trading-Modus
        
        Die Risiko-Stufen sind an den jeweiligen Trading-Modus angepasst:
        
        KONSERVATIV (Thresholds 75%+):
        - < 75%:  Kein Trade
        - 75-80%: 0.5% Risiko
        - 80-88%: 0.75% Risiko
        - > 88%:  1.0% Risiko (Max!)
        - Max Lot: 1.5
        
        NEUTRAL (Thresholds 68%+):
        - < 68%:  Kein Trade
        - 68-75%: 0.5% Risiko
        - 75-85%: 1.0% Risiko
        - > 85%:  1.5% Risiko
        - Max Lot: 2.0
        
        AGGRESSIV (Thresholds 60%+):
        - < 60%:  Kein Trade
        - 60-68%: 1.0% Risiko
        - 68-78%: 1.5% Risiko
        - > 78%:  2.0% Risiko
        - Max Lot: 2.5
        
        Formel: Lots = (Balance * Risiko%) / (Stop_Loss_Pips * Tick_Value)
        """
        # Normalisiere Confidence auf 0-100 falls nötig
        if confidence_score <= 1.0:
            confidence_percent = confidence_score * 100
        else:
            confidence_percent = confidence_score
        
        # Trading-Modus Risiko-Konfiguration holen
        mode_config = self.RISK_LEVELS.get(trading_mode.lower(), self.RISK_LEVELS['neutral'])
        
        # ─────────────────────────────────────────────────────────────────
        # RISIKO-STUFEN BASIEREND AUF TRADING-MODUS UND SIGNAL-STÄRKE
        # ─────────────────────────────────────────────────────────────────
        min_conf = mode_config['min_confidence']
        low_max = mode_config['low_risk_max']
        med_max = mode_config['medium_risk_max']
        
        if confidence_percent < min_conf:
            logger.info(f"⛔ Lot-Berechnung [{trading_mode.upper()}]: Signal {confidence_percent:.1f}% < {min_conf}% Minimum - Kein Trade")
            return 0.0
        elif confidence_percent < low_max:
            risk_percent = mode_config['low_risk']
            risk_level = "NIEDRIG"
        elif confidence_percent <= med_max:
            risk_percent = mode_config['medium_risk']
            risk_level = "MITTEL"
        else:
            risk_percent = mode_config['high_risk']
            risk_level = "HOCH"
        
        # ─────────────────────────────────────────────────────────────────
        # LOT-BERECHNUNG
        # Formel: Lots = (Balance * Risiko%) / (Stop_Loss_Pips * Tick_Value)
        # ─────────────────────────────────────────────────────────────────
        
        # Sicherheits-Checks
        if balance <= 0:
            logger.warning("⚠️ Balance ist 0 oder negativ!")
            return 0.01
        
        if stop_loss_pips <= 0:
            logger.warning("⚠️ Stop Loss Pips ungültig, verwende 20 als Default")
            stop_loss_pips = 20.0
        
        if tick_value <= 0:
            logger.warning("⚠️ Tick Value ungültig, verwende 10 als Default")
            tick_value = 10.0
        
        # Verschuldetes Kapital berechnen
        risk_amount = balance * risk_percent
        
        # Lot-Größe berechnen
        lot_size = risk_amount / (stop_loss_pips * tick_value)
        
        # ─────────────────────────────────────────────────────────────────
        # SICHERHEITS-LIMITS (Trading-Modus abhängig!)
        # ─────────────────────────────────────────────────────────────────
        MIN_LOT = 0.01
        MAX_LOT = mode_config['max_lot']  # Abhängig vom Modus!
        
        # Auf 2 Dezimalstellen runden
        lot_size = round(lot_size, 2)
        
        # Limits anwenden
        if lot_size < MIN_LOT:
            lot_size = MIN_LOT
        elif lot_size > MAX_LOT:
            logger.warning(f"⚠️ Lot {lot_size} überschreitet Maximum für {trading_mode}! Limitiert auf {MAX_LOT}")
            lot_size = MAX_LOT
        
        logger.info(f"📊 Lot-Berechnung [{symbol}] - Modus: {trading_mode.upper()}")
        logger.info(f"   ├─ Signal: {confidence_percent:.1f}% ({risk_level})")
        logger.info(f"   ├─ Balance: {balance:.2f}")
        logger.info(f"   ├─ Risiko: {risk_percent*100:.2f}% = {risk_amount:.2f}")
        logger.info(f"   ├─ SL: {stop_loss_pips:.1f} Pips, Tick: {tick_value}")
        logger.info(f"   ├─ Max Lot ({trading_mode}): {MAX_LOT}")
        logger.info(f"   └─ LOT: {lot_size}")
        
        return lot_size
    
    def _calculate_lot_size(self, balance: float, risk_percent: float, price: float, trading_mode: str = "neutral") -> float:
        """
        Legacy Lot-Berechnung (für Abwärtskompatibilität)
        Verwendet V2.6.0 Logik mit Default-Werten
        
        V2.6.0: Trading-Modus wird jetzt berücksichtigt!
        """
        # Konvertiere risk_percent zu confidence
        # Annahme: risk_percent 2% = starkes Signal (85%+ confidence)
        if risk_percent >= 2.0:
            confidence = 0.90
        elif risk_percent >= 1.0:
            confidence = 0.75
        else:
            confidence = 0.60
        
        # Verwende neue Methode MIT Trading-Modus
        return self._calculate_lot_size_v2(
            balance=balance,
            confidence_score=confidence,
            stop_loss_pips=20,  # Default
            tick_value=10.0,  # Default für Forex
            trading_mode=trading_mode  # V2.6.0: Trading-Modus übergeben!
        )
    
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
            # V3.0.0: Neue Assets
            'ZINC': 'ZINC',  # LME-Symbol
            'NASDAQ100': 'USTEC',  # US Tech 100
        }
        return symbol_map.get(commodity, commodity)
    
    async def _get_symbol_info(self, symbol: str, platform: str = None) -> dict:
        """
        V2.6.0: Holt Symbol-Informationen vom Broker (Tick Value, Contract Size, etc.)
        
        Args:
            symbol: MT5 Symbol (z.B. 'XAUUSD', 'EURUSD')
            platform: Plattform-ID
        
        Returns:
            Dict mit tick_value, contract_size, min_lot, max_lot, pip_size
        """
        # Standard-Werte für verschiedene Asset-Klassen
        DEFAULT_VALUES = {
            # Forex Major (Standard Lot = 100,000 Einheiten)
            'EURUSD': {'tick_value': 10.0, 'contract_size': 100000, 'pip_size': 0.0001, 'min_lot': 0.01, 'max_lot': 100},
            'GBPUSD': {'tick_value': 10.0, 'contract_size': 100000, 'pip_size': 0.0001, 'min_lot': 0.01, 'max_lot': 100},
            'USDJPY': {'tick_value': 9.0, 'contract_size': 100000, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 100},
            'USDCHF': {'tick_value': 11.0, 'contract_size': 100000, 'pip_size': 0.0001, 'min_lot': 0.01, 'max_lot': 100},
            'AUDUSD': {'tick_value': 10.0, 'contract_size': 100000, 'pip_size': 0.0001, 'min_lot': 0.01, 'max_lot': 100},
            
            # Gold (1 Lot = 100 oz)
            'XAUUSD': {'tick_value': 1.0, 'contract_size': 100, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 50},
            'GOLD': {'tick_value': 1.0, 'contract_size': 100, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 50},
            
            # Silber (1 Lot = 5000 oz)
            'XAGUSD': {'tick_value': 5.0, 'contract_size': 5000, 'pip_size': 0.001, 'min_lot': 0.01, 'max_lot': 50},
            'SILVER': {'tick_value': 5.0, 'contract_size': 5000, 'pip_size': 0.001, 'min_lot': 0.01, 'max_lot': 50},
            
            # Platin & Palladium
            'XPTUSD': {'tick_value': 1.0, 'contract_size': 100, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 20},
            'XPDUSD': {'tick_value': 1.0, 'contract_size': 100, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 20},
            
            # Öl (1 Lot = 1000 Barrel)
            'XTIUSD': {'tick_value': 10.0, 'contract_size': 1000, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 100},
            'XBRUSD': {'tick_value': 10.0, 'contract_size': 1000, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 100},
            'WTI': {'tick_value': 10.0, 'contract_size': 1000, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 100},
            'BRENT': {'tick_value': 10.0, 'contract_size': 1000, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 100},
            
            # Natural Gas
            'XNGUSD': {'tick_value': 10.0, 'contract_size': 10000, 'pip_size': 0.001, 'min_lot': 0.01, 'max_lot': 50},
            
            # Crypto
            'BTCUSD': {'tick_value': 1.0, 'contract_size': 1, 'pip_size': 1.0, 'min_lot': 0.01, 'max_lot': 10},
            'ETHUSD': {'tick_value': 1.0, 'contract_size': 1, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 50},
            
            # Agrar (variiert stark)
            'WHEAT': {'tick_value': 5.0, 'contract_size': 5000, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},
            'CORN': {'tick_value': 5.0, 'contract_size': 5000, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},
            'SOYBEAN': {'tick_value': 5.0, 'contract_size': 5000, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},
            'COFFEE': {'tick_value': 3.75, 'contract_size': 37500, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},
            'SUGAR': {'tick_value': 11.2, 'contract_size': 112000, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},
            'COCOA': {'tick_value': 10.0, 'contract_size': 10, 'pip_size': 1.0, 'min_lot': 0.1, 'max_lot': 20},
            
            # V3.0.0: Neue Assets
            'ZINC': {'tick_value': 5.0, 'contract_size': 25000, 'pip_size': 0.01, 'min_lot': 0.1, 'max_lot': 20},  # LME Zink
            'USTEC': {'tick_value': 1.0, 'contract_size': 1, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 50},    # Nasdaq 100
            'NASDAQ100': {'tick_value': 1.0, 'contract_size': 1, 'pip_size': 0.01, 'min_lot': 0.01, 'max_lot': 50},
        }
        
        # Suche nach Symbol
        symbol_upper = symbol.upper()
        
        # Direkte Übereinstimmung
        if symbol_upper in DEFAULT_VALUES:
            return DEFAULT_VALUES[symbol_upper]
        
        # Partial Match
        for key, values in DEFAULT_VALUES.items():
            if key in symbol_upper or symbol_upper in key:
                return values
        
        # Default für unbekannte Symbole (konservativ)
        logger.warning(f"⚠️ Unbekanntes Symbol {symbol} - verwende konservative Defaults")
        return {
            'tick_value': 10.0,
            'contract_size': 100,
            'pip_size': 0.01,
            'min_lot': 0.01,
            'max_lot': 2.0  # Konservatives Maximum
        }
    
    async def calculate_trade_lot(
        self,
        commodity: str,
        confidence_score: float,
        stop_loss_percent: float,
        platform: str = None
    ) -> float:
        """
        V2.6.0: Hauptmethode für Lot-Berechnung bei neuen Trades
        
        Ruft Account-Balance ab und berechnet optimale Lot-Größe.
        Berücksichtigt den Trading-Modus (konservativ/neutral/aggressiv)!
        
        Args:
            commodity: Asset-Name (z.B. 'GOLD', 'EURUSD')
            confidence_score: Signal-Stärke 0-100 oder 0.0-1.0
            stop_loss_percent: Stop-Loss in Prozent
            platform: Trading-Plattform
        
        Returns:
            Berechnete Lot-Größe
        """
        try:
            # Import multi_platform für Account-Zugriff
            from multi_platform_connector import multi_platform
            import database as db_module
            
            # 1. Settings holen (für Trading-Modus und Plattformen)
            settings = await self.get_settings()
            
            # V2.6.0: Trading-Modus aus Settings holen!
            trading_mode = settings.get('trading_mode', 'neutral')
            logger.info(f"📊 Trading-Modus für Lot-Berechnung: {trading_mode.upper()}")
            
            # 2. Account Balance abrufen
            if platform:
                account_info = await multi_platform.get_account_info(platform)
            else:
                # Default: Erste aktive Plattform
                platforms = settings.get('active_platforms', ['MT5_LIBERTEX_DEMO'])
                account_info = await multi_platform.get_account_info(platforms[0])
            
            balance = account_info.get('balance', 10000) if account_info else 10000
            
            # 3. Symbol-Info holen
            symbol = self._get_mt5_symbol(commodity, platform)
            symbol_info = await self._get_symbol_info(symbol, platform)
            
            # 4. Stop Loss in Pips umrechnen
            # stop_loss_percent (z.B. 2%) → Pips basierend auf aktuellem Preis
            market_data = await db_module.market_data.find_one({"commodity": commodity})
            current_price = market_data.get('price', 1000) if market_data else 1000
            
            pip_size = symbol_info.get('pip_size', 0.01)
            stop_loss_pips = (current_price * stop_loss_percent / 100) / pip_size
            
            # Minimum 10 Pips für Sicherheit
            stop_loss_pips = max(10, stop_loss_pips)
            
            # 5. Tick Value
            tick_value = symbol_info.get('tick_value', 10.0)
            
            # 6. Lot berechnen MIT TRADING-MODUS!
            lot_size = self._calculate_lot_size_v2(
                balance=balance,
                confidence_score=confidence_score,
                stop_loss_pips=stop_loss_pips,
                tick_value=tick_value,
                symbol=symbol,
                trading_mode=trading_mode  # V2.6.0: Trading-Modus übergeben!
            )
            
            # 6. Symbol-spezifische Limits anwenden
            min_lot = symbol_info.get('min_lot', 0.01)
            max_lot = symbol_info.get('max_lot', 2.0)
            
            if lot_size < min_lot:
                lot_size = min_lot
            elif lot_size > max_lot:
                lot_size = max_lot
            
            return lot_size
            
        except Exception as e:
            logger.error(f"Fehler bei Lot-Berechnung: {e}")
            return 0.01  # Minimaler Default
    
    async def _get_all_mt5_positions(self) -> list:
        """
        V2.3.39: Holt ALLE offenen Positionen von allen MT5 Plattformen
        Verwendet multi_platform als zentrale Quelle
        """
        from multi_platform_connector import multi_platform
        
        all_positions = []
        
        try:
            settings = await self.get_settings()
            active_platforms = settings.get('active_platforms', ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO'])
            
            for platform in active_platforms:
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    if positions:
                        all_positions.extend(positions)
                except Exception as e:
                    logger.debug(f"Fehler beim Holen von Positionen für {platform}: {e}")
            
            return all_positions
            
        except Exception as e:
            logger.error(f"Fehler beim Holen aller MT5 Positionen: {e}")
            return []


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
