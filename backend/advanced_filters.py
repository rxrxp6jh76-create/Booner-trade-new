"""
🎯 ADVANCED TRADING FILTERS - V2.4.0 (Ultimate Upgrade)
=========================================================

Erweiterte Filter für höhere Trefferquote:
1. Spread-Filter - Nur handeln bei akzeptablem Spread
2. Multi-Timeframe Bestätigung (MTF) mit H1/H4 Confluence
3. Smart Entry (Pullback-Strategie)
4. Session-Filter (London/NY)
5. Korrelations-Check + Anti-Cluster (USD Exposure)
6. Chartmuster-Erkennung
7. DXY Correlation Guard (EUR/USD)
8. BTC Volatility Squeeze Filter
9. Spread-to-Profit Ratio Guard
10. Equity Curve Protection

Diese Filter werden VOR jedem Trade geprüft.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DXY (US DOLLAR INDEX) TREND ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

class DXYTrendAnalyzer:
    """
    Analysiert den US Dollar Index (DXY) Trend für EUR/USD Korrelation.
    Long EUR/USD nur bei bearish/neutral DXY.
    """
    
    _cache = {'data': None, 'timestamp': None}
    CACHE_DURATION = timedelta(minutes=15)
    
    @classmethod
    async def get_dxy_data(cls) -> Optional[Dict]:
        """
        Holt DXY-Daten von yfinance oder MT5.
        Cached für 15 Minuten.
        """
        now = datetime.now(timezone.utc)
        
        # Cache prüfen
        if cls._cache['data'] and cls._cache['timestamp']:
            if now - cls._cache['timestamp'] < cls.CACHE_DURATION:
                return cls._cache['data']
        
        try:
            import yfinance as yf
            
            # DXY Ticker
            dxy = yf.Ticker("DX-Y.NYB")
            hist = dxy.history(period="1mo", interval="1d")
            
            if hist.empty:
                logger.warning("⚠️ DXY: Keine Daten von yfinance")
                return None
            
            closes = hist['Close'].values
            current_price = closes[-1]
            
            # SMA 20 berechnen
            sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
            
            # Trend bestimmen
            if current_price > sma_20 * 1.005:  # > 0.5% über SMA
                trend = 'BULLISH'
            elif current_price < sma_20 * 0.995:  # < 0.5% unter SMA
                trend = 'BEARISH'
            else:
                trend = 'NEUTRAL'
            
            data = {
                'price': float(current_price),
                'sma_20': float(sma_20),
                'trend': trend,
                'deviation': float((current_price - sma_20) / sma_20 * 100),
                'timestamp': now.isoformat()
            }
            
            # Cache aktualisieren
            cls._cache = {'data': data, 'timestamp': now}
            
            logger.info(f"📊 DXY Update: ${current_price:.2f} | SMA20: ${sma_20:.2f} | Trend: {trend}")
            return data
            
        except Exception as e:
            logger.warning(f"⚠️ DXY Daten-Fehler: {e}")
            # Fallback: Versuche MT5-Daten
            return await cls._get_dxy_from_mt5()
    
    @classmethod
    async def _get_dxy_from_mt5(cls) -> Optional[Dict]:
        """Fallback: DXY von MT5 holen (USDX Symbol)"""
        try:
            from multi_platform_connector import multi_platform
            
            # Versuche USDX zu holen
            for platform_name, connector in multi_platform.platforms.items():
                try:
                    tick = await connector.get_current_price("USDX")
                    if tick:
                        # Vereinfachte Trend-Bestimmung ohne Historie
                        return {
                            'price': tick.get('bid', 0),
                            'sma_20': tick.get('bid', 0),  # Keine Historie verfügbar
                            'trend': 'NEUTRAL',
                            'deviation': 0,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'source': 'MT5'
                        }
                except:
                    continue
            return None
        except Exception as e:
            logger.debug(f"MT5 DXY Fallback fehlgeschlagen: {e}")
            return None
    
    @classmethod
    def get_dxy_trend(cls, dxy_data: Optional[Dict] = None) -> str:
        """
        Gibt den aktuellen DXY Trend zurück.
        Returns: 'BULLISH', 'BEARISH', oder 'NEUTRAL'
        """
        if dxy_data:
            return dxy_data.get('trend', 'NEUTRAL')
        
        # Aus Cache holen
        if cls._cache['data']:
            return cls._cache['data'].get('trend', 'NEUTRAL')
        
        return 'NEUTRAL'
    
    @classmethod
    def check_eurusd_dxy_correlation(cls, signal: str, dxy_data: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Prüft ob EUR/USD Signal mit DXY korreliert.
        
        - Long EUR/USD nur wenn DXY bearish/neutral
        - Short EUR/USD nur wenn DXY bullish/neutral
        
        Returns: (is_allowed, reason)
        """
        trend = cls.get_dxy_trend(dxy_data)
        
        if signal == 'BUY':
            # Long EUR/USD = bearish USD
            if trend == 'BULLISH':
                return False, f"❌ EUR/USD Long blockiert: DXY ist BULLISH (USD stark)"
            return True, f"✅ EUR/USD Long OK: DXY ist {trend}"
        
        elif signal == 'SELL':
            # Short EUR/USD = bullish USD
            if trend == 'BEARISH':
                return False, f"❌ EUR/USD Short blockiert: DXY ist BEARISH (USD schwach)"
            return True, f"✅ EUR/USD Short OK: DXY ist {trend}"
        
        return True, "✅ DXY Check: Kein direktes Signal"


