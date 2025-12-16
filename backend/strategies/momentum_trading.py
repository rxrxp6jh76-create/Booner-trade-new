"""
Momentum Trading Strategy

Folgt starken Trends und Momentum.
Bestens für Trending Markets.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MomentumTradingStrategy:
    """
    Momentum Trading Strategie
    
    Logik:
    1. Berechne Momentum (Rate of Change)
    2. Prüfe Trend mit Moving Averages (50, 200)
    3. Trade in Richtung des Momentum
    4. Exit wenn Momentum schwächer wird
    """
    
    def __init__(self, settings: Dict):
        self.name = "momentum"
        self.display_name = "🚀 Momentum Trading"
        self.settings = settings
        
        # Parameter aus Settings oder Defaults
        self.enabled = settings.get('momentum_enabled', False)
        self.momentum_period = settings.get('momentum_period', 14)
        self.momentum_threshold = settings.get('momentum_threshold', 0.5)  # 0.5%
        self.ma_fast_period = settings.get('momentum_ma_fast', 50)
        self.ma_slow_period = settings.get('momentum_ma_slow', 200)
        self.min_confidence = settings.get('momentum_min_confidence', 0.7)
        self.stop_loss_percent = settings.get('momentum_stop_loss_percent', 2.5)
        self.take_profit_percent = settings.get('momentum_take_profit_percent', 5.0)
        self.max_positions = settings.get('momentum_max_positions', 8)
        self.risk_per_trade_percent = settings.get('momentum_risk_per_trade_percent', 2.0)
        
        logger.info(f"🎯 Momentum Trading Strategy initialized: enabled={self.enabled}")
    
    def calculate_momentum(self, prices: List[float], period: int = None) -> float:
        """
        Berechne Momentum (Rate of Change)
        
        Args:
            prices: Liste der letzten Preise
            period: Lookback Periode
            
        Returns:
            Momentum als Prozent
        """
        if period is None:
            period = self.momentum_period
        
        if len(prices) < period + 1:
            return 0.0
        
        current_price = prices[-1]
        past_price = prices[-period-1]
        
        if past_price == 0:
            return 0.0
        
        momentum = ((current_price - past_price) / past_price) * 100
        return momentum
    
    def calculate_ma(self, prices: List[float], period: int) -> float:
        """
        Berechne Simple Moving Average
        
        Args:
            prices: Liste der letzten Preise
            period: MA Periode
            
        Returns:
            MA Wert
        """
        if len(prices) < period:
            return 0.0
        
        recent_prices = prices[-period:]
        return sum(recent_prices) / len(recent_prices)
    
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
            
            # Brauchen genug Daten für slow MA
            if len(price_history) < self.ma_slow_period:
                logger.debug(f"Momentum: Not enough data for {symbol}")
                return None
            
            # Berechne Indicators
            momentum = self.calculate_momentum(price_history)
            ma_fast = self.calculate_ma(price_history, self.ma_fast_period)
            ma_slow = self.calculate_ma(price_history, self.ma_slow_period)
            
            # Signal-Logik
            signal = None
            confidence = 0.5
            reason = ""
            
            # BUY Signal: Positives Momentum + Fast MA > Slow MA
            if momentum > self.momentum_threshold and ma_fast > ma_slow:
                signal = 'BUY'
                # Confidence basierend auf Momentum Stärke
                confidence = min(0.95, 0.7 + (momentum / 10))  # Stärkeres Momentum = höhere Confidence
                reason = f"Positive momentum ({momentum:.2f}%) + Bullish MA crossover"
            
            # SELL Signal: Negatives Momentum + Fast MA < Slow MA
            elif momentum < -self.momentum_threshold and ma_fast < ma_slow:
                signal = 'SELL'
                confidence = min(0.95, 0.7 + (abs(momentum) / 10))
                reason = f"Negative momentum ({momentum:.2f}%) + Bearish MA crossover"
            
            # Check Min Confidence
            if signal and confidence >= self.min_confidence:
                # Berechne SL/TP
                if signal == 'BUY':
                    stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                    take_profit = current_price * (1 + self.take_profit_percent / 100)
                else:  # SELL
                    stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                    take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                logger.info(f"🚀 Momentum Signal: {signal} {symbol} @ {current_price:.2f} (Confidence: {confidence:.2%})")
                
                return {
                    'strategy': 'momentum',
                    'signal': signal,
                    'symbol': symbol,
                    'confidence': confidence,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': reason,
                    'indicators': {
                        'momentum': momentum,
                        'ma_fast': ma_fast,
                        'ma_slow': ma_slow
                    },
                    'risk_percent': self.risk_per_trade_percent,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Momentum analysis: {e}", exc_info=True)
            return None
    
    def get_settings_dict(self) -> Dict:
        """Gib aktuelle Settings zurück"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'momentum_period': self.momentum_period,
            'momentum_threshold': self.momentum_threshold,
            'ma_fast_period': self.ma_fast_period,
            'ma_slow_period': self.ma_slow_period,
            'min_confidence': self.min_confidence,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_positions': self.max_positions,
            'risk_per_trade_percent': self.risk_per_trade_percent
        }
