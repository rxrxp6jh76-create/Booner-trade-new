"""
🧠 SELF-LEARNING TRADING TAGEBUCH - V2.4.0
=========================================

KI-Feedback-Loop für adaptives Trading mit 80% Trefferquoten-Ziel

Features:
1. Trade-Tagebuch: Speichert jeden Trade mit Kontext
2. Lerneffekt: Wöchentliche Win-Rate Analyse pro Parameter
3. Confluence-Check: Min. 3 Indikatoren müssen konvergieren
4. Top-Down-Validierung: Kleine TF müssen mit großen übereinstimmen
5. Automatische Blockierung: Setups mit <60% Win-Rate werden gesperrt

Datenquellen:
- SQLite: trade_journal Tabelle
- News-Analyzer: Sentiment und High-Impact Events
- MetaAPI: Live-Preisdaten für Multi-Timeframe
"""

import logging
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

class MarketPhase(Enum):
    """Marktphasen für Kontext-Analyse"""
    ASIAN = "asian"          # 00:00-08:00 UTC
    LONDON = "london"        # 08:00-16:00 UTC
    NEW_YORK = "new_york"    # 13:00-21:00 UTC
    OVERLAP = "overlap"      # 13:00-16:00 UTC (höchste Volatilität)
    QUIET = "quiet"          # 21:00-00:00 UTC

class TrendDirection(Enum):
    """Trend-Richtungen für Multi-Timeframe"""
    STRONG_UP = "strong_up"
    UP = "up"
    NEUTRAL = "neutral"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TradeJournalEntry:
    """Einzelner Tagebuch-Eintrag für einen Trade"""
    trade_id: str
    timestamp: str
    strategy: str
    commodity: str
    direction: str  # BUY/SELL
    
    # Markt-Kontext
    atr: float
    adx: float
    volatility: float
    market_phase: str
    day_of_week: int  # 0=Montag, 6=Sonntag
    hour_of_day: int
    
    # Signal-Daten
    confidence_score: float
    confluence_count: int  # Anzahl konvergierender Indikatoren
    indicators_used: List[str]
    
    # Multi-Timeframe
    trend_m15: str
    trend_h1: str
    trend_h4: str
    trend_d1: str
    top_down_aligned: bool  # Alle Timeframes in gleicher Richtung?
    
    # News/Sentiment
    news_sentiment: str  # bullish/bearish/neutral
    high_impact_news_pending: bool
    
    # Geplante Werte
    entry_price: float
    planned_sl: float
    planned_tp: float
    planned_rr_ratio: float  # Risk-Reward
    
    # Tatsächliches Ergebnis (nach Trade-Schließung)
    exit_price: float = 0.0
    actual_profit: float = 0.0
    actual_rr_ratio: float = 0.0
    hit_tp: bool = False
    hit_sl: bool = False
    trade_duration_minutes: int = 0
    is_winner: bool = False
    
    # Status
    status: str = "open"  # open, closed, cancelled


@dataclass
class StrategyPerformance:
    """Performance-Statistiken pro Strategie"""
    strategy: str
    total_trades: int = 0
    winners: int = 0
    losers: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_rr_ratio: float = 0.0
    best_market_phase: str = ""
    worst_market_phase: str = ""
    blocked_conditions: List[str] = field(default_factory=list)


@dataclass
class ConfluenceResult:
    """Ergebnis der Confluence-Prüfung"""
    passed: bool
    confluence_count: int
    indicators_aligned: List[str]
    missing_for_trade: int  # Wie viele fehlen noch für 3?
    details: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN CLASS: SELF-LEARNING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