# ═══════════════════════════════════════════════════════════════════════════
# BTC VOLATILITY SQUEEZE FILTER
# ═══════════════════════════════════════════════════════════════════════════

class BTCVolatilityFilter:
    """
    Bitcoin Volatility Squeeze Filter.
    Vermeidet Trading in low-liquid/choppy ranges.
    Verwendet Bollinger Band Width (BBW).
    """
    
    # BBW Thresholds
    MIN_BBW_PERCENT = 2.0   # Minimum BBW für Trading (vermeidet Squeeze)
    MAX_BBW_PERCENT = 15.0  # Maximum BBW (vermeidet extreme Volatilität)
    
    @classmethod
    def calculate_bollinger_bands(cls, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict:
        """
        Berechnet Bollinger Bands und Width.
        """
        if len(prices) < period:
            return None
        
        prices_arr = np.array(prices[-period:])
        sma = np.mean(prices_arr)
        std = np.std(prices_arr)
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        # Bollinger Band Width (BBW) als Prozent
        bbw = ((upper_band - lower_band) / sma) * 100
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band,
            'bbw': bbw,
            'current_price': prices[-1],
            'position': 'UPPER' if prices[-1] > upper_band else ('LOWER' if prices[-1] < lower_band else 'MIDDLE')
        }
    
    @classmethod
    def check_btc_volatility(cls, prices: List[float]) -> Tuple[bool, str, float]:
        """
        Prüft ob BTC-Volatilität für Trading geeignet ist.
        
        Returns: (is_suitable, reason, bbw_value)
        """
        bb_data = cls.calculate_bollinger_bands(prices)
        
        if not bb_data:
            return False, "❌ BTC: Nicht genug Preisdaten", 0
        
        bbw = bb_data['bbw']
        
        # Squeeze Detection (zu niedrige Volatilität)
        if bbw < cls.MIN_BBW_PERCENT:
            return False, f"❌ BTC Squeeze: BBW {bbw:.1f}% < {cls.MIN_BBW_PERCENT}% (Range-Markt)", bbw
        
        # Extreme Volatilität
        if bbw > cls.MAX_BBW_PERCENT:
            return False, f"⚠️ BTC Extreme Vola: BBW {bbw:.1f}% > {cls.MAX_BBW_PERCENT}%", bbw
        
        return True, f"✅ BTC Volatilität OK: BBW {bbw:.1f}%", bbw
    
    @classmethod
    def get_btc_signal_bias(cls, prices: List[float]) -> Tuple[str, float]:
        """
        Gibt Signal-Bias basierend auf BB-Position.
        
        Returns: (bias, confidence_boost)
        """
        bb_data = cls.calculate_bollinger_bands(prices)
        
        if not bb_data:
            return 'NEUTRAL', 0
        
        current = bb_data['current_price']
        upper = bb_data['upper']
        lower = bb_data['lower']
        middle = bb_data['middle']
        
        # Preis am oberen Band → Mean Reversion SELL
        if current >= upper * 0.99:
            return 'SELL', 0.1
        
        # Preis am unteren Band → Mean Reversion BUY
        if current <= lower * 1.01:
            return 'BUY', 0.1
        
        # Trending über/unter Middle
        if current > middle * 1.01:
            return 'BUY', 0.05
        elif current < middle * 0.99:
            return 'SELL', 0.05
        
        return 'NEUTRAL', 0


