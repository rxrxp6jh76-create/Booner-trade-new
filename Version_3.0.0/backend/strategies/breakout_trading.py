"""
Breakout Trading Strategy

Handelt Ausbrüche aus Ranges/Konsolidierungen.
Bestens für Volatility Breakouts.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class BreakoutTradingStrategy:
    """
    Breakout Trading Strategie
    
    Logik:
    1. Finde Resistance/Support Levels (Lookback Period)
    2. Warte auf Breakout mit Volume Bestätigung
    3. Trade in Breakout-Richtung
    4. Exit bei False Breakout oder Target erreicht
    """
    
    def __init__(self, settings: Dict):
        self.name = "breakout"
        self.display_name = "💥 Breakout Trading"
        self.settings = settings
        
        # Parameter aus Settings oder Defaults
        self.enabled = settings.get('breakout_enabled', False)
        self.lookback_period = settings.get('breakout_lookback_period', 20)
        self.confirmation_bars = settings.get('breakout_confirmation_bars', 2)
        self.volume_multiplier = settings.get('breakout_volume_multiplier', 1.5)  # 1.5x durchschnitt
        self.min_confidence = settings.get('breakout_min_confidence', 0.65)
        self.stop_loss_percent = settings.get('breakout_stop_loss_percent', 2.0)
        self.take_profit_percent = settings.get('breakout_take_profit_percent', 4.0)
        self.max_positions = settings.get('breakout_max_positions', 6)
        self.risk_per_trade_percent = settings.get('breakout_risk_per_trade_percent', 1.8)
        
        logger.info(f"🎯 Breakout Trading Strategy initialized: enabled={self.enabled}")
    
    def find_resistance_support(self, prices: List[float]) -> Dict:
        """
        Finde Resistance (Hoch) und Support (Tief) Levels
        
        Args:
            prices: Liste der letzten Preise
            
        Returns:
            Dict mit resistance, support
        """
        if len(prices) < self.lookback_period:
            return {'resistance': 0, 'support': 0, 'range': 0}
        
        recent_prices = prices[-self.lookback_period:]
        resistance = max(recent_prices)
        support = min(recent_prices)
        price_range = resistance - support
        
        return {
            'resistance': resistance,
            'support': support,
            'range': price_range,
            'mid': (resistance + support) / 2
        }
    
    def calculate_avg_volume(self, volumes: List[float]) -> float:
        """
        Berechne durchschnittliches Volumen
        
        Args:
            volumes: Liste der letzten Volume-Werte
            
        Returns:
            Durchschnittliches Volumen
        """
        if not volumes or len(volumes) < self.lookback_period:
            return 0.0
        
        recent_volumes = volumes[-self.lookback_period:]
        return sum(recent_volumes) / len(recent_volumes)
    
    async def analyze_signal(self, market_data: Dict) -> Optional[Dict]:
        """
        Analysiere Market Data und generiere Trade Signal
        
        Args:
            market_data: Dict mit price_history, current_price, symbol, volume_history, etc.
            
        Returns:
            Trade Signal Dict oder None
        """
        if not self.enabled:
            return None
        
        try:
            price_history = market_data.get('price_history', [])
            current_price = market_data.get('current_price', 0)
            symbol = market_data.get('symbol', 'UNKNOWN')
            volume_history = market_data.get('volume_history', [])
            current_volume = market_data.get('current_volume', 0)
            
            if len(price_history) < self.lookback_period + self.confirmation_bars:
                logger.debug(f"Breakout: Not enough data for {symbol}")
                return None
            
            # Berechne Resistance/Support
            levels = self.find_resistance_support(price_history[:-self.confirmation_bars])  # Exkludiere letzte bars für Confirmation
            avg_volume = self.calculate_avg_volume(volume_history) if volume_history else 0
            
            # Signal-Logik
            signal = None
            confidence = 0.5
            reason = ""
            
            # BUY Signal: Breakout über Resistance
            if current_price > levels['resistance']:
                # Prüfe Confirmation: Letzten bars alle über Resistance?
                recent_prices = price_history[-self.confirmation_bars:]
                confirmed = all(p > levels['resistance'] for p in recent_prices)
                
                # Prüfe Volume (falls verfügbar)
                volume_confirmed = True
                if current_volume > 0 and avg_volume > 0:
                    volume_confirmed = current_volume >= (avg_volume * self.volume_multiplier)
                
                if confirmed and volume_confirmed:
                    signal = 'BUY'
                    # Confidence basierend auf Breakout-Stärke
                    breakout_percent = ((current_price - levels['resistance']) / levels['resistance']) * 100
                    confidence = min(0.95, 0.65 + (breakout_percent * 10))
                    reason = f"Breakout above resistance ({levels['resistance']:.2f}) with volume confirmation"
            
            # SELL Signal: Breakout unter Support
            elif current_price < levels['support']:
                # Prüfe Confirmation
                recent_prices = price_history[-self.confirmation_bars:]
                confirmed = all(p < levels['support'] for p in recent_prices)
                
                # Prüfe Volume
                volume_confirmed = True
                if current_volume > 0 and avg_volume > 0:
                    volume_confirmed = current_volume >= (avg_volume * self.volume_multiplier)
                
                if confirmed and volume_confirmed:
                    signal = 'SELL'
                    breakout_percent = ((levels['support'] - current_price) / levels['support']) * 100
                    confidence = min(0.95, 0.65 + (breakout_percent * 10))
                    reason = f"Breakout below support ({levels['support']:.2f}) with volume confirmation"
            
            # Check Min Confidence
            if signal and confidence >= self.min_confidence:
                # Berechne SL/TP
                if signal == 'BUY':
                    stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                    take_profit = current_price * (1 + self.take_profit_percent / 100)
                else:  # SELL
                    stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                    take_profit = current_price * (1 - self.take_profit_percent / 100)
                
                logger.info(f"💥 Breakout Signal: {signal} {symbol} @ {current_price:.2f} (Confidence: {confidence:.2%})")
                
                return {
                    'strategy': 'breakout',
                    'signal': signal,
                    'symbol': symbol,
                    'confidence': confidence,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': reason,
                    'indicators': {
                        'resistance': levels['resistance'],
                        'support': levels['support'],
                        'range': levels['range'],
                        'avg_volume': avg_volume,
                        'current_volume': current_volume
                    },
                    'risk_percent': self.risk_per_trade_percent,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Breakout analysis: {e}", exc_info=True)
            return None
    
    def get_settings_dict(self) -> Dict:
        """Gib aktuelle Settings zurück"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'lookback_period': self.lookback_period,
            'confirmation_bars': self.confirmation_bars,
            'volume_multiplier': self.volume_multiplier,
            'min_confidence': self.min_confidence,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'max_positions': self.max_positions,
            'risk_per_trade_percent': self.risk_per_trade_percent
        }
