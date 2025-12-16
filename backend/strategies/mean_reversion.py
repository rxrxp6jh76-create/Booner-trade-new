"""
Mean Reversion Trading Strategy

Handelt auf Rückkehr zum Mittelwert.
Bestens für Range-bound Markets.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

class MeanReversionStrategy:
    """
    Mean Reversion Strategie
    
    Logik:
    1. Berechne Bollinger Bands (20, 2.0)
    2. RSI für Überkauft/Überverkauft
    3. Trade wenn Preis außerhalb von Bands
    4. Exit wenn Preis zurück zum Mittelwert
    """
    
    def __init__(self, settings: Dict):
        self.name = "mean_reversion"
        self.display_name = "📊 Mean Reversion"
        self.settings = settings
        
        # Parameter aus Settings oder Defaults
        self.enabled = settings.get('mean_reversion_enabled', False)
        self.bb_period = settings.get('mean_reversion_bb_period', 20)
        self.bb_std_dev = settings.get('mean_reversion_bb_std_dev', 2.0)
        self.rsi_oversold = settings.get('mean_reversion_rsi_oversold', 30)
        self.rsi_overbought = settings.get('mean_reversion_rsi_overbought', 70)
        self.min_confidence = settings.get('mean_reversion_min_confidence', 0.65)
        self.stop_loss_percent = settings.get('mean_reversion_stop_loss_percent', 1.5)
        self.take_profit_percent = settings.get('mean_reversion_take_profit_percent', 2.0)
        self.max_positions = settings.get('mean_reversion_max_positions', 5)
        self.risk_per_trade_percent = settings.get('mean_reversion_risk_per_trade_percent', 1.5)
        
        logger.info(f"🎯 Mean Reversion Strategy initialized: enabled={self.enabled}")
    
    def calculate_bollinger_bands(self, prices: List[float]) -> Dict:
        """
        Berechne Bollinger Bands
        
        Args:
            prices: Liste der letzten Preise
            
        Returns:
            Dict mit upper_band, middle_band, lower_band
        """
        if len(prices) < self.bb_period:
            return {'upper': 0, 'middle': 0, 'lower': 0}
        
        # Nutze die letzten bb_period Preise
        recent_prices = prices[-self.bb_period:]
        
        # Mittelwert (SMA)
        middle = sum(recent_prices) / len(recent_prices)
        
        # Standardabweichung
        variance = sum((p - middle) ** 2 for p in recent_prices) / len(recent_prices)
        std_dev = variance ** 0.5
        
        # Bands
        upper = middle + (self.bb_std_dev * std_dev)
        lower = middle - (self.bb_std_dev * std_dev)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'std_dev': std_dev
        }
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Berechne RSI (Relative Strength Index)
        
        Args:
            prices: Liste der letzten Preise
            period: RSI Periode (Standard: 14)
            
        Returns:
            RSI Wert (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        # Preisänderungen berechnen
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Nutze die letzten period Änderungen
        recent_changes = changes[-period:]
        
        # Gains und Losses
        gains = [c if c > 0 else 0 for c in recent_changes]
        losses = [-c if c < 0 else 0 for c in recent_changes]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def analyze_signal(self, market_data: Dict) -> Optional[Dict]:
        """
        Analysiere Market Data und generiere Trade Signal
        
        Args:
            market_data: Dict mit price_history, current_price, symbol, etc.
            
        Returns:
            Trade Signal Dict oder None
        """
        if not self.enabled:
            return None
        
        try:
            price_history = market_data.get('price_history', [])
            current_price = market_data.get('current_price', 0)
            symbol = market_data.get('symbol', 'UNKNOWN')
            
            if len(price_history) < self.bb_period:
                logger.debug(f"Mean Reversion: Not enough data for {symbol}")
                return None
            
            # Berechne Indicators
            bb = self.calculate_bollinger_bands(price_history)
            rsi = self.calculate_rsi(price_history)
            
            # Signal-Logik
            signal = None
            confidence = 0.5
            reason = ""
            
            # SELL Signal: Preis über Upper Band + RSI überkauft
            if current_price > bb['upper'] and rsi > self.rsi_overbought:
                signal = 'SELL'
                # Confidence basierend auf wie weit über Band
                distance_from_band = (current_price - bb['upper']) / bb['upper']
                confidence = min(0.95, 0.65 + (distance_from_band * 100))  # Mehr Distanz = höhere Confidence
                reason = f"Price above upper BB ({bb['upper']:.2f}) + RSI overbought ({rsi:.1f})"
            
            # BUY Signal: Preis unter Lower Band + RSI überverkauft
            elif current_price < bb['lower'] and rsi < self.rsi_oversold:
                signal = 'BUY'
                # Confidence basierend auf wie weit unter Band
                distance_from_band = (bb['lower'] - current_price) / bb['lower']
                confidence = min(0.95, 0.65 + (distance_from_band * 100))
                reason = f"Price below lower BB ({bb['lower']:.2f}) + RSI oversold ({rsi:.1f})"
            
            # Check Min Confidence
            if signal and confidence >= self.min_confidence:
                # Berechne SL/TP
                if signal == 'BUY':
                    stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                    take_profit = current_price * (1 + self.take_profit_percent / 100)
                else:  # SELL
                    stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                    take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                logger.info(f"📊 Mean Reversion Signal: {signal} {symbol} @ {current_price:.2f} (Confidence: {confidence:.2%})")
                
                return {
                    'strategy': 'mean_reversion',
                    'signal': signal,
                    'symbol': symbol,
                    'confidence': confidence,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': reason,
                    'indicators': {
                        'bb_upper': bb['upper'],
                        'bb_middle': bb['middle'],
                        'bb_lower': bb['lower'],
                        'rsi': rsi
                    },
                    'risk_percent': self.risk_per_trade_percent,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Mean Reversion analysis: {e}", exc_info=True)
            return None
    
    def get_settings_dict(self) -> Dict:
        """Gib aktuelle Settings zurück"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'bb_period': self.bb_period,
            'bb_std_dev': self.bb_std_dev,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'min_confidence': self.min_confidence,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_positions': self.max_positions,
            'risk_per_trade_percent': self.risk_per_trade_percent
        }