# ═══════════════════════════════════════════════════════════════════════════
# ANTI-CORRELATION / ANTI-CLUSTER GUARD
# ═══════════════════════════════════════════════════════════════════════════

class AntiClusterGuard:
    """
    Verhindert Over-Correlation durch Anti-Cluster Logic.
    Blockiert mehrere gleichzeitige Trades gegen USD.
    """
    
    # Assets die gegen USD korrelieren
    USD_INVERSE_ASSETS = {
        'GOLD': 'inverse',      # Gold steigt wenn USD fällt
        'SILVER': 'inverse',    # Silber korreliert mit Gold
        'EURUSD': 'inverse',    # Long EUR/USD = Short USD
        'BITCOIN': 'inverse',   # BTC oft inverse zu USD
    }
    
    USD_POSITIVE_ASSETS = {
        'USDJPY': 'positive',   # Long USD/JPY = Long USD
    }
    
    @classmethod
    def get_usd_exposure(cls, commodity: str, direction: str) -> str:
        """
        Bestimmt USD-Exposure eines Trades.
        Returns: 'LONG_USD', 'SHORT_USD', oder 'NEUTRAL'
        """
        if commodity in cls.USD_INVERSE_ASSETS:
            # Inverse: BUY = Short USD, SELL = Long USD
            return 'SHORT_USD' if direction == 'BUY' else 'LONG_USD'
        
        if commodity in cls.USD_POSITIVE_ASSETS:
            # Positive: BUY = Long USD, SELL = Short USD
            return 'LONG_USD' if direction == 'BUY' else 'SHORT_USD'
        
        return 'NEUTRAL'
    
    @classmethod
    def check_cluster_risk(
        cls, 
        commodity: str, 
        signal: str, 
        open_positions: List[Dict]
    ) -> Tuple[bool, str, float]:
        """
        Prüft Cluster-Risiko für neuen Trade.
        
        Returns: (is_allowed, reason, confidence_penalty)
        """
        if not open_positions:
            return True, "✅ Anti-Cluster: Keine offenen Positionen", 0
        
        new_exposure = cls.get_usd_exposure(commodity, signal)
        
        if new_exposure == 'NEUTRAL':
            return True, "✅ Anti-Cluster: Asset USD-neutral", 0
        
        # Zähle bestehende USD-Exposure
        long_usd_count = 0
        short_usd_count = 0
        
        for pos in open_positions:
            pos_commodity = pos.get('commodity') or pos.get('symbol', '')
            pos_direction = pos.get('direction') or ('BUY' if pos.get('type', '').upper().find('BUY') >= 0 else 'SELL')
            
            exposure = cls.get_usd_exposure(pos_commodity, pos_direction)
            
            if exposure == 'LONG_USD':
                long_usd_count += 1
            elif exposure == 'SHORT_USD':
                short_usd_count += 1
        
        # Prüfe Cluster-Risiko
        MAX_SAME_EXPOSURE = 3  # Max 3 Trades in gleiche USD-Richtung
        
        if new_exposure == 'SHORT_USD' and short_usd_count >= MAX_SAME_EXPOSURE:
            penalty = 0.15 + (short_usd_count - MAX_SAME_EXPOSURE) * 0.05
            return False, f"❌ Anti-Cluster: {short_usd_count} Short-USD Trades offen (Max: {MAX_SAME_EXPOSURE})", penalty
        
        if new_exposure == 'LONG_USD' and long_usd_count >= MAX_SAME_EXPOSURE:
            penalty = 0.15 + (long_usd_count - MAX_SAME_EXPOSURE) * 0.05
            return False, f"❌ Anti-Cluster: {long_usd_count} Long-USD Trades offen (Max: {MAX_SAME_EXPOSURE})", penalty
        
        # Warnung bei 2 Trades
        if new_exposure == 'SHORT_USD' and short_usd_count >= 2:
            return True, f"⚠️ Anti-Cluster: Bereits {short_usd_count} Short-USD Trades", 0.05
        
        if new_exposure == 'LONG_USD' and long_usd_count >= 2:
            return True, f"⚠️ Anti-Cluster: Bereits {long_usd_count} Long-USD Trades", 0.05
        
        return True, f"✅ Anti-Cluster: USD-Exposure ausgeglichen", 0


