"""
Market Regime Detection System
V2.3.35: Implementiert Marktregime-Erkennung für die Trading-App

Erkennt:
- Trend-Regime (Stark/Schwach)
- Range-Regime (Seitwärts)
- Volatilität (High/Low)
- News-Regime
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Marktregime-Typen
class MarketRegime:
    STRONG_TREND_UP = "STRONG_TREND_UP"
    STRONG_TREND_DOWN = "STRONG_TREND_DOWN"
    WEAK_TREND_UP = "WEAK_TREND_UP"
    WEAK_TREND_DOWN = "WEAK_TREND_DOWN"
    RANGE = "RANGE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    NEWS_PHASE = "NEWS_PHASE"
    UNKNOWN = "UNKNOWN"

# Strategie-Erlaubnis-Matrix
REGIME_STRATEGY_MATRIX = {
    MarketRegime.STRONG_TREND_UP: {
        "allowed": ["momentum", "swing", "breakout"],
        "blocked": ["mean_reversion", "grid"]
    },
    MarketRegime.STRONG_TREND_DOWN: {
        "allowed": ["momentum", "swing", "breakout"],
        "blocked": ["mean_reversion", "grid"]
    },
    MarketRegime.WEAK_TREND_UP: {
        "allowed": ["swing", "day"],
        "blocked": ["grid"]
    },
    MarketRegime.WEAK_TREND_DOWN: {
        "allowed": ["swing", "day"],
        "blocked": ["grid"]
    },
    MarketRegime.RANGE: {
        "allowed": ["mean_reversion", "grid"],
        "blocked": ["momentum", "breakout"]
    },
    MarketRegime.HIGH_VOLATILITY: {
        "allowed": ["breakout", "momentum"],
        "blocked": ["grid", "scalping"]
    },
    MarketRegime.LOW_VOLATILITY: {
        "allowed": ["mean_reversion", "grid"],
        "blocked": ["breakout", "scalping"]
    },
    MarketRegime.NEWS_PHASE: {
        "allowed": [],
        "blocked": ["all"]  # Keine Trades während News
    },
    MarketRegime.UNKNOWN: {
        "allowed": ["swing"],  # Nur konservative Strategien
        "blocked": ["scalping", "breakout", "grid"]
    }
}

# Strategie-Prioritäten (höher = höhere Priorität)
STRATEGY_PRIORITY = {
    "momentum": 100,
    "swing": 95,
    "breakout": 80,
    "day": 70,
    "mean_reversion": 60,
    "scalping": 50,
    "grid": 40
}


def detect_market_regime(
    prices: List[float],
    rsi: float,
    atr: float,
    atr_percentage: float,
    ema_short: float,
    ema_long: float,
    volume_ratio: float = 1.0,
    is_news_time: bool = False
) -> Tuple[str, Dict]:
    """
    Erkennt das aktuelle Marktregime basierend auf technischen Indikatoren.
    
    Args:
        prices: Liste der letzten Preise (mind. 20)
        rsi: Relative Strength Index (0-100)
        atr: Average True Range
        atr_percentage: ATR als % des Preises
        ema_short: Kurzfristiger EMA (z.B. 20)
        ema_long: Langfristiger EMA (z.B. 50)
        volume_ratio: Aktuelles Volumen / Durchschnittsvolumen
        is_news_time: Ob gerade News-Phase ist
        
    Returns:
        Tuple[regime_name, details_dict]
    """
    
    if is_news_time:
        return MarketRegime.NEWS_PHASE, {
            "reason": "News-Phase aktiv",
            "action": "Keine neuen Trades"
        }
    
    if len(prices) < 10:
        return MarketRegime.UNKNOWN, {"reason": "Nicht genug Daten"}
    
    current_price = prices[-1]
    
    # 1. Trend-Stärke berechnen
    price_change_pct = ((current_price - prices[0]) / prices[0]) * 100
    ema_diff_pct = ((ema_short - ema_long) / ema_long) * 100 if ema_long > 0 else 0
    
    # 2. Volatilität bewerten
    is_high_volatility = atr_percentage > 2.0  # Mehr als 2% ATR = hohe Volatilität
    is_low_volatility = atr_percentage < 0.5   # Weniger als 0.5% = niedrige Volatilität
    
    # 3. Range erkennen (Preis oszilliert um Mittelwert)
    price_std = np.std(prices[-20:]) if len(prices) >= 20 else np.std(prices)
    price_mean = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
    range_bound = (price_std / price_mean) < 0.01  # Weniger als 1% Standardabweichung
    
    # 4. Regime bestimmen
    details = {
        "price_change_pct": round(price_change_pct, 2),
        "ema_diff_pct": round(ema_diff_pct, 2),
        "atr_pct": round(atr_percentage, 2),
        "rsi": round(rsi, 1),
        "is_high_vol": is_high_volatility,
        "is_low_vol": is_low_volatility,
        "is_range": range_bound
    }
    
    # Volatilitäts-Expansion
    if is_high_volatility and volume_ratio > 1.5:
        return MarketRegime.HIGH_VOLATILITY, {
            **details,
            "reason": f"Hohe Volatilität (ATR: {atr_percentage:.2f}%, Vol: {volume_ratio:.1f}x)"
        }
    
    # Niedrige Volatilität
    if is_low_volatility and range_bound:
        return MarketRegime.LOW_VOLATILITY, {
            **details,
            "reason": f"Niedrige Volatilität (ATR: {atr_percentage:.2f}%)"
        }
    
    # Range / Seitwärts
    if range_bound and abs(ema_diff_pct) < 0.5:
        return MarketRegime.RANGE, {
            **details,
            "reason": "Seitwärtsmarkt (Range-bound)"
        }
    
    # Starker Trend
    if abs(price_change_pct) > 3.0 or abs(ema_diff_pct) > 1.5:
        if price_change_pct > 0 and ema_short > ema_long:
            return MarketRegime.STRONG_TREND_UP, {
                **details,
                "reason": f"Starker Aufwärtstrend (+{price_change_pct:.1f}%)"
            }
        elif price_change_pct < 0 and ema_short < ema_long:
            return MarketRegime.STRONG_TREND_DOWN, {
                **details,
                "reason": f"Starker Abwärtstrend ({price_change_pct:.1f}%)"
            }
    
    # Schwacher Trend
    if abs(price_change_pct) > 1.0:
        if price_change_pct > 0:
            return MarketRegime.WEAK_TREND_UP, {
                **details,
                "reason": f"Schwacher Aufwärtstrend (+{price_change_pct:.1f}%)"
            }
        else:
            return MarketRegime.WEAK_TREND_DOWN, {
                **details,
                "reason": f"Schwacher Abwärtstrend ({price_change_pct:.1f}%)"
            }
    
    # Default: Range
    return MarketRegime.RANGE, {
        **details,
        "reason": "Kein klarer Trend erkannt"
    }


def is_strategy_allowed(regime: str, strategy: str) -> Tuple[bool, str]:
    """
    Prüft ob eine Strategie im aktuellen Regime erlaubt ist.
    
    Returns:
        Tuple[is_allowed, reason]
    """
    strategy_lower = strategy.lower().replace("_trading", "").replace("trading", "")
    
    matrix = REGIME_STRATEGY_MATRIX.get(regime, REGIME_STRATEGY_MATRIX[MarketRegime.UNKNOWN])
    
    if "all" in matrix["blocked"]:
        return False, f"Alle Strategien gesperrt im Regime: {regime}"
    
    if strategy_lower in matrix["blocked"]:
        return False, f"Strategie '{strategy}' ist gesperrt im Regime: {regime}"
    
    if strategy_lower in matrix["allowed"]:
        return True, f"Strategie '{strategy}' ist optimal für Regime: {regime}"
    
    # Strategie nicht explizit erlaubt oder blockiert
    return True, f"Strategie '{strategy}' ist neutral im Regime: {regime}"


def get_highest_priority_strategy(strategies: List[str]) -> Optional[str]:
    """
    Gibt die Strategie mit der höchsten Priorität zurück.
    """
    if not strategies:
        return None
    
    sorted_strategies = sorted(
        strategies,
        key=lambda s: STRATEGY_PRIORITY.get(s.lower().replace("_trading", ""), 0),
        reverse=True
    )
    
    return sorted_strategies[0] if sorted_strategies else None


def check_news_window(commodity_id: str, current_time: datetime = None) -> bool:
    """
    Prüft ob gerade eine News-Phase für das Asset ist.
    Wichtig für EUR/USD und andere news-sensitive Assets.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # News-Zeiten (UTC)
    NEWS_WINDOWS = {
        "EURUSD": [
            (8, 30, 9, 0),   # EU Open
            (12, 30, 13, 30), # US News
            (14, 0, 14, 30),  # FOMC, etc.
            (18, 0, 18, 30),  # US Close
        ],
        "DEFAULT": [
            (13, 30, 14, 0),  # US Economic Data
        ]
    }
    
    windows = NEWS_WINDOWS.get(commodity_id, NEWS_WINDOWS["DEFAULT"])
    
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_minutes = current_hour * 60 + current_minute
    
    for start_h, start_m, end_h, end_m in windows:
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        if start_minutes <= current_minutes <= end_minutes:
            return True
    
    return False


# Export
__all__ = [
    'MarketRegime',
    'REGIME_STRATEGY_MATRIX',
    'STRATEGY_PRIORITY',
    'detect_market_regime',
    'is_strategy_allowed',
    'get_highest_priority_strategy',
    'check_news_window'
]
