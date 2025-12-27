"""
Scalping Trading Strategy
Ultra-schnelle Trades mit kleinen Gewinnen (5-20 Pips)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ScalpingStrategy:
    """
    Scalping-Strategie für schnelle, kleine Gewinne
    
    Charakteristika:
    - Sehr kurze Haltezeiten (30 Sekunden - 5 Minuten)
    - Kleine Gewinne pro Trade (5-20 Pips)
    - Enge Stop-Loss (3-10 Pips)
    - Hohe Trade-Frequenz
    - Fokus auf liquide Märkte
    """
    
    def __init__(self):
        # Scalping Parameter
        self.min_price_movement = 0.0005  # 5 Pips Minimum-Bewegung
        self.tight_spread_threshold = 0.0002  # 2 Pips max Spread
        self.quick_profit_target = 0.0015  # 15 Pips Gewinnziel
        self.tight_stop_loss = 0.0008  # 8 Pips Stop-Loss
        self.max_holding_time = 300  # 5 Minuten max
        
    def analyze(self, market_data: Dict, commodity_info: Dict) -> Dict:
        """
        Analysiere Markt für Scalping-Gelegenheiten
        
        Returns:
            dict mit 'signal', 'confidence', 'entry_price', 'tp', 'sl'
        """
        try:
            price = market_data.get('price', 0)
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            ema_20 = market_data.get('ema_20', price)
            
            # Scalping-Bedingungen
            signal = "HOLD"
            confidence = 0.0
            reason = []
            
            # 1. RSI Extremwerte (schnelle Umkehr)
            if rsi < 25:  # Stark überverkauft
                signal = "BUY"
                confidence += 0.4
                reason.append("RSI stark überverkauft")
            elif rsi > 75:  # Stark überkauft
                signal = "SELL"
                confidence += 0.4
                reason.append("RSI stark überkauft")
            
            # 2. MACD Crossover (Momentum-Wechsel)
            macd_histogram = macd - macd_signal
            if macd > macd_signal and macd_histogram > 0.001:
                if signal == "HOLD":
                    signal = "BUY"
                confidence += 0.3
                reason.append("MACD Bullish Crossover")
            elif macd < macd_signal and macd_histogram < -0.001:
                if signal == "HOLD":
                    signal = "SELL"
                confidence += 0.3
                reason.append("MACD Bearish Crossover")
            
            # 3. EMA Bounce (Preis prallt von EMA ab)
            price_to_ema_ratio = abs(price - ema_20) / ema_20
            if price_to_ema_ratio < 0.002:  # Sehr nah an EMA
                if price > ema_20 and signal != "SELL":
                    if signal == "HOLD":
                        signal = "BUY"
                    confidence += 0.3
                    reason.append("Preis über EMA-20")
                elif price < ema_20 and signal != "BUY":
                    if signal == "HOLD":
                        signal = "SELL"
                    confidence += 0.3
                    reason.append("Preis unter EMA-20")
            
            # Mindest-Confidence für Scalping: 0.6 (höher als normale Strategien)
            if confidence < 0.6:
                signal = "HOLD"
                confidence = 0.0
                reason = ["Zu wenig Confidence für Scalping"]
            
            # Berechne enge TP/SL für Scalping
            if signal == "BUY":
                entry_price = price
                take_profit = price * (1 + self.quick_profit_target)  # +0.15%
                stop_loss = price * (1 - self.tight_stop_loss)  # -0.08%
            elif signal == "SELL":
                entry_price = price
                take_profit = price * (1 - self.quick_profit_target)  # -0.15%
                stop_loss = price * (1 + self.tight_stop_loss)  # +0.08%
            else:
                entry_price = price
                take_profit = None
                stop_loss = None
            
            result = {
                'signal': signal,
                'confidence': round(confidence, 2),
                'entry_price': entry_price,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'reason': " | ".join(reason),
                'strategy': 'SCALPING',
                'holding_time_target': '30s-5min',
                'risk_reward_ratio': round(self.quick_profit_target / self.tight_stop_loss, 2)
            }
            
            if signal != "HOLD":
                logger.info(f"🎯 SCALPING Signal für {commodity_info.get('name')}: {signal} "
                          f"(Confidence: {confidence:.0%}) - {result['reason']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in scalping analysis: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'entry_price': 0,
                'take_profit': None,
                'stop_loss': None,
                'reason': f'Error: {str(e)}',
                'strategy': 'SCALPING'
            }
    
    def should_close_position(self, trade: Dict, current_price: float, time_held: int) -> Dict:
        """
        Prüfe ob Position geschlossen werden soll (Scalping-spezifisch)
        
        Args:
            trade: Trade-Dict mit entry_price, type, etc.
            current_price: Aktueller Marktpreis
            time_held: Sekunden seit Trade-Opening
            
        Returns:
            dict mit 'should_close', 'reason'
        """
        try:
            entry_price = trade.get('entry_price', 0)
            trade_type = trade.get('type', 'BUY')
            
            if entry_price == 0:
                return {'should_close': False, 'reason': 'Invalid entry price'}
            
            # Berechne P/L Prozent
            if trade_type == 'BUY':
                pl_percent = (current_price - entry_price) / entry_price
            else:  # SELL
                pl_percent = (entry_price - current_price) / entry_price
            
            # Scalping Exit-Bedingungen
            
            # 1. Schneller Gewinn erreicht (15 Pips)
            if pl_percent >= self.quick_profit_target:
                return {
                    'should_close': True,
                    'reason': f'Scalping Gewinnziel erreicht: {pl_percent:.2%}'
                }
            
            # 2. Stop-Loss (8 Pips)
            if pl_percent <= -self.tight_stop_loss:
                return {
                    'should_close': True,
                    'reason': f'Scalping Stop-Loss: {pl_percent:.2%}'
                }
            
            # 3. Max Haltezeit überschritten (5 Minuten)
            if time_held > self.max_holding_time:
                return {
                    'should_close': True,
                    'reason': f'Max Scalping Zeit ({self.max_holding_time}s) überschritten'
                }
            
            # 4. Kleiner Gewinn + lange Haltezeit (Break-Even Exit)
            if pl_percent > 0.0005 and time_held > 180:  # 5+ Pips nach 3 min
                return {
                    'should_close': True,
                    'reason': f'Break-Even Exit: {pl_percent:.2%} nach {time_held}s'
                }
            
            return {'should_close': False, 'reason': 'Halte Position'}
            
        except Exception as e:
            logger.error(f"Error in scalping exit logic: {e}")
            return {'should_close': False, 'reason': f'Error: {str(e)}'}
    
    def get_position_size(self, account_balance: float, risk_percent: float = 0.5) -> float:
        """
        Berechne Position Size für Scalping (kleiner als normale Trades)
        
        Args:
            account_balance: Account Balance
            risk_percent: Risiko pro Trade (Standard: 0.5% für Scalping)
            
        Returns:
            Position size
        """
        # Scalping nutzt kleinere Positionen wegen höherer Frequenz
        return account_balance * (risk_percent / 100)
    
    def is_good_scalping_market(self, commodity_id: str, market_data: Dict) -> bool:
        """
        Prüfe ob Markt für Scalping geeignet ist
        
        Gute Scalping-Märkte:
        - Hohe Liquidität
        - Enge Spreads
        - Hohe Volatilität (aber nicht zu hoch)
        """
        # Bevorzugte Scalping-Märkte
        good_scalping_commodities = [
            'GOLD', 'SILVER', 'EURUSD', 'BITCOIN',
            'WTI_CRUDE', 'NATURAL_GAS'
        ]
        
        if commodity_id not in good_scalping_commodities:
            return False
        
        # Prüfe Volatilität (RSI als Proxy)
        rsi = market_data.get('rsi', 50)
        
        # Zu extreme RSI = zu volatil für Scalping
        if rsi < 15 or rsi > 85:
            return False
        
        return True


# Globale Scalping-Strategie Instanz
scalping_strategy = ScalpingStrategy()
