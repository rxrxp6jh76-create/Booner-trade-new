"""
Grid Trading Strategy

Platziert Orders in Grid-Struktur (Buy/Sell Grids).
Bestens für Range-bound Markets mit Volatility.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class GridTradingStrategy:
    """
    Grid Trading Strategie
    
    Logik:
    1. Erstelle Grid Levels basierend auf Grid-Größe
    2. Platziere Buy Orders unter aktuellem Preis
    3. Platziere Sell Orders über aktuellem Preis
    4. Nimm Profit wenn Preis Grid-Level erreicht
    """
    
    def __init__(self, settings: Dict):
        self.name = "grid"
        self.display_name = "🔹 Grid Trading"
        self.settings = settings
        
        # Parameter aus Settings oder Defaults
        self.enabled = settings.get('grid_enabled', False)
        self.grid_size_pips = settings.get('grid_size_pips', 50)  # Grid-Größe in Pips
        self.grid_levels = settings.get('grid_levels', 5)  # Anzahl Grid-Levels
        self.grid_direction = settings.get('grid_direction', 'BOTH')  # LONG, SHORT, BOTH
        self.stop_loss_percent = settings.get('grid_stop_loss_percent', 3.0)
        self.take_profit_per_level_percent = settings.get('grid_take_profit_per_level_percent', 1.0)
        self.max_positions = settings.get('grid_max_positions', 10)
        self.risk_per_trade_percent = settings.get('grid_risk_per_trade_percent', 1.0)
        
        logger.info(f"🎯 Grid Trading Strategy initialized: enabled={self.enabled}")
    
    def calculate_grid_levels(self, current_price: float, pip_size: float = 0.01) -> Dict:
        """
        Berechne Grid Levels
        
        Args:
            current_price: Aktueller Preis
            pip_size: Pip-Größe (Standard: 0.01 für Rohstoffe)
            
        Returns:
            Dict mit buy_levels, sell_levels
        """
        grid_size = self.grid_size_pips * pip_size
        
        buy_levels = []
        sell_levels = []
        
        # Buy Levels: Unter aktuellem Preis
        if self.grid_direction in ['LONG', 'BOTH']:
            for i in range(1, self.grid_levels + 1):
                level = current_price - (i * grid_size)
                buy_levels.append(level)
        
        # Sell Levels: Über aktuellem Preis
        if self.grid_direction in ['SHORT', 'BOTH']:
            for i in range(1, self.grid_levels + 1):
                level = current_price + (i * grid_size)
                sell_levels.append(level)
        
        return {
            'buy_levels': buy_levels,
            'sell_levels': sell_levels,
            'grid_size': grid_size,
            'current_price': current_price
        }
    
    def find_closest_grid_level(self, current_price: float, grid_levels: List[float]) -> Optional[float]:
        """
        Finde nächstes Grid Level
        
        Args:
            current_price: Aktueller Preis
            grid_levels: Liste von Grid Levels
            
        Returns:
            Nächstes Grid Level oder None
        """
        if not grid_levels:
            return None
        
        # Finde Level mit kleinster Distanz
        closest = min(grid_levels, key=lambda x: abs(x - current_price))
        return closest
    
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
            open_positions = market_data.get('open_positions', [])
            
            # Bestimme Pip-Größe basierend auf Symbol
            # Gold, Silver etc: 0.01, Währungen: 0.0001
            pip_size = 0.01  # Default für Rohstoffe
            
            # Berechne Grid Levels
            grid_data = self.calculate_grid_levels(current_price, pip_size)
            
            # Prüfe ob wir bereits Grid-Positionen haben
            grid_positions_count = len([p for p in open_positions if p.get('strategy') == 'grid'])
            
            if grid_positions_count >= self.max_positions:
                logger.debug(f"Grid: Max positions ({self.max_positions}) reached for {symbol}")
                return None
            
            # Signal-Logik: Trade wenn Preis Grid-Level erreicht
            signal = None
            confidence = 0.65  # Grid Trading hat moderate Confidence
            reason = ""
            target_level = None
            
            # BUY Signal: Preis erreicht Buy Level
            if self.grid_direction in ['LONG', 'BOTH']:
                closest_buy = self.find_closest_grid_level(current_price, grid_data['buy_levels'])
                if closest_buy and abs(current_price - closest_buy) < (grid_data['grid_size'] * 0.1):  # 10% Toleranz
                    signal = 'BUY'
                    target_level = closest_buy
                    reason = f"Price reached buy grid level ({closest_buy:.2f})"
            
            # SELL Signal: Preis erreicht Sell Level
            if not signal and self.grid_direction in ['SHORT', 'BOTH']:
                closest_sell = self.find_closest_grid_level(current_price, grid_data['sell_levels'])
                if closest_sell and abs(current_price - closest_sell) < (grid_data['grid_size'] * 0.1):
                    signal = 'SELL'
                    target_level = closest_sell
                    reason = f"Price reached sell grid level ({closest_sell:.2f})"
            
            if signal:
                # Berechne SL/TP für Grid Trading
                # TP ist das nächste Grid Level
                # SL ist weiter weg (grid_stop_loss_percent)
                
                if signal == 'BUY':
                    # TP = aktueller Preis + 1 Grid Level
                    take_profit = current_price * (1 + self.take_profit_per_level_percent / 100)
                    stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                else:  # SELL
                    take_profit = current_price * (1 - self.take_profit_per_level_percent / 100)
                    stop_loss = current_price * (1 + self.stop_loss_percent / 100)
                
                logger.info(f"🔹 Grid Signal: {signal} {symbol} @ {current_price:.2f} (Grid Level: {target_level:.2f})")
                
                return {
                    'strategy': 'grid',
                    'signal': signal,
                    'symbol': symbol,
                    'confidence': confidence,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'reason': reason,
                    'indicators': {
                        'target_level': target_level,
                        'grid_size': grid_data['grid_size'],
                        'grid_positions': grid_positions_count,
                        'max_positions': self.max_positions
                    },
                    'risk_percent': self.risk_per_trade_percent,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Grid analysis: {e}", exc_info=True)
            return None
    
    def get_settings_dict(self) -> Dict:
        """Gib aktuelle Settings zurück"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.enabled,
            'grid_size_pips': self.grid_size_pips,
            'grid_levels': self.grid_levels,
            'grid_direction': self.grid_direction,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_per_level_percent': self.take_profit_per_level_percent,
            'max_positions': self.max_positions,
            'risk_per_trade_percent': self.risk_per_trade_percent
        }