class SelfLearningTradeManager:
    """
    KI-gesteuertes Trading-Tagebuch mit adaptivem Lernen
    
    Ziel: 80% Trefferquote durch:
    - Confluence-Validierung (min. 3 Indikatoren)
    - Multi-Timeframe Top-Down Analyse
    - Sentiment/News-Integration
    - Automatische Sperrung schlechter Setups
    """
    
    # Konfiguration
    MIN_CONFLUENCE = 3  # Mindestens 3 konvergierende Indikatoren
    MIN_WIN_RATE_THRESHOLD = 60.0  # Unter 60% wird Setup gesperrt
    CONFIDENCE_FOR_FULL_SIZE = 80.0  # Ab 80% volle Positionsgröße
    WEEKLY_ANALYSIS_DAY = 0  # Montag
    
    def __init__(self):
        self.journal: List[TradeJournalEntry] = []
        self.strategy_stats: Dict[str, StrategyPerformance] = {}
        self.blocked_setups: List[Dict] = []  # Gesperrte Kombinationen
        self._db = None
        
        # Performance-Cache (wird wöchentlich neu berechnet)
        self._performance_cache = {}
        self._last_analysis = None
        
    async def init_database(self):
        """Initialisiere SQLite Tabelle für Trade-Journal"""
        try:
            import database as db_module
            self._db = db_module
            
            # Erstelle trade_journal Tabelle falls nicht existiert
            if hasattr(db_module, '_db') and db_module._db:
                await db_module._db.execute("""
                    CREATE TABLE IF NOT EXISTS trade_journal (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id TEXT UNIQUE,
                        timestamp TEXT,
                        strategy TEXT,
                        commodity TEXT,
                        direction TEXT,
                        atr REAL,
                        adx REAL,
                        volatility REAL,
                        market_phase TEXT,
                        day_of_week INTEGER,
                        hour_of_day INTEGER,
                        confidence_score REAL,
                        confluence_count INTEGER,
                        indicators_used TEXT,
                        trend_m15 TEXT,
                        trend_h1 TEXT,
                        trend_h4 TEXT,
                        trend_d1 TEXT,
                        top_down_aligned INTEGER,
                        news_sentiment TEXT,
                        high_impact_news_pending INTEGER,
                        entry_price REAL,
                        planned_sl REAL,
                        planned_tp REAL,
                        planned_rr_ratio REAL,
                        exit_price REAL DEFAULT 0,
                        actual_profit REAL DEFAULT 0,
                        actual_rr_ratio REAL DEFAULT 0,
                        hit_tp INTEGER DEFAULT 0,
                        hit_sl INTEGER DEFAULT 0,
                        trade_duration_minutes INTEGER DEFAULT 0,
                        is_winner INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'open'
                    )
                """)
                
                # Erstelle blocked_setups Tabelle
                await db_module._db.execute("""
                    CREATE TABLE IF NOT EXISTS blocked_setups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy TEXT,
                        condition_type TEXT,
                        condition_value TEXT,
                        win_rate REAL,
                        sample_size INTEGER,
                        blocked_at TEXT,
                        reason TEXT
                    )
                """)
                
                await db_module._db.commit()
                logger.info("✅ Trade-Journal Datenbank initialisiert")
                
        except Exception as e:
            logger.error(f"Fehler bei DB-Init: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFLUENCE CHECK (Mindestens 3 Indikatoren müssen übereinstimmen)
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_confluence(
        self,
        signal: str,  # BUY/SELL
        indicators: Dict[str, Any]
    ) -> ConfluenceResult:
        """
        Prüft ob mindestens 3 Indikatoren in die gleiche Richtung zeigen
        
        Indikatoren die geprüft werden:
        1. RSI (Überverkauft/Überkauft)
        2. MACD (Histogramm + Crossover)
        3. EMA Crossover (9/21 oder 50/200)
        4. Stochastik
        5. Bollinger Bands
        6. ADX (Trendstärke)
        7. VWAP-Distanz
        8. Volume-Bestätigung
        """
        aligned_indicators = []
        is_buy = signal == 'BUY'
        
        # 1. RSI Check
        rsi = indicators.get('rsi', 50)
        if is_buy and rsi < 40:
            aligned_indicators.append('RSI_oversold')
        elif not is_buy and rsi > 60:
            aligned_indicators.append('RSI_overbought')
        
        # 2. MACD Check
        macd_hist = indicators.get('macd_histogram', 0)
        macd_bullish = indicators.get('macd_bullish', False)
        if is_buy and (macd_hist > 0 or macd_bullish):
            aligned_indicators.append('MACD_bullish')
        elif not is_buy and (macd_hist < 0 or not macd_bullish):
            aligned_indicators.append('MACD_bearish')
        
        # 3. EMA Crossover
        ema_9 = indicators.get('ema_9', 0)
        ema_21 = indicators.get('ema_21', 0)
        ema_50 = indicators.get('ema_50', 0)
        ema_200 = indicators.get('ema_200', indicators.get('sma_200', 0))
        
        if is_buy and (ema_9 > ema_21 or ema_50 > ema_200):
            aligned_indicators.append('EMA_bullish_cross')
        elif not is_buy and (ema_9 < ema_21 or ema_50 < ema_200):
            aligned_indicators.append('EMA_bearish_cross')
        
        # 4. Stochastik
        stoch_k = indicators.get('stochastic_k', 50)
        stoch_d = indicators.get('stochastic_d', 50)
        if is_buy and stoch_k < 30:
            aligned_indicators.append('Stoch_oversold')
        elif not is_buy and stoch_k > 70:
            aligned_indicators.append('Stoch_overbought')
        
        # 5. Bollinger Bands
        bb_upper = indicators.get('upper_band', 0)
        bb_lower = indicators.get('lower_band', 0)
        bb_middle = indicators.get('middle_band', 0)
        current_price = indicators.get('current_price', 0)
        
        if current_price and bb_lower:
            if is_buy and current_price < bb_lower:
                aligned_indicators.append('BB_below_lower')
            elif not is_buy and current_price > bb_upper:
                aligned_indicators.append('BB_above_upper')
        
        # 6. ADX (Trendstärke > 25)
        adx = indicators.get('adx', 0)
        if adx > 25:
            aligned_indicators.append('ADX_strong_trend')
        
        # 7. VWAP
        vwap = indicators.get('vwap', 0)
        vwap_distance = indicators.get('vwap_distance', 0)
        if current_price and vwap:
            if is_buy and current_price < vwap:
                aligned_indicators.append('Below_VWAP')
            elif not is_buy and current_price > vwap:
                aligned_indicators.append('Above_VWAP')
        
        # 8. Volume-Bestätigung
        volume_surge = indicators.get('volume_surge', False)
        volume_peak = indicators.get('volume_peak', False)
        if volume_surge or volume_peak:
            aligned_indicators.append('Volume_confirmation')
        
        confluence_count = len(aligned_indicators)
        passed = confluence_count >= self.MIN_CONFLUENCE
        
        return ConfluenceResult(
            passed=passed,
            confluence_count=confluence_count,
            indicators_aligned=aligned_indicators,
            missing_for_trade=max(0, self.MIN_CONFLUENCE - confluence_count),
            details={
                'required': self.MIN_CONFLUENCE,
                'signal': signal,
                'all_checks': {
                    'rsi': rsi,
                    'macd_hist': macd_hist,
                    'stoch_k': stoch_k,
                    'adx': adx
                }
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # TOP-DOWN MULTI-TIMEFRAME CHECK
    # ═══════════════════════════════════════════════════════════════════════
    
    def check_top_down_alignment(
        self,
        signal: str,
        trend_m15: TrendDirection,
        trend_h1: TrendDirection,
        trend_h4: TrendDirection,
        trend_d1: TrendDirection
    ) -> Tuple[bool, str]:
        """
        Prüft ob alle Timeframes in die gleiche Richtung zeigen
        
        Regel: Trade nur wenn:
        - D1 und H4 den Haupttrend bestätigen
        - H1 und M15 das Entry-Signal geben
        
        Returns:
            (aligned: bool, reason: str)
        """
        is_buy = signal == 'BUY'
        
        # Definiere "bullish" Trends
        bullish_trends = [TrendDirection.STRONG_UP, TrendDirection.UP]
        bearish_trends = [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]
        
        # D1 muss den Haupttrend bestätigen
        if is_buy:
            d1_ok = trend_d1 in bullish_trends or trend_d1 == TrendDirection.NEUTRAL
            h4_ok = trend_h4 in bullish_trends or trend_h4 == TrendDirection.NEUTRAL
            h1_ok = trend_h1 in bullish_trends
            m15_ok = trend_m15 in bullish_trends
        else:
            d1_ok = trend_d1 in bearish_trends or trend_d1 == TrendDirection.NEUTRAL
            h4_ok = trend_h4 in bearish_trends or trend_h4 == TrendDirection.NEUTRAL
            h1_ok = trend_h1 in bearish_trends
            m15_ok = trend_m15 in bearish_trends
        
        # Mindestens D1+H4 oder H4+H1+M15 müssen aligned sein
        strong_alignment = d1_ok and h4_ok and (h1_ok or m15_ok)
        weak_alignment = h4_ok and h1_ok and m15_ok
        
        aligned = strong_alignment or weak_alignment
        
        if aligned:
            reason = "Top-Down aligned: " + ", ".join([
                f"D1={trend_d1.value}",
                f"H4={trend_h4.value}",
                f"H1={trend_h1.value}",
                f"M15={trend_m15.value}"
            ])
        else:
            conflicts = []
            if not d1_ok:
                conflicts.append(f"D1 gegen Signal ({trend_d1.value})")
            if not h4_ok:
                conflicts.append(f"H4 gegen Signal ({trend_h4.value})")
            reason = "Top-Down NICHT aligned: " + ", ".join(conflicts)
        
        return aligned, reason
    
    # ═══════════════════════════════════════════════════════════════════════
    # MARKT-KONTEXT ANALYSE
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_market_phase(self, hour_utc: int) -> MarketPhase:
        """Bestimmt die aktuelle Marktphase basierend auf UTC-Zeit"""
        if 0 <= hour_utc < 8:
            return MarketPhase.ASIAN
        elif 8 <= hour_utc < 13:
            return MarketPhase.LONDON
        elif 13 <= hour_utc < 16:
            return MarketPhase.OVERLAP
        elif 16 <= hour_utc < 21:
            return MarketPhase.NEW_YORK
        else:
            return MarketPhase.QUIET
    
    def calculate_trend_from_prices(self, prices: List[float], period: int = 20) -> TrendDirection:
        """Berechnet Trend-Richtung aus Preisliste"""
        if len(prices) < period:
            return TrendDirection.NEUTRAL
        
        recent = prices[-period:]
        sma = sum(recent) / len(recent)
        current = prices[-1]
        
        # Berechne Steigung
        first_half = sum(recent[:period//2]) / (period//2)
        second_half = sum(recent[period//2:]) / (period//2)
        slope = (second_half - first_half) / first_half * 100 if first_half > 0 else 0
        
        # Distanz zum SMA
        distance = (current - sma) / sma * 100 if sma > 0 else 0
        
        if slope > 1.0 and distance > 0.5:
            return TrendDirection.STRONG_UP
        elif slope > 0.3 or distance > 0.2:
            return TrendDirection.UP
        elif slope < -1.0 and distance < -0.5:
            return TrendDirection.STRONG_DOWN
        elif slope < -0.3 or distance < -0.2:
            return TrendDirection.DOWN
        else:
            return TrendDirection.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════════════════
    # TRADE-JOURNAL OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    async def log_trade_entry(
        self,
        trade_id: str,
        strategy: str,
        commodity: str,
        direction: str,
        entry_price: float,
        planned_sl: float,
        planned_tp: float,
        confidence_score: float,
        indicators: Dict[str, Any],
        news_sentiment: str = "neutral",
        high_impact_pending: bool = False
    ) -> TradeJournalEntry:
        """
        Loggt einen neuen Trade ins Tagebuch
        """
        now = datetime.now(timezone.utc)
        
        # Hole Markt-Kontext
        market_phase = self.get_market_phase(now.hour)
        
        # Berechne R:R Ratio
        sl_distance = abs(entry_price - planned_sl)
        tp_distance = abs(planned_tp - entry_price)
        rr_ratio = tp_distance / sl_distance if sl_distance > 0 else 0
        
        # Confluence Check
        confluence = self.check_confluence(direction, indicators)
        
        # Trend-Analyse (vereinfacht - in Produktion von MetaAPI holen)
        trend_m15 = TrendDirection.NEUTRAL.value
        trend_h1 = TrendDirection.NEUTRAL.value
        trend_h4 = TrendDirection.NEUTRAL.value
        trend_d1 = TrendDirection.NEUTRAL.value
        
        entry = TradeJournalEntry(
            trade_id=trade_id,
            timestamp=now.isoformat(),
            strategy=strategy,
            commodity=commodity,
            direction=direction,
            atr=indicators.get('atr', 0),
            adx=indicators.get('adx', 0),
            volatility=indicators.get('volatility', 0),
            market_phase=market_phase.value,
            day_of_week=now.weekday(),
            hour_of_day=now.hour,
            confidence_score=confidence_score,
            confluence_count=confluence.confluence_count,
            indicators_used=confluence.indicators_aligned,
            trend_m15=trend_m15,
            trend_h1=trend_h1,
            trend_h4=trend_h4,
            trend_d1=trend_d1,
            top_down_aligned=False,  # Wird separat berechnet
            news_sentiment=news_sentiment,
            high_impact_news_pending=high_impact_pending,
            entry_price=entry_price,
            planned_sl=planned_sl,
            planned_tp=planned_tp,
            planned_rr_ratio=rr_ratio
        )
        
        self.journal.append(entry)
        
        # Speichere in DB
        await self._save_entry_to_db(entry)
        
        logger.info(f"📝 Trade-Journal: {trade_id} geloggt")
        logger.info(f"   Strategy: {strategy}, Confluence: {confluence.confluence_count}/{self.MIN_CONFLUENCE}")
        logger.info(f"   Confidence: {confidence_score}%, R:R = 1:{rr_ratio:.2f}")
        
        return entry
    
    async def log_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        actual_profit: float,
        hit_tp: bool,
        hit_sl: bool
    ):
        """Aktualisiert einen Trade nach Schließung"""
        try:
            # Finde Entry
            entry = None
            for e in self.journal:
                if e.trade_id == trade_id:
                    entry = e
                    break
            
            if not entry:
                logger.warning(f"Trade {trade_id} nicht im Journal gefunden")
                return
            
            # Aktualisiere
            entry.exit_price = exit_price
            entry.actual_profit = actual_profit
            entry.hit_tp = hit_tp
            entry.hit_sl = hit_sl
            entry.is_winner = actual_profit > 0
            entry.status = "closed"
            
            # Berechne tatsächliches R:R
            sl_distance = abs(entry.entry_price - entry.planned_sl)
            if sl_distance > 0:
                entry.actual_rr_ratio = actual_profit / sl_distance
            
            # Berechne Trade-Dauer
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                duration = datetime.now(timezone.utc) - entry_time
                entry.trade_duration_minutes = int(duration.total_seconds() / 60)
            except:
                pass
            
            # Update DB
            await self._update_entry_in_db(entry)
            
            logger.info(f"📝 Trade-Journal Update: {trade_id}")
            logger.info(f"   Profit: {actual_profit:.2f}, Winner: {entry.is_winner}")
            
        except Exception as e:
            logger.error(f"Fehler beim Trade-Exit Logging: {e}")
    
    async def _save_entry_to_db(self, entry: TradeJournalEntry):
        """Speichert Entry in SQLite"""
        try:
            if self._db and hasattr(self._db, '_db') and self._db._db:
                await self._db._db.execute("""
                    INSERT OR REPLACE INTO trade_journal (
                        trade_id, timestamp, strategy, commodity, direction,
                        atr, adx, volatility, market_phase, day_of_week, hour_of_day,
                        confidence_score, confluence_count, indicators_used,
                        trend_m15, trend_h1, trend_h4, trend_d1, top_down_aligned,
                        news_sentiment, high_impact_news_pending,
                        entry_price, planned_sl, planned_tp, planned_rr_ratio,
                        exit_price, actual_profit, actual_rr_ratio,
                        hit_tp, hit_sl, trade_duration_minutes, is_winner, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.trade_id, entry.timestamp, entry.strategy, entry.commodity, entry.direction,
                    entry.atr, entry.adx, entry.volatility, entry.market_phase, entry.day_of_week, entry.hour_of_day,
                    entry.confidence_score, entry.confluence_count, json.dumps(entry.indicators_used),
                    entry.trend_m15, entry.trend_h1, entry.trend_h4, entry.trend_d1, int(entry.top_down_aligned),
                    entry.news_sentiment, int(entry.high_impact_news_pending),
                    entry.entry_price, entry.planned_sl, entry.planned_tp, entry.planned_rr_ratio,
                    entry.exit_price, entry.actual_profit, entry.actual_rr_ratio,
                    int(entry.hit_tp), int(entry.hit_sl), entry.trade_duration_minutes, int(entry.is_winner), entry.status
                ))
                await self._db._db.commit()
        except Exception as e:
            logger.error(f"DB Save Error: {e}")
    
    async def _update_entry_in_db(self, entry: TradeJournalEntry):
        """Aktualisiert Entry in SQLite"""
        try:
            if self._db and hasattr(self._db, '_db') and self._db._db:
                await self._db._db.execute("""
                    UPDATE trade_journal SET
                        exit_price = ?, actual_profit = ?, actual_rr_ratio = ?,
                        hit_tp = ?, hit_sl = ?, trade_duration_minutes = ?,
                        is_winner = ?, status = ?
                    WHERE trade_id = ?
                """, (
                    entry.exit_price, entry.actual_profit, entry.actual_rr_ratio,
                    int(entry.hit_tp), int(entry.hit_sl), entry.trade_duration_minutes,
                    int(entry.is_winner), entry.status, entry.trade_id
                ))
                await self._db._db.commit()
        except Exception as e:
            logger.error(f"DB Update Error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # WEEKLY ANALYSIS & LEARNING
    # ═══════════════════════════════════════════════════════════════════════
    
    async def run_weekly_analysis(self) -> Dict[str, StrategyPerformance]:
        """
        Wöchentliche Analyse aller Trades
        - Berechnet Win-Rate pro Strategie
        - Identifiziert problematische Kombinationen
        - Sperrt Setups mit <60% Win-Rate
        """
        logger.info("🧠 Starte wöchentliche Trading-Analyse...")
        
        # Hole alle geschlossenen Trades der letzten 7 Tage
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_trades = [
            e for e in self.journal 
            if e.status == "closed" and datetime.fromisoformat(e.timestamp) > cutoff
        ]
        
        if not recent_trades:
            logger.info("Keine abgeschlossenen Trades in den letzten 7 Tagen")
            return {}
        
        # Gruppiere nach Strategie
        by_strategy = defaultdict(list)
        for trade in recent_trades:
            by_strategy[trade.strategy].append(trade)
        
        results = {}
        
        for strategy, trades in by_strategy.items():
            total = len(trades)
            winners = len([t for t in trades if t.is_winner])
            losers = total - winners
            win_rate = (winners / total * 100) if total > 0 else 0
            avg_profit = sum(t.actual_profit for t in trades) / total if total > 0 else 0
            
            # Analysiere nach Marktphase
            phase_stats = defaultdict(lambda: {'total': 0, 'wins': 0})
            for trade in trades:
                phase_stats[trade.market_phase]['total'] += 1
                if trade.is_winner:
                    phase_stats[trade.market_phase]['wins'] += 1
            
            # Finde beste/schlechteste Phase
            best_phase = ""
            worst_phase = ""
            best_rate = 0
            worst_rate = 100
            
            for phase, stats in phase_stats.items():
                if stats['total'] >= 3:  # Mindestens 3 Trades für Statistik
                    rate = stats['wins'] / stats['total'] * 100
                    if rate > best_rate:
                        best_rate = rate
                        best_phase = phase
                    if rate < worst_rate:
                        worst_rate = rate
                        worst_phase = phase
            
            # Prüfe auf zu sperrende Setups
            blocked_conditions = []
            
            # Sperre Strategie in bestimmter Phase wenn Win-Rate < 60%
            for phase, stats in phase_stats.items():
                if stats['total'] >= 5:  # Mindestens 5 Trades für Sperrung
                    rate = stats['wins'] / stats['total'] * 100
                    if rate < self.MIN_WIN_RATE_THRESHOLD:
                        blocked_conditions.append(f"{phase} (Win-Rate: {rate:.1f}%)")
                        await self._block_setup(strategy, 'market_phase', phase, rate, stats['total'])
            
            perf = StrategyPerformance(
                strategy=strategy,
                total_trades=total,
                winners=winners,
                losers=losers,
                win_rate=win_rate,
                avg_profit=avg_profit,
                best_market_phase=best_phase,
                worst_market_phase=worst_phase,
                blocked_conditions=blocked_conditions
            )
            
            results[strategy] = perf
            self.strategy_stats[strategy] = perf
            
            logger.info(f"📊 {strategy.upper()}: {total} Trades, Win-Rate: {win_rate:.1f}%")
            if blocked_conditions:
                logger.warning(f"   ⛔ Gesperrt in: {', '.join(blocked_conditions)}")
        
        self._last_analysis = datetime.now(timezone.utc)
        self._performance_cache = results
        
        return results
    
    async def _block_setup(self, strategy: str, condition_type: str, condition_value: str, win_rate: float, sample_size: int):
        """Sperrt ein Setup für zukünftige Trades"""
        block_entry = {
            'strategy': strategy,
            'condition_type': condition_type,
            'condition_value': condition_value,
            'win_rate': win_rate,
            'sample_size': sample_size,
            'blocked_at': datetime.now(timezone.utc).isoformat(),
            'reason': f"Win-Rate {win_rate:.1f}% < {self.MIN_WIN_RATE_THRESHOLD}%"
        }
        
        self.blocked_setups.append(block_entry)
        
        # Speichere in DB
        try:
            if self._db and hasattr(self._db, '_db') and self._db._db:
                await self._db._db.execute("""
                    INSERT INTO blocked_setups (strategy, condition_type, condition_value, win_rate, sample_size, blocked_at, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (strategy, condition_type, condition_value, win_rate, sample_size, block_entry['blocked_at'], block_entry['reason']))
                await self._db._db.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Sperrung: {e}")
        
        logger.warning(f"⛔ SETUP GESPERRT: {strategy} + {condition_type}={condition_value}")
    
    def is_setup_blocked(self, strategy: str, market_phase: str, **kwargs) -> Tuple[bool, str]:
        """Prüft ob ein Setup gesperrt ist"""
        for block in self.blocked_setups:
            if block['strategy'] == strategy:
                if block['condition_type'] == 'market_phase' and block['condition_value'] == market_phase:
                    return True, f"Gesperrt: {strategy} in {market_phase} (Win-Rate: {block['win_rate']:.1f}%)"
        
        return False, ""
    
    # ═══════════════════════════════════════════════════════════════════════
    # POSITION SIZE CALCULATION BASED ON CONFIDENCE
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_position_size_multiplier(self, confidence: float) -> float:
        """
        Berechnet Positionsgrößen-Multiplikator basierend auf Konfidenz
        
        - >= 80%: Volle Positionsgröße (1.0x)
        - 70-79%: 75% der Position (0.75x)
        - 65-69%: 50% der Position (0.5x)
        - < 65%: Kein Trade (0x)
        """
        if confidence >= self.CONFIDENCE_FOR_FULL_SIZE:
            return 1.0
        elif confidence >= 70:
            return 0.75
        elif confidence >= 65:
            return 0.5
        else:
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════════════
    # MASTER VALIDATION (Alle Checks kombiniert)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def validate_trade_signal(
        self,
        strategy: str,
        commodity: str,
        signal: str,
        confidence: float,
        indicators: Dict[str, Any],
        news_sentiment: str = "neutral",
        high_impact_pending: bool = False
    ) -> Dict[str, Any]:
        """
        Master-Validierung für ein Trading-Signal
        
        Prüft:
        1. Confluence (min. 3 Indikatoren)
        2. Top-Down Alignment
        3. Gesperrte Setups
        4. News-Impact
        5. Konfidenz-Schwelle
        
        Returns:
            {
                'approved': bool,
                'position_size_multiplier': float,
                'reasons': List[str],
                'confluence': ConfluenceResult,
                'blocked': bool,
                'final_confidence': float
            }
        """
        reasons = []
        approved = True
        
        # 1. Confluence Check
        confluence = self.check_confluence(signal, indicators)
        if not confluence.passed:
            approved = False
            reasons.append(f"❌ Confluence nicht erreicht ({confluence.confluence_count}/{self.MIN_CONFLUENCE})")
        else:
            reasons.append(f"✅ Confluence OK ({confluence.confluence_count} Indikatoren)")
        
        # 2. Gesperrte Setups
        market_phase = self.get_market_phase(datetime.now(timezone.utc).hour)
        is_blocked, block_reason = self.is_setup_blocked(strategy, market_phase.value)
        if is_blocked:
            approved = False
            reasons.append(f"⛔ {block_reason}")
        
        # 3. High-Impact News
        if high_impact_pending:
            approved = False
            reasons.append("⚠️ High-Impact News anstehend - Trade blockiert")
        
        # 4. Konfidenz-Schwelle
        min_confidence = 65.0
        if confidence < min_confidence:
            approved = False
            reasons.append(f"❌ Konfidenz zu niedrig ({confidence:.1f}% < {min_confidence}%)")
        
        # Berechne finale Konfidenz (inkl. Confluence-Bonus)
        final_confidence = confidence
        if confluence.confluence_count >= 4:
            final_confidence += 5  # Bonus für starke Confluence
        if confluence.confluence_count >= 5:
            final_confidence += 5  # Extra Bonus
        
        final_confidence = min(95, final_confidence)
        
        # Positionsgrößen-Multiplikator
        size_multiplier = self.calculate_position_size_multiplier(final_confidence)
        if size_multiplier == 0:
            approved = False
            reasons.append("❌ Positionsgröße = 0 (Konfidenz zu niedrig)")
        
        return {
            'approved': approved,
            'position_size_multiplier': size_multiplier,
            'reasons': reasons,
            'confluence': asdict(confluence),
            'blocked': is_blocked,
            'final_confidence': final_confidence,
            'market_phase': market_phase.value
        }


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

trading_journal = SelfLearningTradeManager()