# ═══════════════════════════════════════════════════════════════════════════
# SPREAD-TO-PROFIT RATIO GUARD
# ═══════════════════════════════════════════════════════════════════════════

class SpreadToProfitGuard:
    """
    Blockiert Trades wenn Spread > X% des Take-Profit.
    Kritisch für Agrics/Metals mit hohen Spreads.
    """
    
    MAX_SPREAD_TO_TP_RATIO = 0.10  # Max 10% des TP darf Spread sein
    
    @classmethod
    def check_spread_to_profit_ratio(
        cls,
        spread_pips: float,
        take_profit_pips: float,
        commodity: str
    ) -> Tuple[bool, str]:
        """
        Prüft ob Spread-zu-TP Verhältnis akzeptabel ist.
        
        Returns: (is_acceptable, reason)
        """
        if take_profit_pips <= 0:
            return False, "❌ S2P: Take-Profit muss > 0 sein"
        
        ratio = spread_pips / take_profit_pips
        
        if ratio > cls.MAX_SPREAD_TO_TP_RATIO:
            return False, f"❌ S2P Guard: Spread ({spread_pips:.1f}) ist {ratio*100:.1f}% des TP ({take_profit_pips:.1f}) - Max: {cls.MAX_SPREAD_TO_TP_RATIO*100}%"
        
        return True, f"✅ S2P OK: Spread ist {ratio*100:.1f}% des TP"
    
    @classmethod
    def calculate_from_prices(
        cls,
        bid: float,
        ask: float,
        entry_price: float,
        take_profit: float
    ) -> Tuple[bool, str]:
        """
        Berechnet S2P aus Preisen.
        """
        spread = abs(ask - bid)
        tp_distance = abs(take_profit - entry_price)
        
        if tp_distance <= 0:
            return False, "❌ S2P: TP-Distanz ungültig"
        
        return cls.check_spread_to_profit_ratio(spread, tp_distance, "")


# ═══════════════════════════════════════════════════════════════════════════
# EQUITY CURVE PROTECTION
# ═══════════════════════════════════════════════════════════════════════════

