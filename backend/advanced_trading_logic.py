"""
ADVANCED TRADING LOGIC - Prädiktives Trading-Modul V2.4.0
=========================================================

Implementiert fortgeschrittene KI-Logik für alle 7 Strategien:
1. Scalping - Order Flow Imbalance, Micro-Momentum
2. Day Trading - VWAP, ATR-basiertes SL/TP
3. Momentum - Trailing Stop, MACD-Histogramm
4. Breakout - Range-Analyse, 200% TP
5. Mean Reversion - Bollinger Bands, Standardabweichung
6. Grid Trading - ADR-basierte Gitter
7. Swing Trading - Multi-Timeframe, Fibonacci Extensions

Features:
- Konfidenz-Score (0-100%) mit Schwellwert 65%
- Dynamische SL/TP basierend auf ATR und Volatilität
- CRV-Anpassung basierend auf Wahrscheinlichkeit
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)


class TradingStrategy(Enum):
    SCALPING = "scalping"
    DAY_TRADING = "day"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    GRID = "grid"
    SWING = "swing"


@dataclass
class TradeSignal:
    """Struktur für ein Trading-Signal mit allen relevanten Daten"""
    strategy: TradingStrategy
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-100%
    entry_price: float
    stop_loss: float
    take_profit: float
    trailing_stop: bool
    crv: float  # Chance-Risiko-Verhältnis
    atr: float
    volatility: float
    reasons: List[str]
    indicators: Dict
    
    def should_execute(self, min_confidence: float = 65.0) -> bool:
        """Prüft ob der Trade ausgeführt werden soll"""
        return self.signal != 'HOLD' and self.confidence >= min_confidence


class AdvancedTradingLogic:
    """
    Fortgeschrittene Trading-Logik mit prädiktiver Analyse
    """
    
    # Minimum Konfidenz für Trade-Ausführung
    MIN_CONFIDENCE = 65.0
    
    # CRV-Mapping basierend auf Konfidenz
    CRV_MAPPING = {
        'aggressive': 3.0,    # Konfidenz > 80%
        'standard': 2.0,      # Konfidenz 65-80%
        'defensive': 1.5      # Konfidenz < 65% (kein Trade)
    }
    
    def __init__(self):
        self.last_signals = {}  # Cache für letzte Signale
        
    # ═══════════════════════════════════════════════════════════════════
    # HAUPT-ANALYSE-METHODE
    # ═══════════════════════════════════════════════════════════════════
    
    def analyze_for_strategy(
        self,
        strategy: TradingStrategy,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float] = None,
        bid_volume: float = None,
        ask_volume: float = None,
        spread: float = None
    ) -> TradeSignal:
        """
        Haupteinstiegspunkt für die Analyse einer Strategie
        
        Args:
            strategy: Die zu analysierende Strategie
            current_price: Aktueller Preis
            prices: Liste der Schlusskurse
            highs: Liste der Hochkurse
            lows: Liste der Tiefkurse
            volumes: Liste der Volumen (optional)
            bid_volume: Bid-Volumen für Order Flow (optional)
            ask_volume: Ask-Volumen für Order Flow (optional)
            spread: Aktueller Spread (optional)
        
        Returns:
            TradeSignal mit allen Informationen
        """
        
        # Gemeinsame Berechnungen
        atr = self._calculate_atr(prices, highs, lows, 14)
        volatility = self._calculate_volatility(prices[-20:]) if len(prices) >= 20 else 0
        
        # Strategie-spezifische Analyse
        if strategy == TradingStrategy.SCALPING:
            return self._analyze_scalping(current_price, prices, highs, lows, atr, volatility, bid_volume, ask_volume, spread)
        elif strategy == TradingStrategy.DAY_TRADING:
            return self._analyze_day_trading(current_price, prices, highs, lows, volumes, atr, volatility)
        elif strategy == TradingStrategy.MOMENTUM:
            return self._analyze_momentum(current_price, prices, highs, lows, volumes, atr, volatility)
        elif strategy == TradingStrategy.BREAKOUT:
            return self._analyze_breakout(current_price, prices, highs, lows, atr, volatility)
        elif strategy == TradingStrategy.MEAN_REVERSION:
            return self._analyze_mean_reversion(current_price, prices, highs, lows, atr, volatility)
        elif strategy == TradingStrategy.GRID:
            return self._analyze_grid(current_price, prices, highs, lows, atr, volatility)
        elif strategy == TradingStrategy.SWING:
            return self._analyze_swing(current_price, prices, highs, lows, volumes, atr, volatility)
        else:
            return self._create_hold_signal(strategy, current_price, atr, volatility)
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. SCALPING - Precision Probability
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_scalping(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        atr: float,
        volatility: float,
        bid_volume: float = None,
        ask_volume: float = None,
        spread: float = None
    ) -> TradeSignal:
        """
        SCALPING - Hochfrequenz-Trading
        
        Logik:
        - Order Flow Imbalance (OFI): Kauf-/Verkaufs-Order Überhang
        - Relative Spread Strength (RSS): Spread vs. erwarteter Gewinn
        - Micro-Momentum: Preissteigung im 5-Sekunden-Bereich
        
        SL: 0.5 × ATR (1min) oder unter letztem Tief
        TP: 1.5 × Spread oder 1:2 Ratio
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 20:
            return self._create_hold_signal(TradingStrategy.SCALPING, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. ORDER FLOW IMBALANCE (OFI)
        # Wenn keine echten Order-Daten, simulieren wir mit Preis-Momentum
        if bid_volume is not None and ask_volume is not None:
            total_volume = bid_volume + ask_volume
            ofi = bid_volume / total_volume if total_volume > 0 else 0.5
        else:
            # Simuliere OFI aus Preis-Momentum
            momentum_5 = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 and prices[-5] > 0 else 0
            ofi = 0.5 + (momentum_5 / 2)  # Normalisiere auf 0-1
            ofi = max(0, min(1, ofi))
        
        # 2. RELATIVE SPREAD STRENGTH (RSS)
        # Spread sollte < 10% des erwarteten Gewinns sein
        if spread is None:
            spread = atr * 0.1  # Schätze Spread als 10% des ATR
        
        expected_profit = atr * 0.5  # Erwarteter Gewinn = 0.5 ATR
        rss = 1 - (spread / expected_profit) if expected_profit > 0 else 0
        rss = max(0, min(1, rss))
        
        # 3. MICRO-MOMENTUM (letzte 3-5 Ticks)
        micro_momentum = 0
        if len(prices) >= 5:
            micro_momentum = (prices[-1] - prices[-3]) / prices[-3] * 100 if prices[-3] > 0 else 0
        
        # 4. STOCHASTIK für Überkauft/Überverkauft
        stoch_k, stoch_d = self._calculate_stochastic(prices, highs, lows, 14, 3)
        
        # 5. EMA CROSSOVER (9/21)
        ema_9 = self._calculate_ema(prices, 9)
        ema_21 = self._calculate_ema(prices, 21)
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG Signal
        if ofi > 0.6 and stoch_k < 30:  # Kaufüberhang + überverkauft
            signal = 'BUY'
            confidence = 50
            reasons.append(f"Order Flow bullish (OFI={ofi:.2f})")
            reasons.append(f"Stochastik überverkauft (K={stoch_k:.1f})")
            
            if ema_9 > ema_21:
                confidence += 15
                reasons.append("EMA 9 > EMA 21 (Aufwärtstrend)")
            
            if micro_momentum > 0.05:
                confidence += 10
                reasons.append(f"Positives Micro-Momentum ({micro_momentum:.2f}%)")
            
            if rss > 0.8:
                confidence += 10
                reasons.append("Günstiger Spread")
        
        # SHORT Signal
        elif ofi < 0.4 and stoch_k > 70:  # Verkaufsüberhang + überkauft
            signal = 'SELL'
            confidence = 50
            reasons.append(f"Order Flow bearish (OFI={ofi:.2f})")
            reasons.append(f"Stochastik überkauft (K={stoch_k:.1f})")
            
            if ema_9 < ema_21:
                confidence += 15
                reasons.append("EMA 9 < EMA 21 (Abwärtstrend)")
            
            if micro_momentum < -0.05:
                confidence += 10
                reasons.append(f"Negatives Micro-Momentum ({micro_momentum:.2f}%)")
            
            if rss > 0.8:
                confidence += 10
                reasons.append("Günstiger Spread")
        
        # Volatilitäts-Penalty
        if volatility > 1.5:
            confidence -= 15
            reasons.append(f"⚠️ Hohe Volatilität ({volatility:.2f}%)")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP BERECHNUNG
        # ═══════════════════════════════════════════════════════════════
        
        # SL: 0.5 × ATR oder unter letztem lokalen Minimum
        sl_atr = atr * 0.5
        local_min = min(lows[-5:]) if len(lows) >= 5 else current_price * 0.998
        local_max = max(highs[-5:]) if len(highs) >= 5 else current_price * 1.002
        
        if signal == 'BUY':
            stop_loss = min(current_price - sl_atr, local_min - (atr * 0.1))
            take_profit = current_price + (current_price - stop_loss) * 2  # 1:2 Ratio
        elif signal == 'SELL':
            stop_loss = max(current_price + sl_atr, local_max + (atr * 0.1))
            take_profit = current_price - (stop_loss - current_price) * 2  # 1:2 Ratio
        else:
            stop_loss = current_price * 0.998
            take_profit = current_price * 1.002
        
        # CRV basierend auf Konfidenz
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.SCALPING,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,  # Kein Trailing bei Scalping
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'ofi': ofi,
                'rss': rss,
                'micro_momentum': micro_momentum,
                'stochastic_k': stoch_k,
                'stochastic_d': stoch_d,
                'ema_9': ema_9,
                'ema_21': ema_21,
                'spread': spread
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 2. DAY TRADING - VWAP-basiert
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_day_trading(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        DAY TRADING - Intraday Trends
        
        Logik:
        - VWAP als Anker (Kurs über/unter Durchschnitt)
        - ATR für SL-Berechnung
        - Volume Profile für TP
        
        SL: 1.0 × ATR
        TP: Nächster signifikanter Volumen-Knoten
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 50:
            return self._create_hold_signal(TradingStrategy.DAY_TRADING, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. VWAP BERECHNUNG
        if volumes and len(volumes) == len(prices):
            vwap = self._calculate_vwap(prices, volumes)
        else:
            vwap = self._calculate_sma(prices, 20)  # Fallback zu SMA
        
        # 2. Abstand zum VWAP (wie weit entfernt?)
        vwap_distance = (current_price - vwap) / vwap * 100 if vwap > 0 else 0
        
        # 3. RSI für Bestätigung
        rsi = self._calculate_rsi(prices, 14)
        
        # 4. EMA 20 als Trend-Filter
        ema_20 = self._calculate_ema(prices, 20)
        ema_50 = self._calculate_ema(prices, 50)
        trend_bullish = ema_20 > ema_50
        
        # 5. Volume-Analyse
        avg_volume = sum(volumes[-20:]) / 20 if volumes and len(volumes) >= 20 else 1
        current_volume = volumes[-1] if volumes else 1
        volume_surge = current_volume > avg_volume * 1.5
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG: Preis unter VWAP + RSI überverkauft + bullisher Trend
        if vwap_distance < -0.5 and rsi < 40 and trend_bullish:
            signal = 'BUY'
            confidence = 55
            reasons.append(f"Preis {abs(vwap_distance):.2f}% unter VWAP (Mean Reversion)")
            reasons.append(f"RSI überverkauft ({rsi:.1f})")
            
            if volume_surge:
                confidence += 15
                reasons.append("Volume-Surge bestätigt Signal")
            
            if ema_20 > ema_50:
                confidence += 10
                reasons.append("Aufwärtstrend (EMA 20 > 50)")
        
        # SHORT: Preis über VWAP + RSI überkauft + bearisher Trend
        elif vwap_distance > 0.5 and rsi > 60 and not trend_bullish:
            signal = 'SELL'
            confidence = 55
            reasons.append(f"Preis {vwap_distance:.2f}% über VWAP (Mean Reversion)")
            reasons.append(f"RSI überkauft ({rsi:.1f})")
            
            if volume_surge:
                confidence += 15
                reasons.append("Volume-Surge bestätigt Signal")
            
            if ema_20 < ema_50:
                confidence += 10
                reasons.append("Abwärtstrend (EMA 20 < 50)")
        
        # Breakout über VWAP (Trend-Following)
        elif vwap_distance > 0.3 and rsi > 50 and trend_bullish and volume_surge:
            signal = 'BUY'
            confidence = 60
            reasons.append(f"Breakout über VWAP (+{vwap_distance:.2f}%)")
            reasons.append("Volume bestätigt Breakout")
        
        elif vwap_distance < -0.3 and rsi < 50 and not trend_bullish and volume_surge:
            signal = 'SELL'
            confidence = 60
            reasons.append(f"Breakout unter VWAP ({vwap_distance:.2f}%)")
            reasons.append("Volume bestätigt Breakout")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP BERECHNUNG - 1.0 × ATR für SL
        # ═══════════════════════════════════════════════════════════════
        
        sl_distance = atr * 1.0
        
        if signal == 'BUY':
            stop_loss = current_price - sl_distance
            # TP: Zurück zum VWAP oder 2x SL
            tp_to_vwap = vwap if vwap > current_price else current_price + (sl_distance * 2)
            take_profit = max(tp_to_vwap, current_price + (sl_distance * 2))
        elif signal == 'SELL':
            stop_loss = current_price + sl_distance
            tp_to_vwap = vwap if vwap < current_price else current_price - (sl_distance * 2)
            take_profit = min(tp_to_vwap, current_price - (sl_distance * 2))
        else:
            stop_loss = current_price - sl_distance
            take_profit = current_price + sl_distance
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.DAY_TRADING,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'vwap': vwap,
                'vwap_distance': vwap_distance,
                'rsi': rsi,
                'ema_20': ema_20,
                'ema_50': ema_50,
                'volume_surge': volume_surge,
                'avg_volume': avg_volume
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 3. MOMENTUM - Trend-Stärke mit Trailing Stop
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_momentum(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        MOMENTUM - Trend-Stärke-Trading
        
        Logik:
        - RSI-Steigung + Volumen-Peak
        - Korrelation mit Sektor (vereinfacht: eigenes Momentum)
        
        SL: TRAILING! Zieht nach bei +1%
        TP: Offen bis MACD-Histogramm abnimmt
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 50:
            return self._create_hold_signal(TradingStrategy.MOMENTUM, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. RSI und RSI-STEIGUNG
        rsi = self._calculate_rsi(prices, 14)
        rsi_prev = self._calculate_rsi(prices[:-5], 14) if len(prices) > 19 else rsi
        rsi_slope = rsi - rsi_prev  # Positive = steigend
        
        # 2. MACD-HISTOGRAMM
        macd_line, signal_line, histogram = self._calculate_macd_full(prices)
        macd_hist_prev = self._calculate_macd_full(prices[:-3])[2] if len(prices) > 30 else histogram
        histogram_increasing = histogram > macd_hist_prev
        
        # 3. ADX (Trend-Stärke) - vereinfacht
        adx = self._calculate_adx(prices, highs, lows, 14)
        strong_trend = adx > 25
        
        # 4. Momentum (Rate of Change)
        roc_10 = ((prices[-1] - prices[-10]) / prices[-10] * 100) if len(prices) >= 10 and prices[-10] > 0 else 0
        
        # 5. Volume-Bestätigung
        avg_volume = sum(volumes[-20:]) / 20 if volumes and len(volumes) >= 20 else 1
        volume_peak = volumes[-1] > avg_volume * 1.3 if volumes else False
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG: Starkes bullishes Momentum
        if rsi > 50 and rsi < 75 and rsi_slope > 0 and histogram > 0 and histogram_increasing:
            signal = 'BUY'
            confidence = 55
            reasons.append(f"RSI steigend ({rsi:.1f}, Slope: +{rsi_slope:.1f})")
            reasons.append(f"MACD-Histogramm positiv und steigend ({histogram:.4f})")
            
            if strong_trend:
                confidence += 15
                reasons.append(f"Starker Trend (ADX={adx:.1f})")
            
            if volume_peak:
                confidence += 10
                reasons.append("Volumen-Peak bestätigt Momentum")
            
            if roc_10 > 1.0:
                confidence += 10
                reasons.append(f"Starke 10-Perioden-Bewegung (+{roc_10:.2f}%)")
        
        # SHORT: Starkes bearishes Momentum
        elif rsi < 50 and rsi > 25 and rsi_slope < 0 and histogram < 0 and not histogram_increasing:
            signal = 'SELL'
            confidence = 55
            reasons.append(f"RSI fallend ({rsi:.1f}, Slope: {rsi_slope:.1f})")
            reasons.append(f"MACD-Histogramm negativ und fallend ({histogram:.4f})")
            
            if strong_trend:
                confidence += 15
                reasons.append(f"Starker Trend (ADX={adx:.1f})")
            
            if volume_peak:
                confidence += 10
                reasons.append("Volumen-Peak bestätigt Momentum")
            
            if roc_10 < -1.0:
                confidence += 10
                reasons.append(f"Starke 10-Perioden-Bewegung ({roc_10:.2f}%)")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP - TRAILING STOP!
        # ═══════════════════════════════════════════════════════════════
        
        # Initial SL: 1.5 × ATR
        sl_distance = atr * 1.5
        
        if signal == 'BUY':
            stop_loss = current_price - sl_distance
            # TP: Offen (wir setzen es auf 3x SL, aber Trailing übernimmt)
            take_profit = current_price + (sl_distance * 3)
        elif signal == 'SELL':
            stop_loss = current_price + sl_distance
            take_profit = current_price - (sl_distance * 3)
        else:
            stop_loss = current_price - sl_distance
            take_profit = current_price + sl_distance
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.MOMENTUM,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=True,  # WICHTIG: Trailing Stop aktiviert!
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'rsi': rsi,
                'rsi_slope': rsi_slope,
                'macd_histogram': histogram,
                'histogram_increasing': histogram_increasing,
                'adx': adx,
                'roc_10': roc_10,
                'volume_peak': volume_peak
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 4. BREAKOUT - Ausbruchs-Trading
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_breakout(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        BREAKOUT - Ausbruchs-Trading
        
        Logik:
        - Konsolidierungsdauer messen
        - Je länger Seitwärtsphase, desto stärker der Move
        
        SL: Knapp innerhalb der alten Range (False-Breakout-Schutz)
        TP: 200% der Range-Breite
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 50:
            return self._create_hold_signal(TradingStrategy.BREAKOUT, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. RANGE-ERKENNUNG (letzte 20-50 Perioden)
        lookback = 30
        range_high = max(highs[-lookback:]) if len(highs) >= lookback else max(highs)
        range_low = min(lows[-lookback:]) if len(lows) >= lookback else min(lows)
        range_width = range_high - range_low
        range_percent = (range_width / range_low * 100) if range_low > 0 else 0
        
        # 2. KONSOLIDIERUNGSDAUER (wie viele Perioden in der Range?)
        consolidation_periods = 0
        for i in range(-1, -min(50, len(prices)), -1):
            if range_low <= prices[i] <= range_high:
                consolidation_periods += 1
            else:
                break
        
        # 3. BREAKOUT ERKENNUNG
        breakout_up = current_price > range_high
        breakout_down = current_price < range_low
        
        # 4. Volumen bei Breakout (simuliert mit Volatilität)
        breakout_strength = abs(current_price - (range_high if breakout_up else range_low)) / atr if atr > 0 else 0
        
        # 5. False-Breakout-Filter: Preis muss deutlich außerhalb sein
        min_breakout_distance = atr * 0.3
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG: Breakout nach oben
        if breakout_up and (current_price - range_high) > min_breakout_distance:
            signal = 'BUY'
            confidence = 50
            reasons.append(f"Breakout über Range-High ({range_high:.2f})")
            
            # Je länger die Konsolidierung, desto besser
            if consolidation_periods > 20:
                confidence += 20
                reasons.append(f"Lange Konsolidierung ({consolidation_periods} Perioden)")
            elif consolidation_periods > 10:
                confidence += 10
                reasons.append(f"Mittlere Konsolidierung ({consolidation_periods} Perioden)")
            
            if breakout_strength > 0.5:
                confidence += 10
                reasons.append(f"Starker Breakout (Stärke: {breakout_strength:.2f})")
        
        # SHORT: Breakout nach unten
        elif breakout_down and (range_low - current_price) > min_breakout_distance:
            signal = 'SELL'
            confidence = 50
            reasons.append(f"Breakout unter Range-Low ({range_low:.2f})")
            
            if consolidation_periods > 20:
                confidence += 20
                reasons.append(f"Lange Konsolidierung ({consolidation_periods} Perioden)")
            elif consolidation_periods > 10:
                confidence += 10
                reasons.append(f"Mittlere Konsolidierung ({consolidation_periods} Perioden)")
            
            if breakout_strength > 0.5:
                confidence += 10
                reasons.append(f"Starker Breakout (Stärke: {breakout_strength:.2f})")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP - 200% Range als TP!
        # ═══════════════════════════════════════════════════════════════
        
        if signal == 'BUY':
            # SL: Knapp innerhalb der Range (False-Breakout-Schutz)
            stop_loss = range_high - (range_width * 0.2)
            # TP: 200% der Range-Breite
            take_profit = current_price + (range_width * 2.0)
        elif signal == 'SELL':
            stop_loss = range_low + (range_width * 0.2)
            take_profit = current_price - (range_width * 2.0)
        else:
            stop_loss = current_price - atr
            take_profit = current_price + atr
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.BREAKOUT,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'range_high': range_high,
                'range_low': range_low,
                'range_width': range_width,
                'range_percent': range_percent,
                'consolidation_periods': consolidation_periods,
                'breakout_up': breakout_up,
                'breakout_down': breakout_down,
                'breakout_strength': breakout_strength
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 5. MEAN REVERSION - Rückkehr zum Mittelwert
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_mean_reversion(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        MEAN REVERSION - Rückkehr zum Mittelwert
        
        Logik:
        - Bollinger Bands: Messung der Standardabweichung
        - Signal wenn Kurs > 2.5 Standardabweichungen vom Mittelwert
        
        TP: Gleitender Durchschnitt (EMA 20)
        SL: Jüngstes Extremhoch/-tief + Puffer
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 30:
            return self._create_hold_signal(TradingStrategy.MEAN_REVERSION, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. BOLLINGER BANDS (20, 2.0)
        upper_band, middle_band, lower_band = self._calculate_bollinger_bands(prices, 20, 2.0)
        
        # 2. Erweiterte Bands (2.5 StdDev für starke Signale)
        upper_extreme, _, lower_extreme = self._calculate_bollinger_bands(prices, 20, 2.5)
        
        # 3. Standardabweichung
        std_dev = self._calculate_std_dev(prices[-20:])
        
        # 4. Abstand zum Mittelwert in Standardabweichungen
        distance_from_mean = (current_price - middle_band) / std_dev if std_dev > 0 else 0
        
        # 5. RSI für Bestätigung
        rsi = self._calculate_rsi(prices, 14)
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG: Preis unter unterem Band (überverkauft)
        if current_price < lower_band and distance_from_mean < -2.0:
            signal = 'BUY'
            confidence = 55
            reasons.append(f"Preis unter Bollinger Lower Band ({lower_band:.2f})")
            reasons.append(f"Abstand zum Mittelwert: {distance_from_mean:.2f} StdDev")
            
            if distance_from_mean < -2.5:
                confidence += 15
                reasons.append("Extrem überverkauft (> 2.5 StdDev)")
            
            if rsi < 30:
                confidence += 15
                reasons.append(f"RSI bestätigt Überverkauft ({rsi:.1f})")
            elif rsi < 40:
                confidence += 5
                reasons.append(f"RSI unterstützt Signal ({rsi:.1f})")
        
        # SHORT: Preis über oberem Band (überkauft)
        elif current_price > upper_band and distance_from_mean > 2.0:
            signal = 'SELL'
            confidence = 55
            reasons.append(f"Preis über Bollinger Upper Band ({upper_band:.2f})")
            reasons.append(f"Abstand zum Mittelwert: +{distance_from_mean:.2f} StdDev")
            
            if distance_from_mean > 2.5:
                confidence += 15
                reasons.append("Extrem überkauft (> 2.5 StdDev)")
            
            if rsi > 70:
                confidence += 15
                reasons.append(f"RSI bestätigt Überkauft ({rsi:.1f})")
            elif rsi > 60:
                confidence += 5
                reasons.append(f"RSI unterstützt Signal ({rsi:.1f})")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP - TP = EMA 20 (Mittelwert), SL = Extrempunkt + Puffer
        # ═══════════════════════════════════════════════════════════════
        
        ema_20 = self._calculate_ema(prices, 20)
        recent_high = max(highs[-10:]) if len(highs) >= 10 else current_price * 1.02
        recent_low = min(lows[-10:]) if len(lows) >= 10 else current_price * 0.98
        
        if signal == 'BUY':
            # TP: EMA 20 (Mittelwert)
            take_profit = ema_20
            # SL: Unter dem jüngsten Tief + Puffer
            stop_loss = recent_low - (atr * 0.3)
        elif signal == 'SELL':
            take_profit = ema_20
            stop_loss = recent_high + (atr * 0.3)
        else:
            stop_loss = current_price - atr
            take_profit = current_price + atr
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.MEAN_REVERSION,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'upper_band': upper_band,
                'middle_band': middle_band,
                'lower_band': lower_band,
                'distance_from_mean': distance_from_mean,
                'std_dev': std_dev,
                'rsi': rsi,
                'ema_20': ema_20
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 6. GRID TRADING - Seitwärtsphasen
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_grid(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        GRID TRADING - Seitwärtsphasen
        
        Logik:
        - Average Daily Range (ADR) berechnen
        - Grid-Abstände an Volatilität anpassen
        - Hohe Volatilität = weitere Abstände
        
        SL/TP: Grid-Level-basiert
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 30:
            return self._create_hold_signal(TradingStrategy.GRID, current_price, atr, volatility, "Nicht genug Daten")
        
        # 1. ADR (Average Daily Range) - vereinfacht über ATR
        adr = atr * 1.5  # ADR ist typischerweise 1.5x ATR
        
        # 2. Grid-Abstände basierend auf Volatilität
        # Hohe Volatilität = weitere Abstände
        if volatility > 2.0:
            grid_spacing = adr * 0.4  # Weite Abstände
            grid_type = "wide"
        elif volatility > 1.0:
            grid_spacing = adr * 0.25  # Normale Abstände
            grid_type = "normal"
        else:
            grid_spacing = adr * 0.15  # Enge Abstände
            grid_type = "tight"
        
        # 3. Range-Erkennung (ist der Markt seitwärts?)
        range_high = max(highs[-20:]) if len(highs) >= 20 else current_price * 1.02
        range_low = min(lows[-20:]) if len(lows) >= 20 else current_price * 0.98
        range_width = range_high - range_low
        
        # Seitwärtsphase wenn Range < 2 × ADR
        is_ranging = range_width < (adr * 2)
        
        # 4. ADX für Trend-Stärke
        adx = self._calculate_adx(prices, highs, lows, 14)
        no_strong_trend = adx < 25
        
        # 5. Position im Grid bestimmen
        grid_levels = []
        for i in range(-5, 6):
            level = current_price + (i * grid_spacing)
            grid_levels.append(level)
        
        # Nächstes Grid-Level
        nearest_buy_level = current_price - grid_spacing
        nearest_sell_level = current_price + grid_spacing
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK - Grid handelt IMMER in Seitwärtsphasen
        # ═══════════════════════════════════════════════════════════════
        
        if is_ranging and no_strong_trend:
            # In Seitwärtsphase: Kaufe bei Grid-Low, Verkaufe bei Grid-High
            distance_to_low = current_price - range_low
            distance_to_high = range_high - current_price
            
            # Nahe am unteren Rand = BUY
            if distance_to_low < range_width * 0.3:
                signal = 'BUY'
                confidence = 60
                reasons.append(f"Nahe Grid-Low ({range_low:.2f})")
                reasons.append(f"Seitwärtsphase erkannt (Range: {range_width:.2f})")
                
                if no_strong_trend:
                    confidence += 10
                    reasons.append(f"Kein starker Trend (ADX={adx:.1f})")
            
            # Nahe am oberen Rand = SELL
            elif distance_to_high < range_width * 0.3:
                signal = 'SELL'
                confidence = 60
                reasons.append(f"Nahe Grid-High ({range_high:.2f})")
                reasons.append(f"Seitwärtsphase erkannt (Range: {range_width:.2f})")
                
                if no_strong_trend:
                    confidence += 10
                    reasons.append(f"Kein starker Trend (ADX={adx:.1f})")
        else:
            reasons.append("Kein Grid-Signal: Markt nicht in Seitwärtsphase")
            if not is_ranging:
                reasons.append(f"Range zu groß ({range_width:.2f} > {adr*2:.2f})")
            if not no_strong_trend:
                reasons.append(f"Trend zu stark (ADX={adx:.1f})")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP - Grid-basiert
        # ═══════════════════════════════════════════════════════════════
        
        if signal == 'BUY':
            stop_loss = range_low - grid_spacing
            take_profit = current_price + grid_spacing * 2
        elif signal == 'SELL':
            stop_loss = range_high + grid_spacing
            take_profit = current_price - grid_spacing * 2
        else:
            stop_loss = current_price - grid_spacing
            take_profit = current_price + grid_spacing
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.GRID,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'adr': adr,
                'grid_spacing': grid_spacing,
                'grid_type': grid_type,
                'range_high': range_high,
                'range_low': range_low,
                'is_ranging': is_ranging,
                'adx': adx,
                'grid_levels': grid_levels[:5]  # Nur erste 5 Level
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # 7. SWING TRADING - Mehrtägig mit Fibonacci
    # ═══════════════════════════════════════════════════════════════════
    
    def _analyze_swing(
        self,
        current_price: float,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        atr: float,
        volatility: float
    ) -> TradeSignal:
        """
        SWING TRADING - Mehrtägige Positionen
        
        Logik:
        - Multi-Timeframe-Struktur (D1 und H4 simuliert)
        - Fundamentale Datenkombinationen
        
        SL: Unter letztem Swing-Low
        TP: Fibonacci Extension 1.618 Level
        """
        reasons = []
        confidence = 0
        signal = 'HOLD'
        
        if len(prices) < 100:
            return self._create_hold_signal(TradingStrategy.SWING, current_price, atr, volatility, "Nicht genug Daten (min 100)")
        
        # 1. SWING HIGH/LOW ERKENNUNG
        swing_high, swing_low = self._find_swing_points(prices, highs, lows)
        swing_range = swing_high - swing_low
        
        # 2. FIBONACCI LEVELS (von Swing Low zu Swing High)
        fib_236 = swing_low + (swing_range * 0.236)
        fib_382 = swing_low + (swing_range * 0.382)
        fib_500 = swing_low + (swing_range * 0.500)
        fib_618 = swing_low + (swing_range * 0.618)
        
        # FIBONACCI EXTENSION für TP
        fib_ext_1272 = swing_high + (swing_range * 0.272)  # 127.2%
        fib_ext_1618 = swing_high + (swing_range * 0.618)  # 161.8%
        
        # 3. GOLDEN CROSS / DEATH CROSS (SMA 50/200)
        sma_50 = self._calculate_sma(prices, 50)
        sma_200 = self._calculate_sma(prices, 200) if len(prices) >= 200 else self._calculate_sma(prices, 100)
        
        golden_cross = sma_50 > sma_200
        
        # 4. MACD für Trend-Bestätigung
        macd_line, signal_line, histogram = self._calculate_macd_full(prices)
        macd_bullish = macd_line > signal_line
        
        # 5. Preis nahe Fibonacci-Level?
        near_fib_618 = abs(current_price - fib_618) / fib_618 < 0.02 if fib_618 > 0 else False
        near_fib_382 = abs(current_price - fib_382) / fib_382 < 0.02 if fib_382 > 0 else False
        
        # ═══════════════════════════════════════════════════════════════
        # SIGNAL-LOGIK
        # ═══════════════════════════════════════════════════════════════
        
        # LONG: Pullback zu Fibonacci + bullisher Trend
        if golden_cross and (near_fib_618 or near_fib_382) and current_price > swing_low:
            signal = 'BUY'
            confidence = 55
            
            if near_fib_618:
                reasons.append(f"Pullback zu Fib 61.8% ({fib_618:.2f})")
                confidence += 10
            elif near_fib_382:
                reasons.append(f"Pullback zu Fib 38.2% ({fib_382:.2f})")
                confidence += 5
            
            reasons.append(f"Golden Cross (SMA 50 > 200)")
            
            if macd_bullish:
                confidence += 15
                reasons.append("MACD bestätigt bullischen Trend")
        
        # Golden Cross ohne Fibonacci-Pullback
        elif golden_cross and macd_bullish and current_price > sma_50:
            signal = 'BUY'
            confidence = 50
            reasons.append("Golden Cross aktiv")
            reasons.append("Preis über SMA 50")
            
            if histogram > 0:
                confidence += 10
                reasons.append("MACD-Histogramm positiv")
        
        # SHORT: Death Cross + bearisher Trend
        elif not golden_cross and not macd_bullish and current_price < sma_50:
            signal = 'SELL'
            confidence = 55
            reasons.append("Death Cross (SMA 50 < 200)")
            reasons.append("Preis unter SMA 50")
            
            if histogram < 0:
                confidence += 10
                reasons.append("MACD-Histogramm negativ")
        
        confidence = max(0, min(95, confidence))
        
        # ═══════════════════════════════════════════════════════════════
        # SL/TP - Fibonacci Extension 1.618 als TP!
        # ═══════════════════════════════════════════════════════════════
        
        if signal == 'BUY':
            # SL: Unter letztem Swing-Low
            stop_loss = swing_low - (atr * 0.5)
            # TP: Fibonacci Extension 1.618
            take_profit = fib_ext_1618
        elif signal == 'SELL':
            # SL: Über letztem Swing-High
            stop_loss = swing_high + (atr * 0.5)
            # TP: Fibonacci Extension nach unten
            take_profit = swing_low - (swing_range * 0.618)
        else:
            stop_loss = current_price - atr * 2
            take_profit = current_price + atr * 2
        
        crv = self._get_crv_for_confidence(confidence)
        
        return TradeSignal(
            strategy=TradingStrategy.SWING,
            signal=signal,
            confidence=confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=False,
            crv=crv,
            atr=atr,
            volatility=volatility,
            reasons=reasons,
            indicators={
                'swing_high': swing_high,
                'swing_low': swing_low,
                'fib_382': fib_382,
                'fib_500': fib_500,
                'fib_618': fib_618,
                'fib_ext_1618': fib_ext_1618,
                'sma_50': sma_50,
                'sma_200': sma_200,
                'golden_cross': golden_cross,
                'macd_histogram': histogram
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # HILFSMETHODEN
    # ═══════════════════════════════════════════════════════════════════
    
    def _create_hold_signal(
        self,
        strategy: TradingStrategy,
        current_price: float,
        atr: float,
        volatility: float,
        reason: str = "Kein Signal"
    ) -> TradeSignal:
        """Erstellt ein HOLD-Signal"""
        return TradeSignal(
            strategy=strategy,
            signal='HOLD',
            confidence=0,
            entry_price=current_price,
            stop_loss=current_price - atr,
            take_profit=current_price + atr,
            trailing_stop=False,
            crv=1.0,
            atr=atr,
            volatility=volatility,
            reasons=[reason],
            indicators={}
        )
    
    def _get_crv_for_confidence(self, confidence: float) -> float:
        """Bestimmt CRV basierend auf Konfidenz"""
        if confidence >= 80:
            return self.CRV_MAPPING['aggressive']  # 1:3
        elif confidence >= 65:
            return self.CRV_MAPPING['standard']    # 1:2
        else:
            return self.CRV_MAPPING['defensive']   # 1:1.5
    
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
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Berechnet prozentuale Volatilität"""
        if len(prices) < 2:
            return 0.0
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices)) if prices[i-1] > 0]
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5
    
    def _calculate_stochastic(self, prices: List[float], highs: List[float], lows: List[float], k_period: int = 14, d_period: int = 3) -> Tuple[float, float]:
        """Berechnet Stochastik-Oszillator"""
        if len(prices) < k_period:
            return 50.0, 50.0
        
        highest_high = max(highs[-k_period:]) if len(highs) >= k_period else max(prices[-k_period:])
        lowest_low = min(lows[-k_period:]) if len(lows) >= k_period else min(prices[-k_period:])
        
        if highest_high == lowest_low:
            return 50.0, 50.0
        
        stoch_k = ((prices[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        stoch_d = stoch_k * 0.9  # Vereinfachte Glättung
        
        return stoch_k, stoch_d
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Berechnet Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_sma(self, prices: List[float], period: int) -> float:
        """Berechnet Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Berechnet RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd_full(self, prices: List[float]) -> Tuple[float, float, float]:
        """Berechnet MACD Line, Signal Line und Histogram"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        signal_line = macd_line * 0.85
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def _calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        """Berechnet Volume Weighted Average Price"""
        if not prices or not volumes or len(prices) != len(volumes):
            return prices[-1] if prices else 0
        
        total_pv = sum(p * v for p, v in zip(prices, volumes))
        total_volume = sum(volumes)
        
        return total_pv / total_volume if total_volume > 0 else prices[-1]
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Berechnet Bollinger Bands"""
        if len(prices) < period:
            avg = prices[-1] if prices else 0
            return avg * 1.02, avg, avg * 0.98
        
        recent_prices = prices[-period:]
        middle = sum(recent_prices) / period
        
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = variance ** 0.5
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def _calculate_std_dev(self, prices: List[float]) -> float:
        """Berechnet Standardabweichung"""
        if len(prices) < 2:
            return 0.0
        
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return variance ** 0.5
    
    def _calculate_adx(self, prices: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        """Berechnet ADX (vereinfacht)"""
        if len(prices) < period + 1:
            return 25.0  # Neutraler Wert
        
        # Vereinfachte ADX-Berechnung basierend auf Preisbewegung
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_change = sum(price_changes[-period:]) / period if price_changes else 0
        avg_price = sum(prices[-period:]) / period
        
        # ADX als Prozent der durchschnittlichen Bewegung
        adx = (avg_change / avg_price * 100 * 10) if avg_price > 0 else 25
        return min(100, max(0, adx))
    
    def _find_swing_points(self, prices: List[float], highs: List[float], lows: List[float]) -> Tuple[float, float]:
        """Findet Swing-High und Swing-Low"""
        lookback = min(50, len(prices))
        
        swing_high = max(highs[-lookback:]) if len(highs) >= lookback else max(prices[-lookback:])
        swing_low = min(lows[-lookback:]) if len(lows) >= lookback else min(prices[-lookback:])
        
        return swing_high, swing_low


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON INSTANZ
# ═══════════════════════════════════════════════════════════════════════

advanced_trading = AdvancedTradingLogic()
