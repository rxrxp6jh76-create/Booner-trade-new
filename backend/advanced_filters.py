"""
🎯 ADVANCED TRADING FILTERS - V2.3.39
=====================================

Erweiterte Filter für höhere Trefferquote:
1. Spread-Filter - Nur handeln bei akzeptablem Spread
2. Multi-Timeframe Bestätigung (MTF)
3. Smart Entry (Pullback-Strategie)
4. Session-Filter (London/NY)
5. Korrelations-Check
6. Chartmuster-Erkennung

Diese Filter werden VOR jedem Trade geprüft.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 1. SPREAD-FILTER
# ═══════════════════════════════════════════════════════════════════════════

class SpreadFilter:
    """
    Prüft ob der Spread akzeptabel ist für einen Trade.
    Große Spreads führen zu sofortigen Verlusten.
    """
    
    # Maximum Spread in % des Preises pro Asset-Klasse
    # V2.3.40: Erhöht für realistischere Trading-Bedingungen
    MAX_SPREAD_PERCENT = {
        'forex': 0.05,      # 0.05% für Forex
        'commodities': 0.30, # 0.30% für Rohstoffe (erhöht von 0.15%)
        'indices': 0.10,    # 0.10% für Indizes
        'crypto': 0.40,     # 0.40% für Crypto
        'default': 0.25     # 0.25% Standard (erhöht von 0.10%)
    }
    
    # Asset zu Klasse Mapping
    ASSET_CLASS = {
        'EURUSD': 'forex', 'GBPUSD': 'forex', 'USDJPY': 'forex',
        'GOLD': 'commodities', 'SILVER': 'commodities', 
        'WTI_CRUDE': 'commodities', 'BRENT_CRUDE': 'commodities',
        'NATURAL_GAS': 'commodities', 'COCOA': 'commodities',
        'COFFEE': 'commodities', 'SUGAR': 'commodities',
        'COPPER': 'commodities', 'PLATINUM': 'commodities',
        'CORN': 'commodities', 'WHEAT': 'commodities', 'SOYBEAN': 'commodities',
        'BITCOIN': 'crypto', 'ETHEREUM': 'crypto',
        'SP500': 'indices', 'NASDAQ': 'indices', 'DAX': 'indices',
    }
    
    @classmethod
    def check_spread(cls, commodity: str, bid: float, ask: float) -> Tuple[bool, str, float]:
        """
        Prüft ob der Spread akzeptabel ist.
        
        Returns:
            (is_acceptable, reason, spread_percent)
        """
        if not bid or not ask or bid <= 0:
            return False, "Ungültige Bid/Ask Preise", 0
        
        spread = ask - bid
        spread_percent = (spread / bid) * 100
        
        asset_class = cls.ASSET_CLASS.get(commodity, 'default')
        max_spread = cls.MAX_SPREAD_PERCENT.get(asset_class, cls.MAX_SPREAD_PERCENT['default'])
        
        if spread_percent > max_spread:
            return False, f"Spread zu groß: {spread_percent:.3f}% > {max_spread}% (Max für {asset_class})", spread_percent
        
        logger.info(f"✅ Spread OK: {commodity} = {spread_percent:.3f}% (Max: {max_spread}%)")
        return True, f"Spread akzeptabel: {spread_percent:.3f}%", spread_percent


# ═══════════════════════════════════════════════════════════════════════════
# 2. MULTI-TIMEFRAME BESTÄTIGUNG (MTF)
# ═══════════════════════════════════════════════════════════════════════════

class MultiTimeframeFilter:
    """
    Prüft ob das Signal über mehrere Timeframes bestätigt wird.
    Trade nur wenn H1, H4 und D1 in die gleiche Richtung zeigen.
    """
    
    @classmethod
    def analyze_timeframe(cls, prices: List[float], period: int = 20) -> str:
        """
        Analysiert einen Timeframe und gibt die Richtung zurück.
        
        Returns:
            'bullish', 'bearish', oder 'neutral'
        """
        if not prices or len(prices) < period:
            return 'neutral'
        
        # Berechne EMA
        recent = prices[-period:]
        ema = sum(recent) / len(recent)
        current = prices[-1]
        
        # Berechne Trend-Stärke
        price_change = (current - prices[-period]) / prices[-period] * 100
        
        if current > ema and price_change > 0.5:
            return 'bullish'
        elif current < ema and price_change < -0.5:
            return 'bearish'
        return 'neutral'
    
    @classmethod
    def check_mtf_confirmation(
        cls,
        h1_prices: List[float],
        h4_prices: List[float],
        d1_prices: List[float],
        signal: str  # 'BUY' oder 'SELL'
    ) -> Tuple[bool, str, int]:
        """
        Prüft Multi-Timeframe Bestätigung.
        
        Returns:
            (is_confirmed, reason, confirmation_count)
        """
        h1_trend = cls.analyze_timeframe(h1_prices, 20)
        h4_trend = cls.analyze_timeframe(h4_prices, 20)
        d1_trend = cls.analyze_timeframe(d1_prices, 20)
        
        expected_trend = 'bullish' if signal == 'BUY' else 'bearish'
        
        confirmations = 0
        details = []
        
        if h1_trend == expected_trend:
            confirmations += 1
            details.append("H1 ✅")
        else:
            details.append(f"H1 ❌ ({h1_trend})")
            
        if h4_trend == expected_trend:
            confirmations += 1
            details.append("H4 ✅")
        else:
            details.append(f"H4 ❌ ({h4_trend})")
            
        if d1_trend == expected_trend:
            confirmations += 1
            details.append("D1 ✅")
        else:
            details.append(f"D1 ❌ ({d1_trend})")
        
        # Mindestens 2 von 3 Timeframes müssen bestätigen
        is_confirmed = confirmations >= 2
        reason = f"MTF: {' | '.join(details)} ({confirmations}/3)"
        
        if is_confirmed:
            logger.info(f"✅ {reason}")
        else:
            logger.warning(f"⛔ {reason}")
        
        return is_confirmed, reason, confirmations


# ═══════════════════════════════════════════════════════════════════════════
# 3. SMART ENTRY (PULLBACK-STRATEGIE)
# ═══════════════════════════════════════════════════════════════════════════

class SmartEntryFilter:
    """
    Wartet auf einen Pullback bevor Einstieg.
    Vermeidet Einstieg am lokalen Hoch/Tief.
    """
    
    # Pullback-Prozent pro Asset-Klasse
    PULLBACK_PERCENT = {
        'forex': 0.05,      # 0.05% Pullback
        'commodities': 0.3,  # 0.3% Pullback
        'crypto': 0.5,      # 0.5% Pullback
        'indices': 0.2,     # 0.2% Pullback
        'default': 0.2
    }
    
    @classmethod
    def check_pullback_entry(
        cls,
        commodity: str,
        signal: str,
        current_price: float,
        recent_prices: List[float],  # Letzte 10-20 Preise
        signal_price: float  # Preis als Signal generiert wurde
    ) -> Tuple[bool, str, float]:
        """
        Prüft ob ein guter Einstiegspunkt erreicht ist.
        
        Returns:
            (is_good_entry, reason, entry_quality_score)
        """
        if not recent_prices or len(recent_prices) < 5:
            return True, "Nicht genug Daten für Pullback-Analyse", 0.5
        
        asset_class = SpreadFilter.ASSET_CLASS.get(commodity, 'default')
        required_pullback = cls.PULLBACK_PERCENT.get(asset_class, cls.PULLBACK_PERCENT['default'])
        
        # Finde lokales Hoch/Tief
        recent_high = max(recent_prices[-10:])
        recent_low = min(recent_prices[-10:])
        
        if signal == 'BUY':
            # Für BUY: Warte bis Preis etwas vom Hoch zurückgekommen ist
            pullback_from_high = (recent_high - current_price) / recent_high * 100
            
            if pullback_from_high >= required_pullback:
                entry_quality = min(1.0, pullback_from_high / (required_pullback * 2))
                return True, f"Guter BUY Entry: {pullback_from_high:.2f}% Pullback vom Hoch", entry_quality
            else:
                return False, f"Warte auf Pullback: Nur {pullback_from_high:.2f}% (benötigt {required_pullback}%)", 0.3
        
        else:  # SELL
            # Für SELL: Warte bis Preis etwas vom Tief gestiegen ist
            bounce_from_low = (current_price - recent_low) / recent_low * 100
            
            if bounce_from_low >= required_pullback:
                entry_quality = min(1.0, bounce_from_low / (required_pullback * 2))
                return True, f"Guter SELL Entry: {bounce_from_low:.2f}% Bounce vom Tief", entry_quality
            else:
                return False, f"Warte auf Bounce: Nur {bounce_from_low:.2f}% (benötigt {required_pullback}%)", 0.3


# ═══════════════════════════════════════════════════════════════════════════
# 4. SESSION-FILTER
# ═══════════════════════════════════════════════════════════════════════════

class SessionFilter:
    """
    Handelt nur während aktiver Trading-Sessions.
    Vermeidet schlechte Fills in ruhigen Phasen.
    """
    
    # Trading Sessions (UTC)
    SESSIONS = {
        'london': {'start': 8, 'end': 16},      # 08:00-16:00 UTC
        'new_york': {'start': 13, 'end': 21},   # 13:00-21:00 UTC
        'tokyo': {'start': 0, 'end': 8},        # 00:00-08:00 UTC
        'sydney': {'start': 22, 'end': 6},      # 22:00-06:00 UTC (überlappt Mitternacht)
    }
    
    # Beste Sessions pro Asset-Klasse
    BEST_SESSIONS = {
        'forex': ['london', 'new_york'],
        'commodities': ['london', 'new_york'],
        'indices': ['new_york'],
        'crypto': ['london', 'new_york', 'tokyo', 'sydney'],  # 24/7
    }
    
    @classmethod
    def is_session_active(cls, session_name: str, current_hour: int) -> bool:
        """Prüft ob eine Session aktiv ist."""
        session = cls.SESSIONS.get(session_name)
        if not session:
            return False
        
        start = session['start']
        end = session['end']
        
        # Handle Sessions die über Mitternacht gehen
        if start > end:
            return current_hour >= start or current_hour < end
        return start <= current_hour < end
    
    @classmethod
    def check_trading_session(cls, commodity: str) -> Tuple[bool, str, List[str]]:
        """
        Prüft ob jetzt eine gute Trading-Session ist.
        
        Returns:
            (is_good_session, reason, active_sessions)
        """
        current_hour = datetime.now(timezone.utc).hour
        asset_class = SpreadFilter.ASSET_CLASS.get(commodity, 'default')
        best_sessions = cls.BEST_SESSIONS.get(asset_class, ['london', 'new_york'])
        
        active_sessions = []
        for session_name in cls.SESSIONS.keys():
            if cls.is_session_active(session_name, current_hour):
                active_sessions.append(session_name)
        
        # Prüfe ob eine der besten Sessions aktiv ist
        good_session_active = any(s in active_sessions for s in best_sessions)
        
        if good_session_active:
            return True, f"Aktive Sessions: {', '.join(active_sessions)}", active_sessions
        elif active_sessions:
            return True, f"Session OK (nicht optimal): {', '.join(active_sessions)}", active_sessions
        else:
            return False, f"Keine aktive Session (Stunde: {current_hour} UTC)", active_sessions


# ═══════════════════════════════════════════════════════════════════════════
# 5. KORRELATIONS-CHECK
# ═══════════════════════════════════════════════════════════════════════════

class CorrelationFilter:
    """
    Verhindert gleichzeitige Trades auf stark korrelierten Assets.
    Reduziert Cluster-Risiko.
    """
    
    # Stark korrelierte Asset-Gruppen (korrelieren > 0.7)
    CORRELATION_GROUPS = {
        'precious_metals': ['GOLD', 'SILVER', 'PLATINUM'],
        'oil': ['WTI_CRUDE', 'BRENT_CRUDE'],
        'grains': ['CORN', 'WHEAT', 'SOYBEAN'],
        'soft': ['COCOA', 'COFFEE', 'SUGAR'],
        'usd_pairs': ['EURUSD', 'GBPUSD'],  # Beide gegen USD
        'crypto': ['BITCOIN', 'ETHEREUM'],
    }
    
    @classmethod
    def get_correlation_group(cls, commodity: str) -> Optional[str]:
        """Findet die Korrelationsgruppe eines Assets."""
        for group_name, assets in cls.CORRELATION_GROUPS.items():
            if commodity in assets:
                return group_name
        return None
    
    @classmethod
    def check_correlation(
        cls,
        commodity: str,
        open_positions: List[Dict]
    ) -> Tuple[bool, str, List[str]]:
        """
        Prüft ob bereits ein korreliertes Asset gehandelt wird.
        
        Returns:
            (can_trade, reason, conflicting_assets)
        """
        my_group = cls.get_correlation_group(commodity)
        
        if not my_group:
            return True, f"{commodity} hat keine Korrelationsgruppe", []
        
        # Finde alle Assets aus der gleichen Gruppe die bereits offen sind
        conflicting = []
        for pos in open_positions:
            pos_commodity = pos.get('commodity') or pos.get('symbol', '')
            # Normalisiere Symbol-Namen
            for asset in cls.CORRELATION_GROUPS.get(my_group, []):
                if asset in pos_commodity.upper():
                    if asset != commodity:
                        conflicting.append(asset)
        
        if conflicting:
            return False, f"Korrelierte Position offen: {', '.join(conflicting)} (Gruppe: {my_group})", conflicting
        
        return True, f"Keine korrelierten Positionen offen", []


# ═══════════════════════════════════════════════════════════════════════════
# 6. CHARTMUSTER-ERKENNUNG
# ═══════════════════════════════════════════════════════════════════════════

class ChartPatternDetector:
    """
    Erkennt klassische Chartmuster.
    Bestätigt oder widerlegt Signale.
    """
    
    @classmethod
    def detect_double_top(cls, prices: List[float], tolerance: float = 0.02) -> Tuple[bool, float]:
        """
        Erkennt Double Top Pattern (bearish).
        
        Returns:
            (is_detected, pattern_strength)
        """
        if len(prices) < 20:
            return False, 0
        
        # Finde die zwei höchsten Punkte
        recent = prices[-20:]
        max_idx1 = recent.index(max(recent))
        
        # Zweites Maximum (nicht direkt neben dem ersten)
        second_half = recent[:max_idx1-3] if max_idx1 > 5 else recent[max_idx1+3:]
        if not second_half:
            return False, 0
        
        max2 = max(second_half)
        max1 = recent[max_idx1]
        
        # Prüfe ob beide Maxima ähnlich sind (innerhalb Toleranz)
        diff_percent = abs(max1 - max2) / max1
        
        if diff_percent <= tolerance:
            # Double Top erkannt!
            strength = 1.0 - diff_percent  # Je näher, desto stärker
            return True, strength
        
        return False, 0
    
    @classmethod
    def detect_double_bottom(cls, prices: List[float], tolerance: float = 0.02) -> Tuple[bool, float]:
        """
        Erkennt Double Bottom Pattern (bullish).
        
        Returns:
            (is_detected, pattern_strength)
        """
        if len(prices) < 20:
            return False, 0
        
        recent = prices[-20:]
        min_idx1 = recent.index(min(recent))
        
        # Zweites Minimum
        second_half = recent[:min_idx1-3] if min_idx1 > 5 else recent[min_idx1+3:]
        if not second_half:
            return False, 0
        
        min2 = min(second_half)
        min1 = recent[min_idx1]
        
        diff_percent = abs(min1 - min2) / min1
        
        if diff_percent <= tolerance:
            strength = 1.0 - diff_percent
            return True, strength
        
        return False, 0
    
    @classmethod
    def detect_head_shoulders(cls, prices: List[float]) -> Tuple[bool, str, float]:
        """
        Erkennt Head & Shoulders Pattern.
        
        Returns:
            (is_detected, pattern_type, strength)
        """
        if len(prices) < 30:
            return False, "none", 0
        
        recent = prices[-30:]
        
        # Teile in 3 Segmente
        seg1 = recent[:10]
        seg2 = recent[10:20]
        seg3 = recent[20:]
        
        max1, max2, max3 = max(seg1), max(seg2), max(seg3)
        min1, min2, min3 = min(seg1), min(seg2), min(seg3)
        
        # Head & Shoulders (bearish): Mitte höher als Schultern
        if max2 > max1 and max2 > max3:
            shoulder_avg = (max1 + max3) / 2
            head_height = max2 - shoulder_avg
            if head_height / shoulder_avg > 0.01:  # Mindestens 1% höher
                strength = min(1.0, head_height / shoulder_avg * 10)
                return True, "head_shoulders_top", strength
        
        # Inverse Head & Shoulders (bullish): Mitte tiefer als Schultern
        if min2 < min1 and min2 < min3:
            shoulder_avg = (min1 + min3) / 2
            head_depth = shoulder_avg - min2
            if head_depth / shoulder_avg > 0.01:
                strength = min(1.0, head_depth / shoulder_avg * 10)
                return True, "head_shoulders_bottom", strength
        
        return False, "none", 0
    
    @classmethod
    def analyze_patterns(cls, prices: List[float], signal: str) -> Tuple[bool, str, float]:
        """
        Analysiert alle Patterns und prüft ob sie das Signal bestätigen.
        
        Returns:
            (confirms_signal, pattern_description, confidence_boost)
        """
        patterns_found = []
        confidence_boost = 0
        confirms = True
        
        # Double Top (bearish)
        dt_detected, dt_strength = cls.detect_double_top(prices)
        if dt_detected:
            patterns_found.append(f"Double Top ({dt_strength:.0%})")
            if signal == 'SELL':
                confidence_boost += dt_strength * 0.1  # +10% Konfidenz
            else:
                confirms = False
                confidence_boost -= dt_strength * 0.15  # -15% für Widerspruch
        
        # Double Bottom (bullish)
        db_detected, db_strength = cls.detect_double_bottom(prices)
        if db_detected:
            patterns_found.append(f"Double Bottom ({db_strength:.0%})")
            if signal == 'BUY':
                confidence_boost += db_strength * 0.1
            else:
                confirms = False
                confidence_boost -= db_strength * 0.15
        
        # Head & Shoulders
        hs_detected, hs_type, hs_strength = cls.detect_head_shoulders(prices)
        if hs_detected:
            patterns_found.append(f"{hs_type} ({hs_strength:.0%})")
            if hs_type == "head_shoulders_top" and signal == 'SELL':
                confidence_boost += hs_strength * 0.15
            elif hs_type == "head_shoulders_bottom" and signal == 'BUY':
                confidence_boost += hs_strength * 0.15
            else:
                confirms = False
                confidence_boost -= hs_strength * 0.1
        
        if patterns_found:
            description = f"Patterns: {', '.join(patterns_found)}"
        else:
            description = "Keine Chartmuster erkannt"
        
        return confirms, description, confidence_boost


# ═══════════════════════════════════════════════════════════════════════════
# MASTER FILTER - Kombiniert alle Filter
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FilterResult:
    """Ergebnis der Filter-Prüfung"""
    passed: bool
    score: float  # 0.0 bis 1.0
    reasons: List[str]
    warnings: List[str]
    confidence_adjustment: float  # Anpassung für Confidence Score


class MasterFilter:
    """
    Kombiniert alle Filter und gibt eine Gesamtbewertung.
    """
    
    @classmethod
    async def run_all_filters(
        cls,
        commodity: str,
        signal: str,
        current_price: float,
        bid: float,
        ask: float,
        recent_prices: List[float],
        h1_prices: List[float] = None,
        h4_prices: List[float] = None,
        d1_prices: List[float] = None,
        open_positions: List[Dict] = None,
        signal_price: float = None
    ) -> FilterResult:
        """
        Führt alle Filter aus und gibt das Gesamtergebnis zurück.
        """
        reasons = []
        warnings = []
        confidence_adjustment = 0
        filters_passed = 0
        total_filters = 6
        
        # 1. SPREAD-FILTER
        spread_ok, spread_reason, spread_pct = SpreadFilter.check_spread(commodity, bid, ask)
        if spread_ok:
            filters_passed += 1
            reasons.append(f"✅ Spread: {spread_pct:.3f}%")
        else:
            warnings.append(f"⚠️ {spread_reason}")
            confidence_adjustment -= 0.1
        
        # 2. SESSION-FILTER
        session_ok, session_reason, active_sessions = SessionFilter.check_trading_session(commodity)
        if session_ok:
            filters_passed += 1
            reasons.append(f"✅ Session: {session_reason}")
        else:
            warnings.append(f"⚠️ {session_reason}")
            confidence_adjustment -= 0.05
        
        # 3. KORRELATIONS-CHECK
        if open_positions:
            corr_ok, corr_reason, conflicts = CorrelationFilter.check_correlation(commodity, open_positions)
            if corr_ok:
                filters_passed += 1
                reasons.append(f"✅ Korrelation: OK")
            else:
                warnings.append(f"⚠️ {corr_reason}")
                confidence_adjustment -= 0.15
        else:
            filters_passed += 1
            reasons.append("✅ Korrelation: Keine offenen Positionen")
        
        # 4. MULTI-TIMEFRAME (wenn Daten vorhanden)
        if h1_prices and h4_prices and d1_prices:
            mtf_ok, mtf_reason, mtf_count = MultiTimeframeFilter.check_mtf_confirmation(
                h1_prices, h4_prices, d1_prices, signal
            )
            if mtf_ok:
                filters_passed += 1
                reasons.append(f"✅ MTF: {mtf_count}/3 bestätigt")
                confidence_adjustment += mtf_count * 0.05
            else:
                warnings.append(f"⚠️ {mtf_reason}")
                confidence_adjustment -= 0.1
        else:
            filters_passed += 0.5  # Halbe Punkte wenn keine Daten
            warnings.append("⚠️ MTF: Keine Multi-TF Daten")
        
        # 5. SMART ENTRY (Pullback)
        if recent_prices and len(recent_prices) >= 10:
            entry_ok, entry_reason, entry_quality = SmartEntryFilter.check_pullback_entry(
                commodity, signal, current_price, recent_prices, signal_price or current_price
            )
            if entry_ok:
                filters_passed += 1
                reasons.append(f"✅ Entry: {entry_reason}")
                confidence_adjustment += entry_quality * 0.05
            else:
                warnings.append(f"⚠️ {entry_reason}")
                # Nicht blockieren, nur warnen
        else:
            filters_passed += 0.5
            warnings.append("⚠️ Entry: Nicht genug Daten für Pullback-Analyse")
        
        # 6. CHARTMUSTER
        if recent_prices and len(recent_prices) >= 20:
            pattern_confirms, pattern_desc, pattern_boost = ChartPatternDetector.analyze_patterns(
                recent_prices, signal
            )
            if pattern_confirms:
                filters_passed += 1
                reasons.append(f"✅ Patterns: {pattern_desc}")
            else:
                warnings.append(f"⚠️ Pattern-Widerspruch: {pattern_desc}")
            confidence_adjustment += pattern_boost
        else:
            filters_passed += 0.5
        
        # Berechne Gesamtscore
        score = filters_passed / total_filters
        # V2.3.40: Spread nicht mehr mandatory, nur ein Faktor
        # Alte Logik: passed = score >= 0.6 and spread_ok
        # Neue Logik: Bei schlechtem Spread nur Warnung, aber Trade nicht blockieren
        min_score_required = 0.5 if spread_ok else 0.65  # Höherer Score erforderlich bei schlechtem Spread
        passed = score >= min_score_required
        
        # Log Ergebnis
        logger.info(f"📊 MASTER FILTER RESULT: {commodity} {signal}")
        logger.info(f"   Score: {score:.0%} ({filters_passed}/{total_filters} Filter)")
        logger.info(f"   Confidence Adjustment: {confidence_adjustment:+.0%}")
        for r in reasons:
            logger.info(f"   {r}")
        for w in warnings:
            logger.warning(f"   {w}")
        
        return FilterResult(
            passed=passed,
            score=score,
            reasons=reasons,
            warnings=warnings,
            confidence_adjustment=confidence_adjustment
        )


# Export
__all__ = [
    'SpreadFilter',
    'MultiTimeframeFilter', 
    'SmartEntryFilter',
    'SessionFilter',
    'CorrelationFilter',
    'ChartPatternDetector',
    'MasterFilter',
    'FilterResult'
]