class EquityCurveProtection:
    """
    Schützt vor Drawdown-Serien durch dynamische Threshold-Anpassung.
    Nach 3 Verlusten → +20% Confidence-Threshold.
    """
    
    _recent_trades = []  # Letzte Trades
    MAX_RECENT_TRADES = 10
    
    LOSS_STREAK_THRESHOLD = 3
    CONFIDENCE_INCREASE_PER_LOSS = 0.07  # +7% pro Verlust nach Streak
    
    @classmethod
    def record_trade_result(cls, profit: float):
        """Speichert Trade-Ergebnis."""
        cls._recent_trades.append({
            'profit': profit,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'is_win': profit > 0
        })
        
        # Nur letzte N Trades behalten
        if len(cls._recent_trades) > cls.MAX_RECENT_TRADES:
            cls._recent_trades = cls._recent_trades[-cls.MAX_RECENT_TRADES:]
    
    @classmethod
    def get_confidence_adjustment(cls) -> Tuple[float, str]:
        """
        Berechnet Confidence-Anpassung basierend auf Equity-Curve.
        
        Returns: (adjustment, reason)
        """
        if len(cls._recent_trades) < cls.LOSS_STREAK_THRESHOLD:
            return 0, "✅ Equity: Nicht genug Trades für Analyse"
        
        # Prüfe letzte N Trades auf Verlust-Serie
        recent = cls._recent_trades[-cls.LOSS_STREAK_THRESHOLD:]
        consecutive_losses = sum(1 for t in recent if not t['is_win'])
        
        if consecutive_losses >= cls.LOSS_STREAK_THRESHOLD:
            # Verlust-Serie erkannt
            adjustment = cls.CONFIDENCE_INCREASE_PER_LOSS * (consecutive_losses - cls.LOSS_STREAK_THRESHOLD + 1)
            adjustment = min(adjustment, 0.30)  # Max +30%
            return adjustment, f"⚠️ Equity Protection: {consecutive_losses} Verluste → +{adjustment*100:.0f}% Threshold"
        
        # Prüfe Win-Serie für Bonus
        consecutive_wins = sum(1 for t in recent if t['is_win'])
        if consecutive_wins >= 3:
            return -0.05, f"✅ Equity Bonus: {consecutive_wins} Gewinne → -5% Threshold"
        
        return 0, "✅ Equity: Normal"
    
    @classmethod
    def get_loss_streak(cls) -> int:
        """Gibt aktuelle Verlust-Serie zurück."""
        streak = 0
        for t in reversed(cls._recent_trades):
            if not t['is_win']:
                streak += 1
            else:
                break
        return streak


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
# MASTER FILTER - Kombiniert alle Filter (V2.4.0 Ultimate)
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
    V2.4.0: Kombiniert ALLE Filter für Ultimate Precision.
    Inkl. DXY Guard, BTC Squeeze, Anti-Cluster, S2P Ratio.
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
        signal_price: float = None,
        take_profit: float = None,
        stop_loss: float = None
    ) -> FilterResult:
        """
        V2.4.0: Führt ALLE Filter aus inkl. neue Ultimate Features.
        """
        reasons = []
        warnings = []
        confidence_adjustment = 0
        filters_passed = 0
        total_filters = 10  # Erhöht für neue Filter
        
        # ════════════════════════════════════════════════════════════════
        # 1. SPREAD-FILTER
        # ════════════════════════════════════════════════════════════════
        spread_ok, spread_reason, spread_pct = SpreadFilter.check_spread(commodity, bid, ask)
        if spread_ok:
            filters_passed += 1
            reasons.append(f"✅ Spread: {spread_pct:.3f}%")
        else:
            warnings.append(f"⚠️ {spread_reason}")
            confidence_adjustment -= 0.1
        
        # ════════════════════════════════════════════════════════════════
        # 2. SESSION-FILTER
        # ════════════════════════════════════════════════════════════════
        session_ok, session_reason, active_sessions = SessionFilter.check_trading_session(commodity)
        if session_ok:
            filters_passed += 1
            reasons.append(f"✅ Session: {session_reason}")
        else:
            warnings.append(f"⚠️ {session_reason}")
            confidence_adjustment -= 0.05
        
        # ════════════════════════════════════════════════════════════════
        # 3. KORRELATIONS-CHECK (Legacy)
        # ════════════════════════════════════════════════════════════════
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
        
        # ════════════════════════════════════════════════════════════════
        # 4. ANTI-CLUSTER GUARD (V2.4.0 NEU)
        # ════════════════════════════════════════════════════════════════
        if open_positions:
            cluster_ok, cluster_reason, cluster_penalty = AntiClusterGuard.check_cluster_risk(
                commodity, signal, open_positions
            )
            if cluster_ok:
                filters_passed += 1
                reasons.append(cluster_reason)
            else:
                warnings.append(cluster_reason)
                confidence_adjustment -= cluster_penalty
        else:
            filters_passed += 1
            reasons.append("✅ Anti-Cluster: Keine Positionen")
        
        # ════════════════════════════════════════════════════════════════
        # 5. DXY CORRELATION GUARD (V2.4.0 NEU - nur für EUR/USD)
        # ════════════════════════════════════════════════════════════════
        if commodity.upper() in ['EURUSD', 'EUR/USD']:
            try:
                dxy_data = await DXYTrendAnalyzer.get_dxy_data()
                dxy_ok, dxy_reason = DXYTrendAnalyzer.check_eurusd_dxy_correlation(signal, dxy_data)
                if dxy_ok:
                    filters_passed += 1
                    reasons.append(dxy_reason)
                else:
                    warnings.append(dxy_reason)
                    confidence_adjustment -= 0.15
            except Exception as e:
                logger.warning(f"DXY Check Fehler: {e}")
                filters_passed += 0.5
                warnings.append("⚠️ DXY: Daten nicht verfügbar")
        else:
            filters_passed += 1  # Nicht relevant für andere Assets
        
        # ════════════════════════════════════════════════════════════════
        # 6. BTC VOLATILITY SQUEEZE (V2.4.0 NEU - nur für BTC)
        # ════════════════════════════════════════════════════════════════
        if commodity.upper() in ['BITCOIN', 'BTC', 'BTCUSD']:
            if recent_prices and len(recent_prices) >= 20:
                btc_ok, btc_reason, bbw = BTCVolatilityFilter.check_btc_volatility(recent_prices)
                if btc_ok:
                    filters_passed += 1
                    reasons.append(btc_reason)
                    # Signal Bias prüfen
                    bias, bias_boost = BTCVolatilityFilter.get_btc_signal_bias(recent_prices)
                    if bias == signal:
                        confidence_adjustment += bias_boost
                        reasons.append(f"✅ BTC BB-Bias bestätigt: {bias}")
                else:
                    warnings.append(btc_reason)
                    confidence_adjustment -= 0.12
            else:
                filters_passed += 0.5
                warnings.append("⚠️ BTC: Nicht genug Preisdaten für Squeeze-Analyse")
        else:
            filters_passed += 1  # Nicht relevant für andere Assets
        
        # ════════════════════════════════════════════════════════════════
        # 7. SPREAD-TO-PROFIT RATIO (V2.4.0 NEU)
        # ════════════════════════════════════════════════════════════════
        if take_profit and bid and ask:
            s2p_ok, s2p_reason = SpreadToProfitGuard.calculate_from_prices(
                bid, ask, current_price, take_profit
            )
            if s2p_ok:
                filters_passed += 1
                reasons.append(s2p_reason)
            else:
                warnings.append(s2p_reason)
                confidence_adjustment -= 0.1
        else:
            filters_passed += 0.5
            warnings.append("⚠️ S2P: Kein Take-Profit definiert")
        
        # ════════════════════════════════════════════════════════════════
        # 8. EQUITY CURVE PROTECTION (V2.4.0 NEU)
        # ════════════════════════════════════════════════════════════════
        equity_adj, equity_reason = EquityCurveProtection.get_confidence_adjustment()
        confidence_adjustment += equity_adj
        if equity_adj != 0:
            if equity_adj > 0:
                warnings.append(equity_reason)
            else:
                reasons.append(equity_reason)
        filters_passed += 1  # Immer bestanden, nur Adjustment
        
        # ════════════════════════════════════════════════════════════════
        # 9. MULTI-TIMEFRAME (wenn Daten vorhanden)
        # ════════════════════════════════════════════════════════════════
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
            filters_passed += 0.5
            warnings.append("⚠️ MTF: Keine Multi-TF Daten")
        
        # ════════════════════════════════════════════════════════════════
        # 10. CHARTMUSTER
        # ════════════════════════════════════════════════════════════════
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
        
        # ════════════════════════════════════════════════════════════════
        # GESAMTBEWERTUNG
        # ════════════════════════════════════════════════════════════════
        score = filters_passed / total_filters
        
        # V2.4.0: Dynamischer Threshold basierend auf kritischen Filtern
        critical_passed = spread_ok and session_ok
        min_score_required = 0.5 if critical_passed else 0.65
        
        # Equity Protection kann Threshold erhöhen
        if equity_adj > 0:
            min_score_required += equity_adj
        
        passed = score >= min_score_required
        
        # Log Ergebnis
        logger.info(f"📊 MASTER FILTER V2.4.0: {commodity} {signal}")
        logger.info(f"   Score: {score:.0%} ({filters_passed:.1f}/{total_filters} Filter)")
        logger.info(f"   Min Required: {min_score_required:.0%}")
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
