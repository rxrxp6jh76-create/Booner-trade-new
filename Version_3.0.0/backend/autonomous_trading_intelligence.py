"""
🧠 AUTONOMOUS TRADING INTELLIGENCE - V2.5.0 (Ultimate AI Upgrade)
==================================================================

Universal Trading KI mit 80% Trefferquoten-Ziel

Features:
1. Dynamic Strategy Selection - Automatische Strategie-Wahl nach Marktphase
2. Universal Confidence Score - Gewichtete 4-Säulen-Berechnung
3. Autonomous Risk Circuits - Breakeven + Time-Exit
4. Strategy Clusters - Gruppierung nach Marktbedingungen
5. Meta-Learning - Tägliche Evaluierung und Anpassung
6. V2.5.0: Asset-Class Specific Logic (Commodities, Forex, BTC)
7. V2.5.0: Multi-Timeframe Confluence (M5 + H1/H4)
8. V2.5.0: Relative Strength Analysis
9. V2.5.0: ATR-basierte dynamische SL/TP

Architektur:
- Market State Detection → Asset-Class Analysis → Cluster Matching → Deep Confidence → Execution
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ASSET CLASS DEFINITIONS (V2.5.0 NEU)
# ═══════════════════════════════════════════════════════════════════════════

class AssetClass(Enum):
    """Asset-Klassen für spezifische Behandlung"""
    COMMODITY_METAL = "commodity_metal"      # Gold, Silver, Platinum
    COMMODITY_ENERGY = "commodity_energy"    # Oil, Gas
    COMMODITY_AGRIC = "commodity_agric"      # Wheat, Corn, Coffee, etc.
    FOREX_MAJOR = "forex_major"              # EUR/USD, GBP/USD
    FOREX_MINOR = "forex_minor"              # Andere Paare
    CRYPTO = "crypto"                        # Bitcoin, etc.
    INDEX = "index"                          # S&P500, DAX

ASSET_CLASS_MAP = {
    # ═══════════════════════════════════════════════════════════════════════
    # V3.0.0: VOLLSTÄNDIGE ASSET-MATRIX (20 Assets)
    # ═══════════════════════════════════════════════════════════════════════
    
    # Edelmetalle (4)
    'GOLD': AssetClass.COMMODITY_METAL,
    'SILVER': AssetClass.COMMODITY_METAL,
    'PLATINUM': AssetClass.COMMODITY_METAL,
    'PALLADIUM': AssetClass.COMMODITY_METAL,
    
    # Industriemetalle (2) - V3.0.0: Zink hinzugefügt
    'COPPER': AssetClass.COMMODITY_METAL,
    'ZINC': AssetClass.COMMODITY_METAL,  # V3.0.0: NEU - LME-Handelszeiten
    
    # Energie (3)
    'WTI_CRUDE': AssetClass.COMMODITY_ENERGY,
    'BRENT_CRUDE': AssetClass.COMMODITY_ENERGY,
    'NATURAL_GAS': AssetClass.COMMODITY_ENERGY,
    
    # Agrar (6)
    'WHEAT': AssetClass.COMMODITY_AGRIC,
    'CORN': AssetClass.COMMODITY_AGRIC,
    'SOYBEAN': AssetClass.COMMODITY_AGRIC,
    'SOYBEANS': AssetClass.COMMODITY_AGRIC,
    'COFFEE': AssetClass.COMMODITY_AGRIC,
    'COCOA': AssetClass.COMMODITY_AGRIC,
    'SUGAR': AssetClass.COMMODITY_AGRIC,
    'COTTON': AssetClass.COMMODITY_AGRIC,
    
    # Forex (2) - V3.0.0: USD/JPY hinzugefügt
    'EURUSD': AssetClass.FOREX_MAJOR,
    'EUR/USD': AssetClass.FOREX_MAJOR,
    'GBPUSD': AssetClass.FOREX_MAJOR,
    'USDJPY': AssetClass.FOREX_MINOR,  # V3.0.0: Safe-Haven Korrelation zu Gold
    'USD/JPY': AssetClass.FOREX_MINOR,
    
    # Crypto (2) - V3.0.0: Ethereum hinzugefügt
    'BITCOIN': AssetClass.CRYPTO,
    'BTC': AssetClass.CRYPTO,
    'BTCUSD': AssetClass.CRYPTO,
    'ETHEREUM': AssetClass.CRYPTO,  # V3.0.0: NEU - Hohe Volatilität
    'ETH': AssetClass.CRYPTO,
    'ETHUSD': AssetClass.CRYPTO,
    
    # Indizes (1) - V3.0.0: Nasdaq 100 hinzugefügt
    'SP500': AssetClass.INDEX,
    'NASDAQ': AssetClass.INDEX,
    'NASDAQ100': AssetClass.INDEX,  # V3.0.0: NEU - US-Session, Trend-Fokus
    'DAX': AssetClass.INDEX,
}


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
# V2.5.0: ASSET-CLASS SPECIFIC ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class AssetClassAnalyzer:
    """
    V2.5.0: Asset-Klassen-spezifische Analyse für höhere Precision.
    
    - Commodities: Volume-Spike + ATR Gewichtung, Trend-Following Bias
    - Forex (EUR/USD): DXY Korrelation berücksichtigen
    - Bitcoin: Bollinger Band Width für Squeeze-Detection
    """
    
    # Gewichtungs-Profile pro Asset-Klasse
    WEIGHT_PROFILES = {
        AssetClass.COMMODITY_METAL: {
            'volume_weight': 1.5,    # Volume wichtiger
            'atr_weight': 1.3,       # ATR wichtiger
            'trend_bias': 1.2,       # Trend-Following bevorzugt
            'mean_reversion_penalty': 0.8,
            'preferred_strategies': ['swing', 'day_trading', 'momentum']
        },
        AssetClass.COMMODITY_ENERGY: {
            'volume_weight': 1.4,
            'atr_weight': 1.5,       # Sehr volatil
            'trend_bias': 1.3,
            'mean_reversion_penalty': 0.7,
            'preferred_strategies': ['momentum', 'breakout', 'day_trading']
        },
        AssetClass.COMMODITY_AGRIC: {
            'volume_weight': 1.2,
            'atr_weight': 1.0,
            'trend_bias': 1.1,
            'mean_reversion_penalty': 0.9,
            'preferred_strategies': ['swing', 'mean_reversion']
        },
        AssetClass.FOREX_MAJOR: {
            'volume_weight': 0.8,    # Volume weniger wichtig bei Forex
            'atr_weight': 1.0,
            'trend_bias': 1.0,
            'mean_reversion_penalty': 1.0,
            'dxy_correlation': True,  # DXY prüfen!
            'preferred_strategies': ['scalping', 'day_trading', 'swing']
        },
        AssetClass.CRYPTO: {
            'volume_weight': 1.3,
            'atr_weight': 1.2,
            'trend_bias': 1.0,
            'mean_reversion_penalty': 1.0,
            'squeeze_filter': True,   # BB Squeeze prüfen!
            'preferred_strategies': ['momentum', 'breakout', 'scalping']
        },
        AssetClass.INDEX: {
            'volume_weight': 1.0,
            'atr_weight': 1.0,
            'trend_bias': 1.1,
            'mean_reversion_penalty': 0.9,
            'preferred_strategies': ['day_trading', 'swing']
        }
    }
    
    @classmethod
    def get_asset_class(cls, commodity: str) -> AssetClass:
        """Bestimmt die Asset-Klasse"""
        return ASSET_CLASS_MAP.get(commodity.upper(), AssetClass.COMMODITY_METAL)
    
    @classmethod
    def get_weight_profile(cls, commodity: str) -> Dict:
        """Holt das Gewichtungs-Profil für ein Asset"""
        asset_class = cls.get_asset_class(commodity)
        return cls.WEIGHT_PROFILES.get(asset_class, cls.WEIGHT_PROFILES[AssetClass.COMMODITY_METAL])
    
    @classmethod
    def calculate_volume_spike(cls, volumes: List[float], lookback: int = 20) -> Tuple[bool, float]:
        """
        Erkennt Volume-Spikes (wichtig für Commodities).
        
        Returns: (is_spike, spike_ratio)
        """
        if not volumes or len(volumes) < lookback:
            return False, 1.0
        
        avg_volume = np.mean(volumes[-lookback:-1])  # Ohne aktuellen Wert
        current_volume = volumes[-1]
        
        if avg_volume <= 0:
            return False, 1.0
        
        ratio = current_volume / avg_volume
        
        # Spike wenn > 1.5x Durchschnitt
        is_spike = ratio > 1.5
        
        return is_spike, ratio
    
    @classmethod
    def calculate_atr(cls, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Berechnet ATR (Average True Range)"""
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return 0
        
        tr_list = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_list.append(tr)
        
        # ATR = SMA von True Range
        if len(tr_list) >= period:
            return np.mean(tr_list[-period:])
        return np.mean(tr_list) if tr_list else 0
    
    @classmethod
    def calculate_relative_strength(
        cls, 
        asset_prices: List[float], 
        benchmark_prices: List[float],
        period: int = 14
    ) -> Tuple[str, float]:
        """
        V2.5.0: Berechnet Relative Strength vs Benchmark.
        
        Beispiel: Gold vs Silver, BTC vs Total Market
        
        Returns: (direction, rs_value)
        """
        if len(asset_prices) < period or len(benchmark_prices) < period:
            return 'NEUTRAL', 1.0
        
        # Performance berechnen
        asset_return = (asset_prices[-1] - asset_prices[-period]) / asset_prices[-period]
        benchmark_return = (benchmark_prices[-1] - benchmark_prices[-period]) / benchmark_prices[-period]
        
        # Relative Strength
        if benchmark_return != 0:
            rs = (1 + asset_return) / (1 + benchmark_return)
        else:
            rs = 1 + asset_return
        
        # Interpretation
        if rs > 1.05:
            return 'OUTPERFORMING', rs
        elif rs < 0.95:
            return 'UNDERPERFORMING', rs
        else:
            return 'NEUTRAL', rs
    
    @classmethod
    def get_dynamic_sl_tp(
        cls,
        commodity: str,
        atr: float,
        direction: str,
        entry_price: float,
        trading_mode: str = 'standard',
        spread: float = 0.0,
        bid: float = None,
        ask: float = None
    ) -> Tuple[float, float]:
        """
        V3.1.0: Berechnet dynamische SL/TP basierend auf ATR, Trading-Modus UND Spread.
        
        NEU: Spread-intelligente SL/TP-Anpassung
        - Der Spread wird bei der SL/TP-Berechnung berücksichtigt
        - SL wird um den Spread erweitert, um sofortige Verluste zu vermeiden
        - TP wird angepasst, um das Risiko-/Ertragsverhältnis zu erhalten
        
        Trading-Modi:
        - aggressive: 1.0 × ATR SL, 2.0 × ATR TP (enger, schneller)
        - standard: 1.5 × ATR SL, 3.0 × ATR TP (ausgewogen)
        - conservative: 2.5 × ATR SL, 4.0 × ATR TP (weiter, sicherer)
        
        Args:
            commodity: Asset-Name
            atr: Average True Range
            direction: 'BUY' oder 'SELL'
            entry_price: Einstiegspreis
            trading_mode: 'aggressive', 'standard', 'conservative'
            spread: Aktueller Spread (ask - bid)
            bid: Aktueller Bid-Preis
            ask: Aktueller Ask-Preis
        
        Returns: (stop_loss_price, take_profit_price)
        """
        # Minimum SL/TP-Distanz basierend auf Asset-Klasse
        asset_class = cls.get_asset_class(commodity)
        
        # Mindest-SL in Prozent basierend auf Asset-Klasse
        min_sl_percent = {
            AssetClass.CRYPTO: 3.0,      # Crypto: 3% min
            AssetClass.COMMODITY_ENERGY: 2.0,      # Energie: 2% min
            AssetClass.FOREX_MAJOR: 0.5,  # Forex: 0.5% min
            AssetClass.FOREX_MINOR: 0.5,  # Forex Minor: 0.5% min
            AssetClass.COMMODITY_METAL: 1.5,  # Edelmetalle: 1.5% min
            AssetClass.COMMODITY_AGRIC: 2.0,  # Agrar: 2% min
            AssetClass.INDEX: 1.5,       # Indizes: 1.5% min
        }.get(asset_class, 2.0)
        
        # SL/TP-Multiplikatoren basierend auf Trading-Modus
        if trading_mode == 'aggressive':
            sl_multiplier = 1.0
            tp_multiplier = 2.0
            # Aggressive: Kann enger sein
            min_sl_percent *= 0.75
        elif trading_mode == 'conservative':
            sl_multiplier = 2.5
            tp_multiplier = 4.0
            # Conservative: Muss weiter sein
            min_sl_percent *= 1.5
        else:  # standard
            sl_multiplier = 1.5
            tp_multiplier = 3.0
        
        # Berechne ATR-basierte Distanz
        if atr > 0:
            sl_distance = atr * sl_multiplier
            tp_distance = atr * tp_multiplier
        else:
            # Fallback auf Prozent-basiert
            sl_distance = entry_price * (min_sl_percent / 100)
            tp_distance = entry_price * (min_sl_percent * 2 / 100)
        
        # Stelle sicher, dass SL mindestens min_sl_percent ist
        min_sl_distance = entry_price * (min_sl_percent / 100)
        if sl_distance < min_sl_distance:
            sl_distance = min_sl_distance
            tp_distance = min_sl_distance * 2  # Halte 2:1 R/R
        
        # ═══════════════════════════════════════════════════════════════════
        # V3.1.0: SPREAD-INTELLIGENTE ANPASSUNG
        # ═══════════════════════════════════════════════════════════════════
        
        # Berechne Spread wenn bid/ask verfügbar
        if spread <= 0 and bid and ask and ask > bid:
            spread = ask - bid
        
        # Spread-Prozent berechnen
        spread_percent = (spread / entry_price * 100) if entry_price > 0 and spread > 0 else 0
        
        # Spread-Puffer: SL wird um mindestens 1.5x Spread erweitert
        spread_buffer = spread * 1.5 if spread > 0 else 0
        
        # Zusätzlicher Puffer basierend auf Trading-Modus
        spread_mode_multiplier = {
            'aggressive': 1.2,   # Minimum 1.2x Spread-Buffer
            'standard': 1.5,    # Standard 1.5x Spread-Buffer
            'conservative': 2.0 # Konservativ 2x Spread-Buffer
        }.get(trading_mode, 1.5)
        
        adjusted_spread_buffer = spread * spread_mode_multiplier
        
        # SL-Distanz um Spread-Buffer erweitern
        if adjusted_spread_buffer > 0:
            original_sl_distance = sl_distance
            sl_distance = sl_distance + adjusted_spread_buffer
            
            # TP proportional anpassen, um R/R zu erhalten
            rr_ratio = tp_distance / original_sl_distance if original_sl_distance > 0 else 2.0
            tp_distance = sl_distance * rr_ratio
            
            logger.info(f"📊 SPREAD-ANPASSUNG: Spread={spread:.4f} ({spread_percent:.3f}%)")
            logger.info(f"   SL-Buffer: +{adjusted_spread_buffer:.4f} ({spread_mode_multiplier}x Spread)")
            logger.info(f"   SL: {original_sl_distance:.4f} → {sl_distance:.4f}")
        
        # ═══════════════════════════════════════════════════════════════════
        
        # Berechne finale Preise
        if direction == 'BUY':
            stop_loss = round(entry_price - sl_distance, 5)
            take_profit = round(entry_price + tp_distance, 5)
        else:  # SELL
            stop_loss = round(entry_price + sl_distance, 5)
            take_profit = round(entry_price - tp_distance, 5)
        
        logger.info(f"📊 KI SL/TP für {commodity} ({trading_mode}): Entry={entry_price:.2f}, SL={stop_loss:.2f} ({sl_distance/entry_price*100:.2f}%), TP={take_profit:.2f} ({tp_distance/entry_price*100:.2f}%)")
        if spread > 0:
            logger.info(f"   🔄 Spread-berücksichtigt: {spread:.4f} ({spread_percent:.3f}%)")
        
        return stop_loss, take_profit
    
    @classmethod
    def calculate_spread_adjusted_entry(
        cls,
        commodity: str,
        direction: str,
        bid: float,
        ask: float,
        trading_mode: str = 'standard'
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        V3.1.0: Berechnet Spread-Details und empfiehlt Entry-Price.
        
        Returns:
            Tuple[entry_price, spread, spread_info_dict]
        """
        spread = ask - bid if ask > bid else 0
        spread_percent = (spread / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0
        
        # Entry-Price basierend auf Richtung
        if direction == 'BUY':
            entry_price = ask  # Kaufen zum Ask
        else:
            entry_price = bid  # Verkaufen zum Bid
        
        # Spread-Bewertung
        asset_class = cls.get_asset_class(commodity)
        
        # Max akzeptabler Spread pro Asset-Klasse (in %)
        max_spread_thresholds = {
            AssetClass.CRYPTO: 0.5,           # Crypto: max 0.5%
            AssetClass.COMMODITY_ENERGY: 0.3, # Energie: max 0.3%
            AssetClass.FOREX_MAJOR: 0.02,     # Forex Major: max 0.02%
            AssetClass.FOREX_MINOR: 0.05,     # Forex Minor: max 0.05%
            AssetClass.COMMODITY_METAL: 0.2,  # Metalle: max 0.2%
            AssetClass.COMMODITY_AGRIC: 0.5,  # Agrar: max 0.5% (oft höher)
            AssetClass.INDEX: 0.15,           # Indizes: max 0.15%
        }
        
        max_spread = max_spread_thresholds.get(asset_class, 0.3)
        
        # Spread-Status
        if spread_percent <= max_spread * 0.5:
            spread_status = 'EXCELLENT'
            spread_warning = None
        elif spread_percent <= max_spread:
            spread_status = 'ACCEPTABLE'
            spread_warning = None
        elif spread_percent <= max_spread * 1.5:
            spread_status = 'HIGH'
            spread_warning = f"Spread ({spread_percent:.3f}%) über Normal für {commodity}"
        else:
            spread_status = 'EXTREME'
            spread_warning = f"⚠️ EXTREMER Spread ({spread_percent:.3f}%) für {commodity}!"
        
        spread_info = {
            'spread': spread,
            'spread_percent': spread_percent,
            'status': spread_status,
            'max_threshold': max_spread,
            'warning': spread_warning,
            'bid': bid,
            'ask': ask,
            'direction': direction,
            'entry_price': entry_price
        }
        
        if spread_warning:
            logger.warning(spread_warning)
        else:
            logger.info(f"📊 Spread für {commodity}: {spread:.4f} ({spread_percent:.3f}%) - {spread_status}")
        
        return entry_price, spread, spread_info
    
    @classmethod
    def apply_asset_weights(
        cls,
        commodity: str,
        base_confidence: float,
        volume_spike: bool,
        atr_ratio: float,
        strategy: str
    ) -> Tuple[float, List[str]]:
        """
        V2.5.0: Wendet Asset-spezifische Gewichtungen auf Confidence an.
        
        Returns: (adjusted_confidence, reasons)
        """
        profile = cls.get_weight_profile(commodity)
        reasons = []
        adjustment = 0
        
        # Volume Spike Bonus
        if volume_spike:
            bonus = 0.05 * profile['volume_weight']
            adjustment += bonus
            reasons.append(f"+{bonus*100:.0f}% Volume-Spike")
        
        # ATR Adjustment
        if atr_ratio > 1.5:  # Hohe Volatilität
            penalty = -0.05 * profile['atr_weight']
            adjustment += penalty
            reasons.append(f"{penalty*100:.0f}% Hohe ATR-Vola")
        elif atr_ratio < 0.5:  # Niedrige Volatilität
            penalty = -0.03
            adjustment += penalty
            reasons.append(f"{penalty*100:.0f}% Niedrige ATR")
        
        # Strategie-Präferenz
        if strategy in profile.get('preferred_strategies', []):
            bonus = 0.05
            adjustment += bonus
            reasons.append(f"+{bonus*100:.0f}% Bevorzugte Strategie")
        
        # Mean Reversion Penalty für Commodities
        if strategy == 'mean_reversion':
            penalty_factor = profile.get('mean_reversion_penalty', 1.0)
            if penalty_factor < 1.0:
                penalty = -0.05 * (1 - penalty_factor)
                adjustment += penalty
                reasons.append(f"{penalty*100:.0f}% Mean-Rev Penalty")
        
        final_confidence = base_confidence + adjustment
        return max(0, min(100, final_confidence)), reasons


# ═══════════════════════════════════════════════════════════════════════════
# V2.5.0: MULTI-TIMEFRAME CONFLUENCE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class MTFConfluenceAnalyzer:
    """
    V2.5.0: Multi-Timeframe Confluence für Deep Confidence.
    
    Prüft ob M5/M15 Signale mit H1/H4 Trend-Bias übereinstimmen.
    """
    
    @classmethod
    def calculate_trend(cls, prices: List[float], period: int = 20) -> str:
        """Berechnet Trend-Richtung"""
        if len(prices) < period:
            return 'NEUTRAL'
        
        sma = np.mean(prices[-period:])
        current = prices[-1]
        
        # EMA für bessere Reaktion
        ema = cls._ema(prices, period)
        
        if current > sma * 1.005 and current > ema:
            return 'UP'
        elif current < sma * 0.995 and current < ema:
            return 'DOWN'
        return 'NEUTRAL'
    
    @classmethod
    def _ema(cls, prices: List[float], period: int) -> float:
        """Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @classmethod
    def check_mtf_confluence(
        cls,
        m5_prices: List[float],
        h1_prices: List[float],
        h4_prices: List[float],
        signal: str
    ) -> Tuple[bool, float, str]:
        """
        V2.5.0: Prüft Multi-Timeframe Confluence.
        
        Returns: (is_confluent, confidence_boost, reason)
        """
        m5_trend = cls.calculate_trend(m5_prices, 20)
        h1_trend = cls.calculate_trend(h1_prices, 20)
        h4_trend = cls.calculate_trend(h4_prices, 20)
        
        signal_direction = 'UP' if signal == 'BUY' else 'DOWN'
        
        confluence_count = 0
        
        if m5_trend == signal_direction:
            confluence_count += 1
        if h1_trend == signal_direction:
            confluence_count += 1.5  # H1 wichtiger
        if h4_trend == signal_direction:
            confluence_count += 2    # H4 am wichtigsten
        
        max_confluence = 4.5
        confluence_ratio = confluence_count / max_confluence
        
        # Mindestens H4 oder H1 muss übereinstimmen
        if h4_trend == signal_direction or h1_trend == signal_direction:
            is_confluent = confluence_ratio >= 0.5
        else:
            is_confluent = False
        
        # Confidence Boost
        if confluence_count >= 4:
            boost = 0.15
            reason = f"✅ Perfekte MTF Confluence (M5+H1+H4 = {signal_direction})"
        elif confluence_count >= 3:
            boost = 0.10
            reason = f"✅ Starke MTF Confluence ({confluence_count:.1f}/4.5)"
        elif confluence_count >= 2:
            boost = 0.05
            reason = f"✅ Moderate MTF Confluence ({confluence_count:.1f}/4.5)"
        else:
            boost = -0.10
            reason = f"⚠️ Schwache MTF Confluence ({confluence_count:.1f}/4.5)"
        
        return is_confluent, boost, reason


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
    ema200_distance_percent: float = 0.0  # V2.6.1: Abstand vom EMA200 in %


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
    
    V2.3.38: OPTIMIERT für aktiveres Trading bei gleichbleibender Qualität
    """
    
    # V2.3.40: TRADING-MODUS KONFIGURATION
    # Zwei Modi: "aggressive" (mehr Trades) und "conservative" (weniger, bessere Trades)
    
    # AGGRESSIVER MODUS - Niedrigere Thresholds für mehr Aktivität
    AGGRESSIVE_THRESHOLDS = {
        "strong_uptrend": 58.0,
        "uptrend": 60.0,
        "downtrend": 60.0,
        "strong_downtrend": 58.0,
        "range": 62.0,
        "high_volatility": 68.0,
        "chaos": 75.0
    }
    AGGRESSIVE_MIN_THRESHOLD = 65.0
    
    # KONSERVATIVER MODUS - Höhere Thresholds für Qualität
    CONSERVATIVE_THRESHOLDS = {
        "strong_uptrend": 68.0,
        "uptrend": 70.0,
        "downtrend": 70.0,
        "strong_downtrend": 68.0,
        "range": 72.0,
        "high_volatility": 78.0,
        "chaos": 85.0
    }
    CONSERVATIVE_MIN_THRESHOLD = 72.0
    
    # V2.3.38: DYNAMISCHE KONFIGURATION (wird zur Laufzeit gesetzt)
    MIN_CONFIDENCE_THRESHOLD = 72.0  # Default: Konservativ
    CONFIDENCE_THRESHOLDS = CONSERVATIVE_THRESHOLDS.copy()  # Default: Konservativ
    
    # Aktueller Modus
    _current_mode = "conservative"
    
    BREAKEVEN_TRIGGER_PERCENT = 50.0  # Bei 50% TP-Erreichung → SL auf Einstand
    TIME_EXIT_MINUTES = 240  # 4 Stunden
    
    # ═══════════════════════════════════════════════════════════════════════
    # V2.6.0: STRATEGIE-SPEZIFISCHE SÄULEN-GEWICHTUNGEN
    # Jede Strategie hat einen anderen Fokus auf die 4 Säulen
    # ═══════════════════════════════════════════════════════════════════════
    
    STRATEGY_PROFILES = {
        # ─────────────────────────────────────────────────────────────────
        # 1. SWING TRADING - Trend-Fokus (Tage bis Wochen)
        # Basis: Golden Cross (EMA 50/200) oder MACD Signal-Line Cross auf D1
        # ─────────────────────────────────────────────────────────────────
        'swing': {
            'name': 'Swing Trading',
            'weights': {
                'base_signal': 30,      # EMA 50/200 Cross, MACD
                'trend_confluence': 40,  # W1/D1 Konfluenz (FOKUS!)
                'volatility': 10,        # ATR(14) auf D1 stabil
                'sentiment': 20          # Fundamentaldaten, COT
            },
            'threshold': 75,
            'timeframes': ['D1', 'H4'],
            'indicators': ['EMA_50', 'EMA_200', 'MACD', 'ATR'],
            'description': 'Große Bewegungen über Tage/Wochen mitnehmen'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 2. DAY TRADING - Struktur-Fokus (Intraday)
        # Basis: EMA-Fächer (20/50/100) auf H1 + RSI-Bestätigung
        # ─────────────────────────────────────────────────────────────────
        'day': {
            'name': 'Day Trading',
            'weights': {
                'base_signal': 35,       # EMA-Fächer + RSI (FOKUS!)
                'trend_confluence': 25,  # H4/H1 Alignment
                'volatility': 20,        # Session-Volumen (NY Open)
                'sentiment': 20          # Tagesaktuelle News
            },
            'threshold': 70,
            'timeframes': ['H1', 'M15'],
            'indicators': ['EMA_20', 'EMA_50', 'EMA_100', 'RSI'],
            'description': 'Profit innerhalb eines Handelstages'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 3. SCALPING - Reaktions-Fokus (Minuten)
        # Basis: VWAP-Abweichung + Stochastik-Cross auf M1/M5
        # ─────────────────────────────────────────────────────────────────
        'scalping': {
            'name': 'Scalping',
            'weights': {
                'base_signal': 40,       # VWAP + Stochastik (FOKUS!)
                'trend_confluence': 10,  # Nur M5 Trend
                'volatility': 40,        # Tick-Volumen-Spikes (KRITISCH!)
                'sentiment': 10          # Orderbuch-Ungleichgewicht
            },
            'threshold': 60,
            'timeframes': ['M5', 'M1'],
            'indicators': ['VWAP', 'STOCHASTIC', 'TICK_VOLUME'],
            'description': 'Viele kleine Gewinne in Minuten'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 4. MOMENTUM - Kraft-Fokus (Einspringen in starke Bewegung)
        # Basis: Preis bricht über letztes Hoch/Tief
        # ─────────────────────────────────────────────────────────────────
        'momentum': {
            'name': 'Momentum Trading',
            'weights': {
                'base_signal': 20,       # Hoch/Tief Breakout
                'trend_confluence': 30,  # ADX > 25 (FOKUS!)
                'volatility': 40,        # ATR/Volumen-Expansion (FOKUS!)
                'sentiment': 10          # Social Media Buzz, News-Hype
            },
            'threshold': 65,
            'timeframes': ['H4', 'H1'],
            'indicators': ['ADX', 'ATR', 'VOLUME', 'HIGH_LOW'],
            'description': 'In starke, beschleunigende Bewegung einspringen'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 5. MEAN REVERSION - Rückkehr-Fokus (Überkauft/Überverkauft)
        # Basis: Preis außerhalb 2. Standardabweichung Bollinger
        # ─────────────────────────────────────────────────────────────────
        'mean_reversion': {
            'name': 'Mean Reversion',
            'weights': {
                'base_signal': 50,       # Bollinger Band Touch (FOKUS!)
                'trend_confluence': 10,  # Besser wenn Trend NEUTRAL
                'volatility': 30,        # Vola muss peaken und nachlassen
                'sentiment': 10          # Fear & Greed Index
            },
            'threshold': 60,
            'timeframes': ['H1', 'M30'],
            'indicators': ['BOLLINGER', 'RSI', 'ATR'],
            'description': 'Überkaufte/Überverkaufte Märkte handeln'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 6. BREAKOUT - Ausbruch-Fokus (Range-Zerstörung)
        # Basis: Mehrfacher Test eines Levels (mind. 3 Kontakte)
        # ─────────────────────────────────────────────────────────────────
        'breakout': {
            'name': 'Breakout Trading',
            'weights': {
                'base_signal': 30,       # Level-Tests (3+ Kontakte)
                'trend_confluence': 15,  # Übergeordneter Trend
                'volatility': 45,        # Bollinger Squeeze (FOKUS!)
                'sentiment': 10          # News-Events als Katalysator
            },
            'threshold': 72,
            'timeframes': ['M30', 'M15'],
            'indicators': ['BOLLINGER_WIDTH', 'SUPPORT_RESISTANCE', 'VOLUME'],
            'description': 'Handel bei Zerstörung einer Range'
        },
        
        # ─────────────────────────────────────────────────────────────────
        # 7. GRID TRADING - Mathematik-Fokus (Seitwärtsmarkt)
        # Basis: Start an psychologischen Marken (Runde Zahlen)
        # ─────────────────────────────────────────────────────────────────
        'grid': {
            'name': 'Grid Trading',
            'weights': {
                'base_signal': 10,       # Psychologische Marken
                'trend_confluence': 50,  # NEGATIVER Score bei Trend! (FOKUS!)
                'volatility': 30,        # Ping-Pong Volatilität
                'sentiment': 10          # Ruhige Nachrichtenlage
            },
            'threshold': 0,  # Läuft automatisch wenn Trend < 20
            'timeframes': ['H1', 'M30'],
            'indicators': ['ATR', 'ADX'],
            'requires_range_market': True,  # Nur bei Seitwärtsmarkt
            'description': 'Profitieren von Schwankungen ohne feste Richtung'
        }
    }
    
    # Alias-Mapping für verschiedene Schreibweisen
    STRATEGY_ALIASES = {
        'swing_trading': 'swing',
        'day_trading': 'day',
        'scalp': 'scalping',
        'mean_rev': 'mean_reversion',
        'meanreversion': 'mean_reversion',
        'break': 'breakout',
        'grid_trading': 'grid'
    }
    
    # ═══════════════════════════════════════════════════════════════════════
    # V2.6.0: 3-STUFEN TRADING-MODUS (Konservativ, Neutral, Aggressiv)
    # ═══════════════════════════════════════════════════════════════════════
    
    # KONSERVATIV - Höchste Qualität, weniger Trades
    CONSERVATIVE_THRESHOLDS = {
        "strong_uptrend": 70.0,
        "uptrend": 72.0,
        "downtrend": 72.0,
        "strong_downtrend": 70.0,
        "range": 75.0,
        "high_volatility": 80.0,
        "chaos": 88.0
    }
    CONSERVATIVE_MIN_THRESHOLD = 75.0
    
    # NEUTRAL - Ausgewogen (NEU!)
    NEUTRAL_THRESHOLDS = {
        "strong_uptrend": 62.0,
        "uptrend": 65.0,
        "downtrend": 65.0,
        "strong_downtrend": 62.0,
        "range": 68.0,
        "high_volatility": 72.0,
        "chaos": 80.0
    }
    NEUTRAL_MIN_THRESHOLD = 68.0
    
    # AGGRESSIV - Mehr Trades, höheres Risiko
    AGGRESSIVE_THRESHOLDS = {
        "strong_uptrend": 55.0,
        "uptrend": 58.0,
        "downtrend": 58.0,
        "strong_downtrend": 55.0,
        "range": 60.0,
        "high_volatility": 65.0,
        "chaos": 72.0
    }
    AGGRESSIVE_MIN_THRESHOLD = 60.0
    
    # V2.6.0: Dynamische Konfiguration (wird zur Laufzeit gesetzt)
    MIN_CONFIDENCE_THRESHOLD = 68.0  # Default: Neutral
    CONFIDENCE_THRESHOLDS = NEUTRAL_THRESHOLDS.copy()  # Default: Neutral
    _current_mode = "neutral"
    
    # ═══════════════════════════════════════════════════════════════════════
    # V2.6.0: ASSET-KLASSEN EMPFEHLUNGEN
    # Welche Strategie passt zu welchem Asset?
    # ═══════════════════════════════════════════════════════════════════════
    
    ASSET_STRATEGY_RECOMMENDATIONS = {
        AssetClass.COMMODITY_METAL: ['swing', 'breakout', 'momentum'],
        AssetClass.COMMODITY_ENERGY: ['breakout', 'momentum', 'swing'],
        AssetClass.COMMODITY_AGRIC: ['swing', 'mean_reversion'],
        AssetClass.FOREX_MAJOR: ['mean_reversion', 'day', 'scalping'],
        AssetClass.FOREX_MINOR: ['scalping', 'day', 'mean_reversion'],  # V3.0.0: USD/JPY
        AssetClass.CRYPTO: ['momentum', 'scalping', 'breakout'],
        AssetClass.INDEX: ['day', 'swing', 'momentum']
    }
    
    # ═══════════════════════════════════════════════════════════════════════
    # V3.0.0: ASSET-SPEZIFISCHE 4-SÄULEN-GEWICHTUNGEN
    # Überschreibt die Strategie-Profile für spezifische Assets
    # ═══════════════════════════════════════════════════════════════════════
    
    ASSET_SPECIFIC_WEIGHTS = {
        # Nasdaq 100: Trend-Fokus (US-Session 15:30-22:00 MEZ)
        'NASDAQ100': {
            'weights': {
                'base_signal': 25,        # 25%
                'trend_confluence': 45,   # 45% (FOKUS auf Trend-Stabilität!)
                'volatility': 15,         # 15%
                'sentiment': 15           # 15%
            },
            'note': 'US-Session, Trend-Stabilität priorisiert'
        },
        
        # USD/JPY: Sentiment-Fokus (JPY als Safe-Haven)
        'USDJPY': {
            'weights': {
                'base_signal': 30,        # 30%
                'trend_confluence': 25,   # 25%
                'volatility': 15,         # 15%
                'sentiment': 30           # 30% (FOKUS! Safe-Haven Korrelation zu Gold)
            },
            'note': 'JPY Safe-Haven Korrelation zu Gold, Forex 24/5'
        },
        
        # Ethereum: Volatilität-Fokus (24/7, hohe Volatilität)
        'ETHEREUM': {
            'weights': {
                'base_signal': 30,        # 30%
                'trend_confluence': 20,   # 20%
                'volatility': 40,         # 40% (FOKUS auf hohe Volatilität!)
                'sentiment': 10           # 10%
            },
            'note': 'Hohe Volatilität, 24/7 Markt'
        },
        
        # Zink / Industriemetalle: Basis-Signal Fokus
        'ZINC': {
            'weights': {
                'base_signal': 45,        # 45% (FOKUS auf industrielle Basis-Signale!)
                'trend_confluence': 25,   # 25%
                'volatility': 20,         # 20%
                'sentiment': 10           # 10%
            },
            'note': 'LME-Handelszeiten, industrielle Basis-Signale'
        }
    }
    
    # ═══════════════════════════════════════════════════════════════════════
    # V3.0.0: ASSET-SPEZIFISCHE THRESHOLD OVERRIDES
    # Spezielle Schwellenwerte für bestimmte Assets pro Trading-Modus
    # ═══════════════════════════════════════════════════════════════════════
    
    ASSET_THRESHOLD_OVERRIDES = {
        # Format: 'ASSET': {'conservative': X, 'neutral': Y, 'aggressive': Z}
        'ZINC': {
            'conservative': 70.0,   # Standard: 75%
            'neutral': 62.0,        # Standard: 68%
            'aggressive': 55.0      # Standard: 60%
        },
        'NASDAQ100': {
            'conservative': 72.0,   # Standard: 75%
            'neutral': 65.0,        # Standard: 68%
            'aggressive': 55.0      # Standard: 60%
        }
    }
    
    # BTC Aggressiv-Light - Spezieller Threshold für Crypto
    CRYPTO_THRESHOLD_OVERRIDE = 62.0
    
    # Mindest-Confluence Regel
    MIN_CONFLUENCE_REQUIRED = 1
    
    def __init__(self):
        self.active_risk_circuits: Dict[str, RiskCircuitStatus] = {}
        self.strategy_performance: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'current_weight': 1.0
        })
        self._last_market_analysis: Dict[str, MarketAnalysis] = {}
    
    @classmethod
    def get_strategy_profile(cls, strategy: str) -> Dict:
        """Holt das Strategie-Profil mit Säulen-Gewichtungen"""
        # Normalisiere Strategie-Namen
        strategy_clean = strategy.lower().replace('_trading', '').replace('-', '_')
        strategy_key = cls.STRATEGY_ALIASES.get(strategy_clean, strategy_clean)
        
        if strategy_key in cls.STRATEGY_PROFILES:
            return cls.STRATEGY_PROFILES[strategy_key]
        
        # Fallback: Day Trading Profil
        logger.warning(f"Unbekannte Strategie '{strategy}' - verwende Day Trading Profil")
        return cls.STRATEGY_PROFILES['day']
    
    @classmethod
    def set_trading_mode(cls, mode: str):
        """
        V2.6.0: Setzt den Trading-Modus (conservative, neutral, aggressive)
        """
        mode_lower = mode.lower()
        
        if mode_lower == "aggressive":
            cls.CONFIDENCE_THRESHOLDS = cls.AGGRESSIVE_THRESHOLDS.copy()
            cls.MIN_CONFIDENCE_THRESHOLD = cls.AGGRESSIVE_MIN_THRESHOLD
            cls._current_mode = "aggressive"
            logger.info("🔥 Trading-Modus: AGGRESSIV (niedrigste Thresholds, maximale Aktivität)")
        elif mode_lower == "neutral":
            cls.CONFIDENCE_THRESHOLDS = cls.NEUTRAL_THRESHOLDS.copy()
            cls.MIN_CONFIDENCE_THRESHOLD = cls.NEUTRAL_MIN_THRESHOLD
            cls._current_mode = "neutral"
            logger.info("⚖️ Trading-Modus: NEUTRAL (ausgewogene Thresholds)")
        else:  # conservative
            cls.CONFIDENCE_THRESHOLDS = cls.CONSERVATIVE_THRESHOLDS.copy()
            cls.MIN_CONFIDENCE_THRESHOLD = cls.CONSERVATIVE_MIN_THRESHOLD
            cls._current_mode = "conservative"
            logger.info("🛡️ Trading-Modus: KONSERVATIV (höchste Qualität, weniger Trades)")
        
        logger.info(f"   Min Threshold: {cls.MIN_CONFIDENCE_THRESHOLD}%")
    
    @classmethod
    def get_current_mode(cls) -> str:
        """Gibt den aktuellen Trading-Modus zurück"""
        return cls._current_mode
    
    @classmethod
    def get_recommended_strategies(cls, commodity: str) -> List[str]:
        """Gibt empfohlene Strategien für ein Asset zurück"""
        asset_class = AssetClassAnalyzer.get_asset_class(commodity)
        return cls.ASSET_STRATEGY_RECOMMENDATIONS.get(asset_class, ['day', 'swing'])
    
    @classmethod
    def get_asset_specific_weights(cls, commodity: str, strategy: str) -> Dict:
        """
        V3.0.0: Holt die asset-spezifischen Säulen-Gewichtungen.
        
        Wenn das Asset spezifische Gewichtungen hat, werden diese verwendet.
        Ansonsten wird das Strategie-Profil zurückgegeben.
        
        Returns:
            Dict mit 'weights', 'name', 'note'
        """
        commodity_upper = commodity.upper()
        
        # Prüfe ob es asset-spezifische Gewichtungen gibt
        if commodity_upper in cls.ASSET_SPECIFIC_WEIGHTS:
            asset_weights = cls.ASSET_SPECIFIC_WEIGHTS[commodity_upper]
            strategy_profile = cls.get_strategy_profile(strategy)
            
            # Kombiniere asset-spezifische Gewichte mit Strategie-Metadaten
            return {
                'weights': asset_weights['weights'],
                'name': f"{strategy_profile['name']} ({asset_weights.get('note', commodity_upper)})",
                'note': asset_weights.get('note', ''),
                'asset_override': True,
                'original_strategy': strategy
            }
        
        # Fallback: Standard Strategie-Profil
        return cls.get_strategy_profile(strategy)
    
    @classmethod
    def get_asset_threshold(cls, commodity: str) -> float:
        """
        V3.0.0: Holt den asset-spezifischen Threshold basierend auf aktuellem Modus.
        
        Berücksichtigt ASSET_THRESHOLD_OVERRIDES und CRYPTO_THRESHOLD_OVERRIDE.
        
        Returns:
            Der anwendbare Confidence-Threshold für das Asset
        """
        commodity_upper = commodity.upper()
        current_mode = cls._current_mode
        
        # 1. Prüfe spezifische Threshold-Overrides (Zink, Nasdaq)
        if commodity_upper in cls.ASSET_THRESHOLD_OVERRIDES:
            override = cls.ASSET_THRESHOLD_OVERRIDES[commodity_upper]
            threshold = override.get(current_mode, cls.MIN_CONFIDENCE_THRESHOLD)
            logger.debug(f"📊 Asset {commodity_upper}: Spezial-Threshold {threshold}% (Modus: {current_mode})")
            return threshold
        
        # 2. Prüfe Crypto Override (Bitcoin, Ethereum)
        asset_class = AssetClassAnalyzer.get_asset_class(commodity_upper)
        if asset_class == AssetClass.CRYPTO:
            # Crypto hat einen speziellen niedrigeren Threshold
            crypto_threshold = cls.CRYPTO_THRESHOLD_OVERRIDE
            if current_mode == "conservative":
                crypto_threshold = max(crypto_threshold, cls.MIN_CONFIDENCE_THRESHOLD - 5)
            elif current_mode == "aggressive":
                crypto_threshold = max(crypto_threshold - 5, 55.0)
            logger.debug(f"📊 Crypto {commodity_upper}: Threshold {crypto_threshold}% (Modus: {current_mode})")
            return crypto_threshold
        
        # 3. Standard Threshold für den aktuellen Modus
        return cls.MIN_CONFIDENCE_THRESHOLD
        
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
                timestamp=datetime.now(timezone.utc).isoformat(),
                ema200_distance_percent=0.0  # V2.6.1
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
        
        # V2.6.1: EMA 200 für Mean Reversion Korrektur
        ema_200 = self._calculate_ema(prices, min(200, len(prices) - 1)) if len(prices) > 50 else current_price
        ema200_distance_percent = ((current_price - ema_200) / ema_200 * 100) if ema_200 > 0 else 0.0
        
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
            timestamp=datetime.now(timezone.utc).isoformat(),
            ema200_distance_percent=ema200_distance_percent  # V2.6.1: Mean Reversion
        )
        
        logger.info(f"🌍 MARKT-ZUSTAND: {state.value}")
        logger.info(f"   ADX: {adx:.1f}, ATR: {atr:.4f} ({atr_normalized:.2f}x normal)")
        logger.info(f"   Trend: {trend_direction}, Volatilität: {volatility_level}")
        logger.info(f"   EMA200 Abstand: {ema200_distance_percent:+.2f}%")  # V2.6.1
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
        confluence_count: int = 0,
        commodity: str = "GOLD",
        cot_data: Dict = None
    ) -> UniversalConfidenceScore:
        """
        V2.6.0: STRATEGIE-SPEZIFISCHER Universal Confidence Score
        
        Jede Strategie hat ihre eigene Säulen-Gewichtung:
        - Swing: Trend-Fokus (40% Trend)
        - Day: Struktur-Fokus (35% Basis)
        - Scalping: Reaktions-Fokus (40% Vola)
        - Momentum: Kraft-Fokus (40% Vola)
        - Mean Reversion: Rückkehr-Fokus (50% Basis)
        - Breakout: Ausbruch-Fokus (45% Vola)
        - Grid: Mathematik-Fokus (50% Trend-Negativ)
        """
        penalties = []
        bonuses = []
        
        # V2.6.0: Strategie-Profil holen
        strategy_profile = self.get_strategy_profile(strategy)
        weights = strategy_profile['weights']
        # strategy_threshold und strategy_name für zukünftige Erweiterungen verfügbar
        _ = strategy_profile['threshold']  # Threshold wird über CONFIDENCE_THRESHOLDS gesteuert
        _ = strategy_profile['name']  # Name für Logging verfügbar
        
        # Asset-Klasse für zusätzliche Anpassungen
        asset_class = AssetClassAnalyzer.get_asset_class(commodity)
        
        # Grid Trading: Spezieller Check - braucht Seitwärtsmarkt!
        is_grid = strategy.lower() in ['grid', 'grid_trading']
        if is_grid and market_analysis:
            if market_analysis.state not in [MarketState.RANGE]:
                logger.info(f"⛔ {commodity}: Grid Trading braucht Seitwärtsmarkt, aktuell: {market_analysis.state.value}")
                return UniversalConfidenceScore(
                    base_signal_score=0, trend_confluence_score=0,
                    volatility_score=0, sentiment_score=0,
                    total_score=0, passed_threshold=False,
                    penalties=["Grid Trading braucht Seitwärtsmarkt (Range)"],
                    bonuses=[],
                    details={'strategy': strategy, 'rejection_reason': 'GRID_NEEDS_RANGE'}
                )
        
        # MINDEST-CONFLUENCE REGEL (außer für Grid)
        if not is_grid and confluence_count < self.MIN_CONFLUENCE_REQUIRED:
            logger.info(f"⛔ {commodity}: Confluence {confluence_count} < {self.MIN_CONFLUENCE_REQUIRED}")
            return UniversalConfidenceScore(
                base_signal_score=0, trend_confluence_score=0,
                volatility_score=0, sentiment_score=0,
                total_score=0, passed_threshold=False,
                penalties=[f"Mindest-Confluence nicht erreicht ({confluence_count} < {self.MIN_CONFLUENCE_REQUIRED})"],
                bonuses=[],
                details={'strategy': strategy, 'confluence_count': confluence_count,
                        'rejection_reason': 'MIN_CONFLUENCE_NOT_MET'}
            )
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 1: BASIS-SIGNAL (max Punkte = weights['base_signal'])
        # ═══════════════════════════════════════════════════════════════
        max_base = weights['base_signal']
        base_signal_score = int(max_base * 0.375)  # ~15 bei 40 max
        
        # Strategie passt zum Markt?
        strategy_suitable, suitability_msg = self.is_strategy_suitable_for_market(strategy, market_analysis)
        
        if "OPTIMAL" in suitability_msg:
            base_signal_score += int(max_base * 0.5)  # +20 bei 40 max
            bonuses.append(f"Strategie OPTIMAL für Markt (+{int(max_base * 0.5)})")
        elif "AKZEPTABEL" in suitability_msg:
            base_signal_score += int(max_base * 0.3)  # +12 bei 40 max
            bonuses.append(f"Strategie akzeptabel für Markt (+{int(max_base * 0.3)})")
        elif strategy_suitable:
            base_signal_score += int(max_base * 0.125)
            penalties.append("Strategie nicht optimal")
        else:
            base_signal_score -= int(max_base * 0.125)
            penalties.append("Strategie passt NICHT zum Markt")
        
        # Confluence-Bonus
        if confluence_count >= 5:
            base_signal_score += int(max_base * 0.625)  # +25 bei 40 max
            bonuses.append(f"Exzellente Confluence ({confluence_count} Indikatoren)")
        elif confluence_count >= 3:
            base_signal_score += int(max_base * 0.45)   # +18 bei 40 max
            bonuses.append(f"Gute Confluence ({confluence_count} Indikatoren)")
        elif confluence_count >= 2:
            base_signal_score += int(max_base * 0.3)    # +12 bei 40 max
            bonuses.append(f"Basis Confluence ({confluence_count} Indikatoren)")
        elif confluence_count >= 1:
            base_signal_score += int(max_base * 0.125)  # +5 bei 40 max
            bonuses.append("Einzelner Indikator bestätigt")
        
        base_signal_score = max(0, min(max_base, base_signal_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 2: TREND-KONFLUENZ (max Punkte = weights['trend_confluence'])
        # V2.5.2: Strengere Neutral-Behandlung im konservativen Modus
        # ═══════════════════════════════════════════════════════════════
        max_trend = weights['trend_confluence']
        trend_confluence_score = 0
        is_buy = signal == 'BUY'
        is_conservative = self._current_mode == "conservative"
        
        # Timeframe Alignment Check
        aligned_timeframes = 0
        
        # D1 Trend (wichtigster Timeframe)
        d1_aligned = (is_buy and trend_d1 in ['up', 'strong_up']) or (not is_buy and trend_d1 in ['down', 'strong_down'])
        if d1_aligned:
            aligned_timeframes += 1
            trend_confluence_score += int(max_trend * 0.4)  # +10 bei 25 max
            bonuses.append("D1 Trend aligned")
        elif trend_d1 == 'neutral':
            # V2.5.2: Im konservativen Modus = 0 Punkte für Neutral
            if is_conservative:
                penalties.append("D1 neutral (konservativ: 0 Punkte)")
            else:
                trend_confluence_score += int(max_trend * 0.12)  # +3 bei 25 max
        else:
            penalties.append(f"D1 gegen Signal ({trend_d1})")
        
        # H4 Trend
        h4_aligned = (is_buy and trend_h4 in ['up', 'strong_up']) or (not is_buy and trend_h4 in ['down', 'strong_down'])
        if h4_aligned:
            aligned_timeframes += 1
            trend_confluence_score += int(max_trend * 0.4)  # +10 bei 25 max
            bonuses.append("H4 Trend aligned")
        elif trend_h4 == 'neutral':
            if is_conservative:
                penalties.append("H4 neutral (konservativ: 0 Punkte)")
            else:
                trend_confluence_score += int(max_trend * 0.12)
        
        # H1 Trend
        h1_aligned = (is_buy and trend_h1 in ['up', 'strong_up']) or (not is_buy and trend_h1 in ['down', 'strong_down'])
        if h1_aligned:
            aligned_timeframes += 1
            trend_confluence_score += int(max_trend * 0.2)  # +5 bei 25 max
            bonuses.append("H1 Trend aligned")
        elif trend_h1 == 'neutral' and not is_conservative:
            trend_confluence_score += int(max_trend * 0.08)
        
        if aligned_timeframes == 3:
            bonuses.append("✅ PERFEKTE Trend-Konfluenz (alle TF aligned)")
        elif aligned_timeframes == 0 and is_conservative:
            penalties.append("⛔ Kein Timeframe aligned (konservativ: Trade nicht empfohlen)")
        
        # ═══════════════════════════════════════════════════════════════
        # V2.6.1: MEAN REVERSION KORREKTUR in Säule 2
        # Wenn Preis extrem weit vom EMA 200 entfernt → Überkauft/Überverkauft
        # Reduziert Confidence auch bei aligned Trend!
        # ═══════════════════════════════════════════════════════════════
        # Hole EMA200 Abstand aus market_analysis (primär) oder indicators (fallback)
        ema200_distance = market_analysis.ema200_distance_percent if market_analysis else indicators.get('ema200_distance_percent', 0)
        
        # Thresholds für Mean Reversion Warnung
        MEAN_REV_WARNING_THRESHOLD = 3.0   # Ab 3% Abstand: Warnung
        MEAN_REV_DANGER_THRESHOLD = 5.0    # Ab 5% Abstand: Starke Penalty
        MEAN_REV_EXTREME_THRESHOLD = 8.0   # Ab 8% Abstand: Sehr starke Penalty
        
        if abs(ema200_distance) > 0:
            # Prüfe ob Signal in Richtung der Überdehnung geht
            is_overextended_buy = ema200_distance > 0 and is_buy      # Preis weit ÜBER EMA, will kaufen
            is_overextended_sell = ema200_distance < 0 and not is_buy  # Preis weit UNTER EMA, will verkaufen
            
            if is_overextended_buy or is_overextended_sell:
                abs_distance = abs(ema200_distance)
                
                if abs_distance >= MEAN_REV_EXTREME_THRESHOLD:
                    # Extrem überdehnt: -50% der Trend-Punkte
                    mean_rev_penalty = int(trend_confluence_score * 0.5)
                    trend_confluence_score -= mean_rev_penalty
                    penalties.append(f"⚠️ EXTREM {'überkauft' if is_buy else 'überverkauft'} ({ema200_distance:+.1f}% vom EMA200) → -{mean_rev_penalty} Punkte")
                    logger.warning(f"🔴 Mean Reversion Warnung: {commodity} ist {abs_distance:.1f}% vom EMA200 entfernt!")
                    
                elif abs_distance >= MEAN_REV_DANGER_THRESHOLD:
                    # Stark überdehnt: -30% der Trend-Punkte
                    mean_rev_penalty = int(trend_confluence_score * 0.3)
                    trend_confluence_score -= mean_rev_penalty
                    penalties.append(f"⚠️ Stark {'überkauft' if is_buy else 'überverkauft'} ({ema200_distance:+.1f}% vom EMA200) → -{mean_rev_penalty} Punkte")
                    
                elif abs_distance >= MEAN_REV_WARNING_THRESHOLD:
                    # Leicht überdehnt: -15% der Trend-Punkte
                    mean_rev_penalty = int(trend_confluence_score * 0.15)
                    trend_confluence_score -= mean_rev_penalty
                    penalties.append(f"⚡ Leicht {'überkauft' if is_buy else 'überverkauft'} ({ema200_distance:+.1f}% vom EMA200) → -{mean_rev_penalty} Punkte")
            
            else:
                # Signal geht GEGEN die Überdehnung = Mean Reversion Trade = BONUS!
                abs_distance = abs(ema200_distance)
                if abs_distance >= MEAN_REV_DANGER_THRESHOLD:
                    mean_rev_bonus = int(max_trend * 0.2)  # +20% Bonus für Mean Reversion
                    trend_confluence_score += mean_rev_bonus
                    bonuses.append(f"✅ Mean Reversion Signal ({ema200_distance:+.1f}% vom EMA200) → +{mean_rev_bonus} Punkte")
        
        trend_confluence_score = max(0, min(max_trend, trend_confluence_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 3: VOLATILITÄTS-CHECK (max Punkte = weights['volatility'])
        # ═══════════════════════════════════════════════════════════════
        max_vol = weights['volatility']
        volatility_score = 0
        
        # ATR-Normalisierung
        atr_norm = market_analysis.atr_normalized
        
        # Ideale Volatilität: 0.8 - 1.5x normal
        if 0.8 <= atr_norm <= 1.5:
            volatility_score += int(max_vol * 0.75)  # +15 bei 20 max
            bonuses.append("Optimale Volatilität")
        elif 0.5 <= atr_norm <= 2.0:
            volatility_score += int(max_vol * 0.5)   # +10 bei 20 max
            bonuses.append("Akzeptable Volatilität")
        elif atr_norm > 2.5:
            volatility_score -= int(max_vol * 0.25)
            penalties.append(f"Extreme Volatilität ({atr_norm:.2f}x)")
        else:
            volatility_score += int(max_vol * 0.25)
        
        # Volume Check
        volume_surge = indicators.get('volume_surge', False)
        volume_peak = indicators.get('volume_peak', False)
        if volume_surge or volume_peak:
            volatility_score += int(max_vol * 0.25)
            bonuses.append("Volume bestätigt Signal")
        
        volatility_score = max(0, min(max_vol, volatility_score))
        
        # ═══════════════════════════════════════════════════════════════
        # SÄULE 4: SENTIMENT (max Punkte = weights['sentiment'])
        # V2.5.2: COT-Daten Integration für Commodities
        # ═══════════════════════════════════════════════════════════════
        max_sentiment = weights['sentiment']
        sentiment_score = 0
        
        # V2.5.2: COT-Daten für Commodities (wenn verfügbar)
        if cot_data and asset_class in [AssetClass.COMMODITY_METAL, AssetClass.COMMODITY_ENERGY, AssetClass.COMMODITY_AGRIC]:
            # COT Daten auswerten (commercial_net für zukünftige Erweiterungen)
            _ = cot_data.get('commercial_net', 0)  # Hedger Position (für Smart Money Analyse)
            noncommercial_net = cot_data.get('noncommercial_net', 0)  # Spekulanten
            cot_change = cot_data.get('weekly_change', 0)
            
            # Spekulanten-Sentiment (wichtiger für kurzfristige Bewegungen)
            if noncommercial_net > 0 and is_buy:
                sentiment_score += int(max_sentiment * 0.4)  # +6 bei 15 max
                bonuses.append(f"COT: Spekulanten bullish ({noncommercial_net:+.0f})")
            elif noncommercial_net < 0 and not is_buy:
                sentiment_score += int(max_sentiment * 0.4)
                bonuses.append(f"COT: Spekulanten bearish ({noncommercial_net:+.0f})")
            elif noncommercial_net != 0:
                penalties.append(f"COT: Spekulanten gegen Signal ({noncommercial_net:+.0f})")
            
            # Wöchentliche Änderung (Momentum)
            if cot_change > 5000 and is_buy:
                sentiment_score += int(max_sentiment * 0.2)
                bonuses.append("COT: Bullishes Momentum")
            elif cot_change < -5000 and not is_buy:
                sentiment_score += int(max_sentiment * 0.2)
                bonuses.append("COT: Bearishes Momentum")
        else:
            # Fallback: News Sentiment (für Forex/Crypto)
            if news_sentiment == 'bullish' and is_buy:
                sentiment_score += int(max_sentiment * 0.67)  # +10 bei 15 max
                bonuses.append("News unterstützt BUY")
            elif news_sentiment == 'bearish' and not is_buy:
                sentiment_score += int(max_sentiment * 0.67)
                bonuses.append("News unterstützt SELL")
            elif news_sentiment == 'neutral':
                sentiment_score += int(max_sentiment * 0.33)
            else:
                sentiment_score -= int(max_sentiment * 0.33)
                penalties.append(f"News gegen Signal ({news_sentiment})")
        
        # High-Impact News Penalty (für alle Assets)
        if high_impact_news_pending:
            sentiment_score -= max_sentiment  # Volle Penalty
            penalties.append("⚠️ High-Impact News anstehend")
        else:
            sentiment_score += int(max_sentiment * 0.33)
            bonuses.append("Keine kritischen News")
        
        sentiment_score = max(0, min(max_sentiment, sentiment_score))
        
        # ═══════════════════════════════════════════════════════════════
        # GESAMT-SCORE BERECHNEN
        # V2.5.2: Asset-spezifische Thresholds
        # ═══════════════════════════════════════════════════════════════
        total_score = base_signal_score + trend_confluence_score + volatility_score + sentiment_score
        total_score = max(0, min(100, total_score))
        
        # V2.5.2: Dynamischer Threshold mit BTC "Aggressiv-Light"
        market_state_str = market_analysis.state.value if market_analysis else "range"
        
        # BTC bekommt IMMER 65% Threshold (auch im konservativen Modus)
        if asset_class == AssetClass.CRYPTO:
            dynamic_threshold = self.CRYPTO_THRESHOLD_OVERRIDE
            bonuses.append(f"🪙 Crypto-Threshold: {dynamic_threshold}% (Aggressiv-Light)")
        else:
            dynamic_threshold = self.CONFIDENCE_THRESHOLDS.get(market_state_str, self.MIN_CONFIDENCE_THRESHOLD)
        
        passed_threshold = total_score >= dynamic_threshold
        
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
                'atr_normalized': atr_norm,
                'dynamic_threshold': dynamic_threshold,
                'asset_class': asset_class.value,
                'weights_used': weights,
                'cot_data_available': cot_data is not None
            }
        )
        
        logger.info(f"📊 UNIVERSAL CONFIDENCE SCORE [{commodity}]: {total_score:.1f}%")
        logger.info(f"   ├─ Asset-Klasse: {asset_class.value}")
        logger.info(f"   ├─ Basis-Signal: {base_signal_score}/{max_base}")
        logger.info(f"   ├─ Trend-Konfluenz: {trend_confluence_score}/{max_trend}")
        logger.info(f"   ├─ Volatilität: {volatility_score}/{max_vol}")
        logger.info(f"   └─ Sentiment: {sentiment_score}/{max_sentiment}")
        logger.info(f"   🎯 Threshold: {dynamic_threshold}% (Markt: {market_state_str})")
        logger.info(f"   {'✅ TRADE ERLAUBT' if passed_threshold else '❌ TRADE BLOCKIERT'} (Score: {total_score:.1f}% vs {dynamic_threshold}%)")
        
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
        
        # ═══════════════════════════════════════════════════════════════════
        # V2.3.39: STRATEGIE-SPEZIFISCHE TRAILING STOP KONFIGURATION
        # Jede Strategie hat eigene Trailing Stop Regeln
        # ═══════════════════════════════════════════════════════════════════
        
        TRAILING_STOP_CONFIG = {
            # Scalping: Schneller Trailing, sichert kleine Gewinne
            'scalping': {
                'active': True,
                'trigger_percent': 30,  # Aktiviert bei 30% TP erreicht
                'trail_percent': 60,    # Sichert 60% des Gewinns
            },
            # Day Trading: Moderater Trailing
            'day': {
                'active': True,
                'trigger_percent': 40,
                'trail_percent': 50,
            },
            'day_trading': {
                'active': True,
                'trigger_percent': 40,
                'trail_percent': 50,
            },
            # Swing: Lockerer Trailing, lässt Gewinne laufen
            'swing': {
                'active': True,
                'trigger_percent': 50,
                'trail_percent': 40,
            },
            'swing_trading': {
                'active': True,
                'trigger_percent': 50,
                'trail_percent': 40,
            },
            # Momentum: Aggressiver Trailing
            'momentum': {
                'active': True,
                'trigger_percent': 25,
                'trail_percent': 70,
            },
            # Breakout: Moderater Trailing nach Ausbruch
            'breakout': {
                'active': True,
                'trigger_percent': 35,
                'trail_percent': 55,
            },
            # Mean Reversion: Konservativer Trailing
            'mean_reversion': {
                'active': True,
                'trigger_percent': 45,
                'trail_percent': 45,
            },
            # Grid: Kein Trailing (Grid hat eigene Logik)
            'grid': {
                'active': False,
                'trigger_percent': 0,
                'trail_percent': 0,
            },
        }
        
        # Hole Konfiguration für diese Strategie
        strategy_clean = strategy.replace('_trading', '').lower()
        trail_config = TRAILING_STOP_CONFIG.get(strategy_clean, {
            'active': True, 'trigger_percent': 50, 'trail_percent': 50
        })
        
        status.trailing_stop_active = trail_config['active']
        status.trailing_stop_price = stop_loss
        
        # Speichere Trailing-Konfiguration im Status
        status.trailing_config = trail_config
        
        self.active_risk_circuits[trade_id] = status
        
        logger.info(f"🔒 Risk Circuit registriert: {trade_id}")
        logger.info(f"   Entry: {entry_price:.4f}, SL: {stop_loss:.4f}, TP: {take_profit:.4f}")
        logger.info(f"   Trailing Stop: {'Aktiv' if trail_config['active'] else 'Inaktiv'}")
        if trail_config['active']:
            logger.info(f"   → Trigger bei {trail_config['trigger_percent']}% TP, sichert {trail_config['trail_percent']}%")
        
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
        _ = status.stop_loss  # SL für Logging/Debugging verfügbar
        
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
        # CHECK 3: TRAILING STOP (Strategiespezifisch V2.3.39)
        # ═══════════════════════════════════════════════════════════════
        if status.trailing_stop_active and progress_percent > 0:
            # Hole Trailing-Konfiguration
            trail_config = getattr(status, 'trailing_config', {
                'trigger_percent': 50, 'trail_percent': 50
            })
            trigger_pct = trail_config.get('trigger_percent', 50)
            secure_pct = trail_config.get('trail_percent', 50) / 100.0
            
            # Trailing Stop aktiviert wenn Trigger erreicht
            if progress_percent >= trigger_pct:
                # Berechne neuen Trailing Stop
                if tp > entry:  # Long Trade
                    new_trailing = entry + (current_progress * secure_pct)
                    if new_trailing > status.trailing_stop_price:
                        old_trailing = status.trailing_stop_price
                        status.trailing_stop_price = new_trailing
                        
                        logger.info(f"📈 TRAILING STOP NACHGEZOGEN: {trade_id}")
                        logger.info(f"   Progress: {progress_percent:.1f}% (Trigger: {trigger_pct}%)")
                        logger.info(f"   SL: {old_trailing:.4f} → {new_trailing:.4f} (sichert {secure_pct*100:.0f}%)")
                        
                        return {
                            'action': 'trailing_stop',
                            'new_sl': new_trailing,
                            'reason': f'Trailing Stop nachgezogen auf {new_trailing:.4f} ({secure_pct*100:.0f}% gesichert)'
                        }
                else:  # Short Trade
                    new_trailing = entry - (current_progress * secure_pct)
                    if new_trailing < status.trailing_stop_price:
                        old_trailing = status.trailing_stop_price
                        status.trailing_stop_price = new_trailing
                        
                        logger.info(f"📉 TRAILING STOP NACHGEZOGEN: {trade_id}")
                        logger.info(f"   Progress: {progress_percent:.1f}% (Trigger: {trigger_pct}%)")
                        logger.info(f"   SL: {old_trailing:.4f} → {new_trailing:.4f} (sichert {secure_pct*100:.0f}%)")
                        
                        return {
                            'action': 'trailing_stop',
                            'new_sl': new_trailing,
                            'reason': f'Trailing Stop nachgezogen auf {new_trailing:.4f} ({secure_pct*100:.0f}% gesichert)'
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
    
    def get_dynamic_settings_for_signal(
        self,
        signal_strength: float,  # 0.0 bis 1.0
        market_analysis: MarketAnalysis,
        strategy: str,
        base_settings: Dict
    ) -> Dict:
        """
        V2.3.39: INTELLIGENTE DYNAMISCHE SETTINGS
        
        Passt SL/TP und andere Settings basierend auf:
        1. Signal-Stärke (confidence)
        2. Markt-Zustand (Volatilität, Trend)
        3. Strategie-Typ
        
        Returns:
            Optimierte Settings für diesen spezifischen Trade
        """
        # Basis-Werte aus Settings
        base_sl = base_settings.get(f'{strategy}_stop_loss_percent', 2.0)
        base_tp = base_settings.get(f'{strategy}_take_profit_percent', 4.0)
        
        # ═══════════════════════════════════════════════════════════════
        # DYNAMISCHE ANPASSUNG BASIEREND AUF SIGNAL-STÄRKE
        # ═══════════════════════════════════════════════════════════════
        
        # Starkes Signal (>0.8): Engerer SL, weiteres TP → Mehr Gewinn, weniger Risiko
        # Schwaches Signal (<0.6): Weiterer SL, engeres TP → Weniger Risiko
        if signal_strength >= 0.8:
            sl_multiplier = 0.8  # Enger SL
            tp_multiplier = 1.3  # Weiteres TP
            position_size_multiplier = 1.2  # Größere Position
            logger.info(f"🎯 STARKES SIGNAL ({signal_strength:.0%}): Aggressive Settings")
        elif signal_strength >= 0.7:
            sl_multiplier = 0.9
            tp_multiplier = 1.15
            position_size_multiplier = 1.0
            logger.info(f"📊 GUTES SIGNAL ({signal_strength:.0%}): Standard Settings")
        elif signal_strength >= 0.6:
            sl_multiplier = 1.0
            tp_multiplier = 1.0
            position_size_multiplier = 0.8
            logger.info(f"📉 MODERATES SIGNAL ({signal_strength:.0%}): Konservative Settings")
        else:
            sl_multiplier = 1.2  # Weiterer SL
            tp_multiplier = 0.8  # Engeres TP
            position_size_multiplier = 0.5  # Kleinere Position
            logger.info(f"⚠️ SCHWACHES SIGNAL ({signal_strength:.0%}): Sehr konservative Settings")
        
        # ═══════════════════════════════════════════════════════════════
        # ANPASSUNG BASIEREND AUF VOLATILITÄT (ATR)
        # ═══════════════════════════════════════════════════════════════
        
        atr_norm = market_analysis.atr_normalized if market_analysis else 1.0
        
        if atr_norm > 1.5:
            # Hohe Volatilität: Weitere Stops
            sl_multiplier *= 1.3
            tp_multiplier *= 1.2
            logger.info(f"📈 HOHE VOLATILITÄT (ATR: {atr_norm:.2f}x): Weitere Stops")
        elif atr_norm < 0.7:
            # Niedrige Volatilität: Engere Stops
            sl_multiplier *= 0.8
            tp_multiplier *= 0.9
            logger.info(f"📉 NIEDRIGE VOLATILITÄT (ATR: {atr_norm:.2f}x): Engere Stops")
        
        # ═══════════════════════════════════════════════════════════════
        # ANPASSUNG BASIEREND AUF MARKT-ZUSTAND
        # ═══════════════════════════════════════════════════════════════
        
        market_state = market_analysis.state.value if market_analysis else "range"
        
        if market_state in ["strong_uptrend", "strong_downtrend"]:
            # Starker Trend: Weitere TP, da Momentum vorhanden
            tp_multiplier *= 1.2
            logger.info("📈 STARKER TREND: Weiteres TP Target")
        elif market_state == "range":
            # Range: Engere Targets, schnellere Gewinne
            tp_multiplier *= 0.8
            logger.info("↔️ RANGE-MARKT: Engeres TP Target")
        elif market_state == "chaos":
            # Chaos: Sehr konservativ
            sl_multiplier *= 0.7  # Sehr enger SL!
            tp_multiplier *= 0.6
            position_size_multiplier *= 0.5
            logger.info("⚠️ CHAOS-MARKT: Minimales Risiko")
        
        # Berechne finale Werte
        final_sl = round(base_sl * sl_multiplier, 2)
        final_tp = round(base_tp * tp_multiplier, 2)
        
        # Sicherheitsgrenzen
        final_sl = max(0.5, min(5.0, final_sl))  # Min 0.5%, Max 5%
        final_tp = max(1.0, min(10.0, final_tp))  # Min 1%, Max 10%
        
        # TP muss mindestens 1.5x SL sein (Risk/Reward Ratio)
        if final_tp < final_sl * 1.5:
            final_tp = round(final_sl * 1.5, 2)
            logger.info(f"🎯 RR-Anpassung: TP erhöht auf {final_tp}% (min 1.5x SL)")
        
        result = {
            'stop_loss_percent': final_sl,
            'take_profit_percent': final_tp,
            'position_size_multiplier': round(position_size_multiplier, 2),
            'signal_strength': signal_strength,
            'market_state': market_state,
            'atr_normalized': atr_norm,
            'risk_reward_ratio': round(final_tp / final_sl, 2)
        }
        
        logger.info("📊 DYNAMISCHE SETTINGS:")
        logger.info(f"   SL: {base_sl}% → {final_sl}%")
        logger.info(f"   TP: {base_tp}% → {final_tp}%")
        logger.info(f"   Risk/Reward: {result['risk_reward_ratio']}:1")
        logger.info(f"   Position Size: {position_size_multiplier}x")
        
        return result
    
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
# V3.0 INTEGRATION: BOONER INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════

async def get_enhanced_confidence_v3(
    commodity: str,
    signal: str,
    base_confidence: float,
    pillar_scores: Dict[str, float],
    market_data: Dict[str, Any],
    strategy: str = "day",
    use_devils_advocate: bool = True
) -> Dict[str, Any]:
    """
    V3.0: Erweiterte Confidence-Berechnung mit Booner Intelligence Engine.
    
    Integriert:
    - Devil's Advocate Reasoning
    - Dynamic Weight Optimization
    - Chaos Circuit Breaker
    
    Args:
        commodity: Asset-Name
        signal: BUY/SELL
        base_confidence: Ursprünglicher 4-Säulen-Score
        pillar_scores: Dict mit Einzel-Scores der Säulen
        market_data: Dict mit aktuellen Marktdaten
        strategy: Aktive Strategie
        use_devils_advocate: Ob Devil's Advocate Analyse aktiviert
    
    Returns:
        Dict mit final_confidence, approved, reasoning, etc.
    """
    try:
        # Versuche Booner Intelligence Engine zu laden
        from booner_intelligence_engine import get_booner_engine
        
        engine = get_booner_engine()
        
        if use_devils_advocate:
            result = await engine.process_trade_decision(
                commodity=commodity,
                signal=signal,
                original_confidence=base_confidence,
                pillar_scores=pillar_scores,
                market_data=market_data,
                strategy=strategy
            )
            
            return {
                'original_confidence': base_confidence,
                'final_confidence': result['final_confidence'],
                'approved': result['approved'],
                'reasoning': result['reasoning'],
                'circuit_breaker_active': result['circuit_breaker_active'],
                'devils_advocate': result.get('devils_advocate_result'),
                'v3_enhanced': True
            }
        else:
            # Nur Circuit Breaker Check
            atr_norm = market_data.get('atr_normalized', 1.0)
            market_state = market_data.get('market_state', 'normal')
            
            threshold, cb_active, cb_reason = engine.circuit_breaker.check_circuit_breaker(
                atr_normalized=atr_norm,
                market_state=market_state,
                original_threshold=65.0
            )
            
            return {
                'original_confidence': base_confidence,
                'final_confidence': base_confidence,
                'approved': base_confidence >= threshold,
                'reasoning': cb_reason if cb_active else "Standard-Prüfung",
                'circuit_breaker_active': cb_active,
                'v3_enhanced': True
            }
            
    except ImportError:
        logger.warning("⚠️ Booner Intelligence Engine nicht verfügbar - verwende V2.6 Logik")
        return {
            'original_confidence': base_confidence,
            'final_confidence': base_confidence,
            'approved': base_confidence >= 65,
            'reasoning': "V2.6 Standard-Logik (BIE nicht geladen)",
            'circuit_breaker_active': False,
            'v3_enhanced': False
        }
    except Exception as e:
        logger.error(f"❌ V3.0 Enhancement fehlgeschlagen: {e}")
        return {
            'original_confidence': base_confidence,
            'final_confidence': base_confidence,
            'approved': base_confidence >= 65,
            'reasoning': f"Fallback auf V2.6 (Fehler: {str(e)})",
            'circuit_breaker_active': False,
            'v3_enhanced': False
        }


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

autonomous_trading = AutonomousTradingIntelligence()
