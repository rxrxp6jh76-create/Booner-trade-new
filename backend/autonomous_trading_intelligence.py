"""
🧠 AUTONOMOUS TRADING INTELLIGENCE - V2.5.0
============================================

Universal Trading KI mit 80% Trefferquoten-Ziel

Features:
1. Dynamic Strategy Selection - Automatische Strategie-Wahl nach Marktphase
2. Universal Confidence Score - Gewichtete 4-Säulen-Berechnung
3. Autonomous Risk Circuits - Breakeven + Time-Exit
4. Strategy Clusters - Gruppierung nach Marktbedingungen
5. Meta-Learning - Tägliche Evaluierung und Anpassung

Architektur:
- Market State Detection → Cluster Matching → Confidence Score → Execution
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

class MarketState(Enum):
    """Markt-Zustände für Dynamic Strategy Selection"""
    STRONG_UPTREND = "strong_uptrend"      # ADX > 40, Preis > EMAs
    UPTREND = "uptrend"                     # ADX > 25, bullish
    DOWNTREND = "downtrend"                 # ADX > 25, bearish
    STRONG_DOWNTREND = "strong_downtrend"  # ADX > 40, Preis < EMAs
    RANGE = "range"                         # ADX < 20, Seitwärts
    HIGH_VOLATILITY = "high_volatility"    # ATR > 2x Normal
    CHAOS = "chaos"                         # Keine klare Richtung, hohes Risiko


class StrategyCluster(Enum):
    """Strategie-Cluster nach Marktbedingungen"""
    TREND_FOLLOWING = "trend_following"     # EMA Cross, Ichimoku, ADX Trends
    MEAN_REVERSION = "mean_reversion"       # RSI, Bollinger, VWAP Return
    BREAKOUT = "breakout"                   # Range Breakout, Squeeze
    PRICE_ACTION = "price_action"           # Candlestick Patterns
    HARMONIC = "harmonic"                   # Fibonacci, Elliott
    SCALPING = "scalping"                   # Micro-Momentum, Order Flow


# V2.3.38: INTELLIGENTERES Mapping - Mehr Flexibilität, weniger Blockaden
# Jeder Markt-Zustand erlaubt jetzt mehr Strategien mit unterschiedlicher Priorität
STRATEGY_MARKET_FIT = {
    # Starker Aufwärtstrend: Alle Trend-Strategien + Breakout
    MarketState.STRONG_UPTREND: [
        StrategyCluster.TREND_FOLLOWING, 
        StrategyCluster.BREAKOUT, 
        StrategyCluster.SCALPING
    ],
    # Aufwärtstrend: Trend + Scalping
    MarketState.UPTREND: [
        StrategyCluster.TREND_FOLLOWING, 
        StrategyCluster.PRICE_ACTION,
        StrategyCluster.SCALPING,
        StrategyCluster.MEAN_REVERSION  # Kann auch gegen Trend handeln
    ],
    # Abwärtstrend: Trend + Scalping
    MarketState.DOWNTREND: [
        StrategyCluster.TREND_FOLLOWING, 
        StrategyCluster.PRICE_ACTION,
        StrategyCluster.SCALPING,
        StrategyCluster.MEAN_REVERSION
    ],
    # Starker Abwärtstrend
    MarketState.STRONG_DOWNTREND: [
        StrategyCluster.TREND_FOLLOWING, 
        StrategyCluster.BREAKOUT, 
        StrategyCluster.SCALPING
    ],
    # Range/Seitwärts: ALLE Strategien erlaubt, Mean Reversion ist optimal
    MarketState.RANGE: [
        StrategyCluster.MEAN_REVERSION,  # Optimal
        StrategyCluster.SCALPING,        # Gut
        StrategyCluster.TREND_FOLLOWING,  # Mit Vorsicht
        StrategyCluster.BREAKOUT          # Für Range-Breakouts
    ],
    # Hohe Volatilität: Breakout + Scalping + Trend
    MarketState.HIGH_VOLATILITY: [
        StrategyCluster.BREAKOUT, 
        StrategyCluster.SCALPING,
        StrategyCluster.TREND_FOLLOWING
    ],
    # Chaos: Nur Scalping mit strengem Risiko
    MarketState.CHAOS: [StrategyCluster.SCALPING]
}

# V2.3.38: Multi-Cluster Mapping - Strategien können mehreren Clustern angehören
STRATEGY_TO_CLUSTER = {
    "scalping": StrategyCluster.SCALPING,
    "day": StrategyCluster.TREND_FOLLOWING,
    "day_trading": StrategyCluster.TREND_FOLLOWING,
    "swing": StrategyCluster.TREND_FOLLOWING,
    "swing_trading": StrategyCluster.TREND_FOLLOWING,
    "momentum": StrategyCluster.TREND_FOLLOWING,
    "breakout": StrategyCluster.BREAKOUT,
    "mean_reversion": StrategyCluster.MEAN_REVERSION,
    "grid": StrategyCluster.MEAN_REVERSION
}

# V2.3.38: Sekundäre Cluster - erlaubt Strategien in anderen Märkten zu handeln (mit Penalty)
STRATEGY_SECONDARY_CLUSTERS = {
    "scalping": [StrategyCluster.MEAN_REVERSION],  # Scalping funktioniert auch im Range
    "day": [StrategyCluster.SCALPING],              # Day kann auch scalpen
    "day_trading": [StrategyCluster.SCALPING],
    "swing": [StrategyCluster.MEAN_REVERSION],      # Swing kann Mean Reversion machen
    "swing_trading": [StrategyCluster.MEAN_REVERSION],
    "momentum": [StrategyCluster.BREAKOUT],         # Momentum profitiert von Breakouts
    "breakout": [StrategyCluster.TREND_FOLLOWING],  # Breakout folgt Trends
    "mean_reversion": [StrategyCluster.SCALPING],   # Mean Rev kann scalpen
    "grid": [StrategyCluster.SCALPING]              # Grid kann scalpen
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MarketAnalysis:
    """Ergebnis der Markt-Zustand-Analyse"""
    state: MarketState
    adx: float
    atr: float
    atr_normalized: float  # ATR / Durchschnitt
    trend_direction: str  # up, down, neutral
    volatility_level: str  # low, normal, high, extreme
    suitable_clusters: List[StrategyCluster]
    blocked_strategies: List[str]
    timestamp: str


@dataclass
class UniversalConfidenceScore:
    """Gewichteter Confidence Score nach 4-Säulen-Modell"""
    # Die 4 Säulen (Gesamt = 100%)
    base_signal_score: float      # 40% - Strategie-Signal-Qualität
    trend_confluence_score: float  # 25% - Multi-Timeframe Alignment
    volatility_score: float        # 20% - ATR/Volume Check
    sentiment_score: float         # 15% - News/Sentiment
    
    # Berechnetes Ergebnis
    total_score: float
    passed_threshold: bool  # >= 80%
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    penalties: List[str] = field(default_factory=list)
    bonuses: List[str] = field(default_factory=list)


@dataclass 
class RiskCircuitStatus:
    """Status der Risiko-Schaltkreise für eine Position"""
    trade_id: str
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    
    # Breakeven Status
    breakeven_triggered: bool = False
    breakeven_price: float = 0.0
    progress_to_tp_percent: float = 0.0
    
    # Time-Exit Status
    entry_time: str = ""
    elapsed_minutes: int = 0
    time_exit_threshold_minutes: int = 240  # 4 Stunden default
    time_exit_triggered: bool = False
    
    # Trailing Stop Status
    trailing_stop_active: bool = False
    trailing_stop_price: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# MAIN CLASS: AUTONOMOUS TRADING INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

class AutonomousTradingIntelligence:
    """
    Universelle Trading-KI mit autonomer Strategie-Selektion
    
    Ziel: 80% Trefferquote durch:
    - Dynamic Strategy Selection basierend auf Markt-Zustand
    - Universal Confidence Score (4-Säulen-Modell)
    - Autonomous Risk Circuits (Breakeven + Time-Exit)
    - Meta-Learning mit täglicher Evaluierung
    """
    
    # Konfiguration
    MIN_CONFIDENCE_THRESHOLD = 80.0  # Nur >= 80% werden ausgeführt
    BREAKEVEN_TRIGGER_PERCENT = 50.0  # Bei 50% TP-Erreichung → SL auf Einstand
    TIME_EXIT_MINUTES = 240  # 4 Stunden
    
    # Gewichtung der 4 Säulen
    WEIGHT_BASE_SIGNAL = 40
    WEIGHT_TREND_CONFLUENCE = 25
    WEIGHT_VOLATILITY = 20
    WEIGHT_SENTIMENT = 15
    
    def __init__(self):
        self.active_risk_circuits: Dict[str, RiskCircuitStatus] = {}
        self.strategy_performance: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'current_weight': 1.0
        })
        self._last_market_analysis: Dict[str, MarketAnalysis] = {}
        
    # ═══════════════════════════════════════════════════════════════════════
    # 1. MARKET STATE DETECTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def detect_market_state(
        self,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float] = None
    ) -> MarketAnalysis:
        """
        Analysiert den aktuellen Markt-Zustand
        
        Kategorisiert in: Trend (Bull/Bear), Seitwärts (Range), Hochvolatil (Chaos)
        """
        if len(prices) < 50:
            return MarketAnalysis(
                state=MarketState.CHAOS,
                adx=0, atr=0, atr_normalized=0,
                trend_direction="unknown",
                volatility_level="unknown",
                suitable_clusters=[],
                blocked_strategies=list(STRATEGY_TO_CLUSTER.keys()),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # 1. ADX berechnen (Trendstärke)
        adx = self._calculate_adx(prices, highs, lows, 14)
        
        # 2. ATR berechnen (Volatilität)
        atr = self._calculate_atr(prices, highs, lows, 14)
        avg_atr = self._calculate_atr(prices[:-50], highs[:-50], lows[:-50], 14) if len(prices) > 100 else atr
        atr_normalized = atr / avg_atr if avg_atr > 0 else 1.0
        
        # 3. Trend-Richtung (EMA 20 vs EMA 50)
        ema_20 = self._calculate_ema(prices, 20)
        ema_50 = self._calculate_ema(prices, 50)
        current_price = prices[-1]
        
        if current_price > ema_20 > ema_50:
            trend_direction = "up"
        elif current_price < ema_20 < ema_50:
            trend_direction = "down"
        else:
            trend_direction = "neutral"
        
        # 4. Volatilitäts-Level
        if atr_normalized > 2.0:
            volatility_level = "extreme"
        elif atr_normalized > 1.5:
            volatility_level = "high"
        elif atr_normalized > 0.7:
            volatility_level = "normal"
        else:
            volatility_level = "low"
        
        # 5. Markt-Zustand bestimmen
        if volatility_level == "extreme":
            state = MarketState.HIGH_VOLATILITY
        elif adx > 40:
            state = MarketState.STRONG_UPTREND if trend_direction == "up" else MarketState.STRONG_DOWNTREND
        elif adx > 25:
            state = MarketState.UPTREND if trend_direction == "up" else MarketState.DOWNTREND
        elif adx < 20:
            state = MarketState.RANGE
        else:
            state = MarketState.CHAOS if volatility_level == "high" else MarketState.RANGE
        
        # 6. Passende Strategie-Cluster
        suitable_clusters = STRATEGY_MARKET_FIT.get(state, [])
        
        # 7. Blockierte Strategien (nicht passend zum Markt)
        blocked_strategies = []
        for strategy, cluster in STRATEGY_TO_CLUSTER.items():
            if cluster not in suitable_clusters:
                blocked_strategies.append(strategy)
        
        analysis = MarketAnalysis(
            state=state,
            adx=adx,
            atr=atr,
            atr_normalized=atr_normalized,
            trend_direction=trend_direction,
            volatility_level=volatility_level,
            suitable_clusters=suitable_clusters,
            blocked_strategies=blocked_strategies,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"🌍 MARKT-ZUSTAND: {state.value}")
        logger.info(f"   ADX: {adx:.1f}, ATR: {atr:.4f} ({atr_normalized:.2f}x normal)")
        logger.info(f"   Trend: {trend_direction}, Volatilität: {volatility_level}")
        logger.info(f"   Geeignete Cluster: {[c.value for c in suitable_clusters]}")
        if blocked_strategies:
            logger.info(f"   ⛔ Blockierte Strategien: {blocked_strategies}")
        
        return analysis
    
    def is_strategy_suitable_for_market(self, strategy: str, market_analysis: MarketAnalysis) -> Tuple[bool, str]:
        """
        V2.3.38: VERBESSERTES Strategie-Matching
        
        Prüft ob eine Strategie zum aktuellen Markt passt.
        Berücksichtigt jetzt auch sekundäre Cluster für mehr Flexibilität.
        
        Returns:
            (suitable: bool, reason: str)
        """
        # Normalisiere Strategy-Namen
        strategy_clean = strategy.replace('_trading', '').replace('_', '')
        
        # Hole primären und sekundären Cluster
        primary_cluster = STRATEGY_TO_CLUSTER.get(strategy, STRATEGY_TO_CLUSTER.get(strategy_clean))
        secondary_clusters = STRATEGY_SECONDARY_CLUSTERS.get(strategy, STRATEGY_SECONDARY_CLUSTERS.get(strategy_clean, []))
        
        suitable_clusters = market_analysis.suitable_clusters
        
        # Prüfe primären Cluster
        if primary_cluster in suitable_clusters:
            return True, f"✅ Strategie '{strategy}' ist OPTIMAL für '{market_analysis.state.value}'"
        
        # Prüfe sekundäre Cluster - erlaubt mit Warnung
        for sec_cluster in secondary_clusters:
            if sec_cluster in suitable_clusters:
                return True, f"⚠️ Strategie '{strategy}' ist AKZEPTABEL für '{market_analysis.state.value}' (sekundärer Match)"
        
        # V2.3.38: NICHT MEHR BLOCKIEREN - nur warnen und mit reduziertem Score handeln
        # Alte Logik: return False, "blockiert"
        # Neue Logik: Erlaube den Trade, aber mit Penalty im Confidence Score
        logger.warning(f"⚠️ Strategie '{strategy}' nicht optimal für Markt '{market_analysis.state.value}' - Trade erlaubt mit Penalty")
        return True, f"⚠️ Strategie '{strategy}' nicht optimal - Trade mit Risiko-Penalty erlaubt"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 2. UNIVERSAL CONFIDENCE SCORE (4-Säulen-Modell)
    # ═══════════════════════════════════════════════════════════════════════
    
    def calculate_universal_confidence(
        self,
        strategy: str,
        signal: str,  # BUY/SELL
        indicators: Dict[str, Any],
        market_analysis: MarketAnalysis,
        trend_h1: str = "neutral",
        trend_h4: str = "neutral",
        trend_d1: str = "neutral",
        news_sentiment: str = "neutral",
        high_impact_news_pending: bool = False,
        confluence_count: int = 0
    ) -> UniversalConfidenceScore:
        """
        V2.3.38: OPTIMIERTER Universal Confidence Score
        
        Berechnet den Universal Confidence Score nach 4-Säulen-Modell:
        
        1. Basis-Signal (40%): Strategie-Signal-Qualität + Confluence
        2. Trend-Konfluenz (25%): Multi-Timeframe Alignment (H1, H4, D1)
        3. Volatilitäts-Check (20%): ATR + Volume
        4. Sentiment (15%): News + Market Mood
        
        V2.3.38 ÄNDERUNGEN:
        - Basis-Score startet bei 25 (nicht 0) für aktivere Trading
        - Confluence-Boni erhöht
        - Weniger harte Penalties
        """
        penalties = []
        bonuses = []
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 1: BASIS-SIGNAL (40 Punkte max)
        # V2.3.38: Mehr Grundpunkte für aktiveres Trading
        # ═══════════════════════════════════════════════════════════════
        base_signal_score = 15  # V2.3.38: Start bei 15 statt 0
        
        # Strategie passt zum Markt?
        strategy_suitable, suitability_msg = self.is_strategy_suitable_for_market(strategy, market_analysis)
        
        if "OPTIMAL" in suitability_msg:
            base_signal_score += 20
            bonuses.append("Strategie OPTIMAL für Markt (+20)")
        elif "AKZEPTABEL" in suitability_msg:
            base_signal_score += 12
            bonuses.append("Strategie akzeptabel für Markt (+12)")
        elif strategy_suitable:
            base_signal_score += 5  # Kleiner Bonus auch bei nicht-optimalen Strategien
            penalties.append("Strategie nicht optimal (-5 von möglichen +20)")
        else:
            base_signal_score -= 5
            penalties.append("Strategie passt NICHT zum Markt (-5)")
        
        # Confluence-Bonus (Mehrere Indikatoren stimmen überein)
        # V2.3.38: Erhöhte Boni
        if confluence_count >= 5:
            base_signal_score += 25
            bonuses.append(f"Exzellente Confluence ({confluence_count} Indikatoren) (+25)")
        elif confluence_count >= 3:
            base_signal_score += 18
            bonuses.append(f"Gute Confluence ({confluence_count} Indikatoren) (+18)")
        elif confluence_count >= 2:
            base_signal_score += 12
            bonuses.append(f"Basis Confluence ({confluence_count} Indikatoren) (+12)")
        elif confluence_count >= 1:
            base_signal_score += 5
            bonuses.append(f"Einzelner Indikator bestätigt (+5)")
        else:
            penalties.append(f"Keine Confluence ({confluence_count} Indikatoren)")
        
        base_signal_score = max(0, min(40, base_signal_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 2: TREND-KONFLUENZ (25 Punkte max)
        # ═══════════════════════════════════════════════════════════════
        trend_confluence_score = 0
        is_buy = signal == 'BUY'
        
        # Timeframe Alignment Check
        aligned_timeframes = 0
        
        # D1 Trend
        d1_aligned = (is_buy and trend_d1 in ['up', 'strong_up']) or (not is_buy and trend_d1 in ['down', 'strong_down'])
        if d1_aligned:
            aligned_timeframes += 1
            trend_confluence_score += 10
        elif trend_d1 == 'neutral':
            trend_confluence_score += 3
        else:
            penalties.append(f"D1 gegen Signal ({trend_d1})")
        
        # H4 Trend
        h4_aligned = (is_buy and trend_h4 in ['up', 'strong_up']) or (not is_buy and trend_h4 in ['down', 'strong_down'])
        if h4_aligned:
            aligned_timeframes += 1
            trend_confluence_score += 10
        elif trend_h4 == 'neutral':
            trend_confluence_score += 3
        
        # H1 Trend
        h1_aligned = (is_buy and trend_h1 in ['up', 'strong_up']) or (not is_buy and trend_h1 in ['down', 'strong_down'])
        if h1_aligned:
            aligned_timeframes += 1
            trend_confluence_score += 5
        
        if aligned_timeframes == 3:
            bonuses.append("Alle Timeframes aligned (+Bonus)")
        
        trend_confluence_score = max(0, min(25, trend_confluence_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 3: VOLATILITÄTS-CHECK (20 Punkte max)
        # ═══════════════════════════════════════════════════════════════
        volatility_score = 0
        
        # ATR-Normalisierung
        atr_norm = market_analysis.atr_normalized
        
        # Ideale Volatilität: 0.8 - 1.5x normal
        if 0.8 <= atr_norm <= 1.5:
            volatility_score += 15
            bonuses.append("Optimale Volatilität (+15)")
        elif 0.5 <= atr_norm <= 2.0:
            volatility_score += 10
            bonuses.append("Akzeptable Volatilität (+10)")
        elif atr_norm > 2.5:
            volatility_score -= 5
            penalties.append(f"Extreme Volatilität ({atr_norm:.2f}x) (-5)")
        else:
            volatility_score += 5
        
        # Volume Check
        volume_surge = indicators.get('volume_surge', False)
        volume_peak = indicators.get('volume_peak', False)
        if volume_surge or volume_peak:
            volatility_score += 5
            bonuses.append("Volume bestätigt Signal (+5)")
        
        volatility_score = max(0, min(20, volatility_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 4: SENTIMENT (15 Punkte max)
        # ═══════════════════════════════════════════════════════════════
        sentiment_score = 0
        
        # News Sentiment
        if news_sentiment == 'bullish' and is_buy:
            sentiment_score += 10
            bonuses.append("News unterstützt BUY (+10)")
        elif news_sentiment == 'bearish' and not is_buy:
            sentiment_score += 10
            bonuses.append("News unterstützt SELL (+10)")
        elif news_sentiment == 'neutral':
            sentiment_score += 5
        else:
            sentiment_score -= 5
            penalties.append(f"News gegen Signal ({news_sentiment})")
        
        # High-Impact News Penalty
        if high_impact_news_pending:
            sentiment_score -= 15
            penalties.append("⚠️ High-Impact News anstehend (-15)")
        else:
            sentiment_score += 5
            bonuses.append("Keine kritischen News (+5)")
        
        sentiment_score = max(0, min(15, sentiment_score))
        
        # ═══════════════════════════════════════════════════════════════
        # GESAMT-SCORE BERECHNEN
        # ═══════════════════════════════════════════════════════════════
        total_score = base_signal_score + trend_confluence_score + volatility_score + sentiment_score
        total_score = max(0, min(100, total_score))
        
        passed_threshold = total_score >= self.MIN_CONFIDENCE_THRESHOLD
        
        result = UniversalConfidenceScore(
            base_signal_score=base_signal_score,
            trend_confluence_score=trend_confluence_score,
            volatility_score=volatility_score,
            sentiment_score=sentiment_score,
            total_score=total_score,
            passed_threshold=passed_threshold,
            penalties=penalties,
            bonuses=bonuses,
            details={
                'strategy': strategy,
                'signal': signal,
                'market_state': market_analysis.state.value,
                'confluence_count': confluence_count,
                'atr_normalized': atr_norm
            }
        )
        
        logger.info(f"📊 UNIVERSAL CONFIDENCE SCORE: {total_score:.1f}%")
        logger.info(f"   ├─ Basis-Signal: {base_signal_score}/{self.WEIGHT_BASE_SIGNAL}")
        logger.info(f"   ├─ Trend-Konfluenz: {trend_confluence_score}/{self.WEIGHT_TREND_CONFLUENCE}")
        logger.info(f"   ├─ Volatilität: {volatility_score}/{self.WEIGHT_VOLATILITY}")
        logger.info(f"   └─ Sentiment: {sentiment_score}/{self.WEIGHT_SENTIMENT}")
        logger.info(f"   {'✅ TRADE ERLAUBT' if passed_threshold else '❌ TRADE BLOCKIERT'} (Schwelle: {self.MIN_CONFIDENCE_THRESHOLD}%)")
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # 3. AUTONOMOUS RISK CIRCUITS
    # ═══════════════════════════════════════════════════════════════════════
    
    def register_trade_for_risk_monitoring(
        self,
        trade_id: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        strategy: str,
        time_exit_minutes: int = None
    ) -> RiskCircuitStatus:
        """
        Registriert einen Trade für Risiko-Überwachung
        """
        status = RiskCircuitStatus(
            trade_id=trade_id,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.now(timezone.utc).isoformat(),
            time_exit_threshold_minutes=time_exit_minutes or self.TIME_EXIT_MINUTES
        )
        
        # Bei Momentum-Strategie: Trailing Stop aktivieren
        if strategy == 'momentum':
            status.trailing_stop_active = True
            status.trailing_stop_price = stop_loss
        
        self.active_risk_circuits[trade_id] = status
        
        logger.info(f"🔒 Risk Circuit registriert: {trade_id}")
        logger.info(f"   Entry: {entry_price:.4f}, SL: {stop_loss:.4f}, TP: {take_profit:.4f}")
        
        return status
    
    def check_risk_circuits(self, trade_id: str, current_price: float) -> Dict[str, Any]:
        """
        Prüft alle Risiko-Schaltkreise für einen Trade
        
        Returns:
            {
                'action': 'none' | 'move_sl_breakeven' | 'time_exit' | 'trailing_stop',
                'new_sl': float (optional),
                'reason': str
            }
        """
        if trade_id not in self.active_risk_circuits:
            return {'action': 'none', 'reason': 'Trade nicht registriert'}
        
        status = self.active_risk_circuits[trade_id]
        status.current_price = current_price
        
        # Berechne Fortschritt zum TP
        entry = status.entry_price
        tp = status.take_profit
        sl = status.stop_loss
        
        # Long Trade
        if tp > entry:
            total_distance = tp - entry
            current_progress = current_price - entry
            progress_percent = (current_progress / total_distance * 100) if total_distance > 0 else 0
        # Short Trade
        else:
            total_distance = entry - tp
            current_progress = entry - current_price
            progress_percent = (current_progress / total_distance * 100) if total_distance > 0 else 0
        
        status.progress_to_tp_percent = progress_percent
        
        # ═══════════════════════════════════════════════════════════════
        # CHECK 1: BREAKEVEN-AUTOMATIK (50% TP erreicht → SL auf Einstand)
        # ═══════════════════════════════════════════════════════════════
        if not status.breakeven_triggered and progress_percent >= self.BREAKEVEN_TRIGGER_PERCENT:
            # Berechne Breakeven-Preis (Entry + Spread/Gebühren)
            spread_buffer = abs(tp - entry) * 0.01  # 1% Buffer für Gebühren
            
            if tp > entry:  # Long
                breakeven_price = entry + spread_buffer
            else:  # Short
                breakeven_price = entry - spread_buffer
            
            status.breakeven_triggered = True
            status.breakeven_price = breakeven_price
            
            logger.info(f"🔐 BREAKEVEN AKTIVIERT für {trade_id}")
            logger.info(f"   Progress: {progress_percent:.1f}%, Neuer SL: {breakeven_price:.4f}")
            
            return {
                'action': 'move_sl_breakeven',
                'new_sl': breakeven_price,
                'reason': f'50% TP erreicht ({progress_percent:.1f}%) - SL auf Breakeven'
            }
        
        # ═══════════════════════════════════════════════════════════════
        # CHECK 2: TIME-EXIT (Stagnierender Trade)
        # ═══════════════════════════════════════════════════════════════
        try:
            entry_time = datetime.fromisoformat(status.entry_time)
            elapsed = datetime.now(timezone.utc) - entry_time
            status.elapsed_minutes = int(elapsed.total_seconds() / 60)
            
            # Time-Exit wenn:
            # - Zeit überschritten UND
            # - Trade ist nicht signifikant im Plus (< 25% des TP)
            if status.elapsed_minutes >= status.time_exit_threshold_minutes:
                if progress_percent < 25:
                    status.time_exit_triggered = True
                    
                    logger.info(f"⏰ TIME-EXIT für {trade_id}")
                    logger.info(f"   Elapsed: {status.elapsed_minutes}min, Progress: {progress_percent:.1f}%")
                    
                    return {
                        'action': 'time_exit',
                        'reason': f'Zeit überschritten ({status.elapsed_minutes}min) ohne signifikanten Progress ({progress_percent:.1f}%)'
                    }
        except Exception as e:
            logger.debug(f"Time check error: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # CHECK 3: TRAILING STOP (für Momentum-Trades)
        # ═══════════════════════════════════════════════════════════════
        if status.trailing_stop_active and progress_percent > 0:
            # Trailing Stop zieht nach wenn Trade 1% im Plus
            if progress_percent >= 30:  # 30% Progress
                # Berechne neuen Trailing Stop (50% des Gewinns sichern)
                if tp > entry:  # Long
                    new_trailing = entry + (current_progress * 0.5)
                    if new_trailing > status.trailing_stop_price:
                        status.trailing_stop_price = new_trailing
                        
                        return {
                            'action': 'trailing_stop',
                            'new_sl': new_trailing,
                            'reason': f'Trailing Stop nachgezogen auf {new_trailing:.4f} (50% Gewinn gesichert)'
                        }
                else:  # Short
                    new_trailing = entry - (current_progress * 0.5)
                    if new_trailing < status.trailing_stop_price:
                        status.trailing_stop_price = new_trailing
                        
                        return {
                            'action': 'trailing_stop',
                            'new_sl': new_trailing,
                            'reason': f'Trailing Stop nachgezogen auf {new_trailing:.4f}'
                        }
        
        return {'action': 'none', 'reason': 'Keine Aktion erforderlich'}
    
    def remove_risk_circuit(self, trade_id: str):
        """Entfernt einen Trade aus der Risiko-Überwachung"""
        if trade_id in self.active_risk_circuits:
            del self.active_risk_circuits[trade_id]
            logger.info(f"🔓 Risk Circuit entfernt: {trade_id}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 4. DYNAMIC STRATEGY SELECTION (Der KI-Coach)
    # ═══════════════════════════════════════════════════════════════════════
    
    def select_best_strategy(
        self,
        market_analysis: MarketAnalysis,
        available_strategies: List[str],
        commodity_id: str
    ) -> Tuple[Optional[str], str]:
        """
        Wählt die beste Strategie für den aktuellen Markt-Zustand
        
        Returns:
            (best_strategy: str or None, reason: str)
        """
        suitable_strategies = []
        
        for strategy in available_strategies:
            suitable, reason = self.is_strategy_suitable_for_market(strategy, market_analysis)
            if suitable:
                # Gewichtung nach Performance
                weight = self.strategy_performance[strategy].get('current_weight', 1.0)
                suitable_strategies.append((strategy, weight, reason))
        
        if not suitable_strategies:
            return None, f"Keine Strategie passt zu Markt-Zustand '{market_analysis.state.value}'"
        
        # Sortiere nach Gewichtung (Performance)
        suitable_strategies.sort(key=lambda x: x[1], reverse=True)
        
        best = suitable_strategies[0]
        return best[0], f"Beste Strategie: {best[0]} (Gewicht: {best[1]:.2f})"
    
    # ═══════════════════════════════════════════════════════════════════════
    # 5. META-LEARNING (Tägliche Evaluierung)
    # ═══════════════════════════════════════════════════════════════════════
    
    def update_strategy_performance(self, strategy: str, is_winner: bool, profit: float):
        """
        Aktualisiert die Performance-Statistik einer Strategie
        
        Wird nach jedem geschlossenen Trade aufgerufen
        """
        stats = self.strategy_performance[strategy]
        stats['trades'] += 1
        if is_winner:
            stats['wins'] += 1
        
        # Berechne neue Gewichtung
        win_rate = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0.5
        
        # Gewichtung basierend auf Win-Rate
        # Win-Rate 80% → Gewicht 1.6
        # Win-Rate 50% → Gewicht 1.0
        # Win-Rate 30% → Gewicht 0.6
        stats['current_weight'] = 0.4 + (win_rate * 1.5)
        
        logger.info(f"📈 Strategy Performance Update: {strategy}")
        logger.info(f"   Trades: {stats['trades']}, Wins: {stats['wins']}")
        logger.info(f"   Win-Rate: {win_rate*100:.1f}%, Neue Gewichtung: {stats['current_weight']:.2f}")
    
    def run_daily_meta_learning(self) -> Dict[str, Any]:
        """
        Tägliche Evaluierung: Welche Strategien funktionieren aktuell am besten?
        
        Passt die Gewichtungen autonom an
        """
        logger.info("🧠 META-LEARNING: Tägliche Evaluierung...")
        
        results = {}
        
        for strategy, stats in self.strategy_performance.items():
            if stats['trades'] < 5:
                continue  # Zu wenig Daten
            
            win_rate = stats['wins'] / stats['trades'] * 100
            
            # Automatische Anpassung
            if win_rate >= 80:
                stats['current_weight'] = 1.6
                status = "⭐ Top-Performer"
            elif win_rate >= 60:
                stats['current_weight'] = 1.2
                status = "✅ Gut"
            elif win_rate >= 40:
                stats['current_weight'] = 0.8
                status = "⚠️ Durchschnitt"
            else:
                stats['current_weight'] = 0.4
                status = "❌ Schwach - reduziert"
            
            results[strategy] = {
                'win_rate': win_rate,
                'trades': stats['trades'],
                'weight': stats['current_weight'],
                'status': status
            }
            
            logger.info(f"   {strategy}: {status} (Win-Rate: {win_rate:.1f}%, Gewicht: {stats['current_weight']:.2f})")
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════
    # HILFSMETHODEN
    # ═══════════════════════════════════════════════════════════════════════
    
    def _calculate_atr(self, prices: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        """Berechnet Average True Range"""
        if len(prices) < period + 1:
            return abs(prices[-1] - prices[-2]) if len(prices) >= 2 else prices[-1] * 0.01
        
        true_ranges = []
        for i in range(1, min(len(prices), len(highs), len(lows))):
            high = highs[i]
            low = lows[i]
            prev_close = prices[i-1]
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period if true_ranges else prices[-1] * 0.01
    
    def _calculate_adx(self, prices: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        """Berechnet ADX (Average Directional Index) - vereinfacht"""
        if len(prices) < period + 1:
            return 25.0  # Neutraler Wert
        
        # Vereinfachte ADX-Berechnung
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_change = sum(price_changes[-period:]) / period if price_changes else 0
        avg_price = sum(prices[-period:]) / period
        
        adx = (avg_change / avg_price * 100 * 10) if avg_price > 0 else 25
        return min(100, max(0, adx))
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Berechnet Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

autonomous_trading = AutonomousTradingIntelligence()
