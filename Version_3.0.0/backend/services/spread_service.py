"""
📊 Booner Trade V3.1.0 - Spread Service

Service für Spread-Berechnung und -Analyse.
Extrahiert aus multi_bot_system.py für bessere Modularität.
"""

from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SpreadStatus(Enum):
    """Status-Klassifikation für Spreads."""
    EXCELLENT = "EXCELLENT"    # < 0.1%
    ACCEPTABLE = "ACCEPTABLE"  # 0.1% - 0.3%
    HIGH = "HIGH"              # 0.3% - 0.5%
    EXTREME = "EXTREME"        # > 0.5%


class SpreadService:
    """
    V3.1.0: Service für Spread-bezogene Berechnungen.
    
    Zentrale Logik für:
    - Spread-Abruf vom Broker
    - Spread-Klassifikation
    - SL/TP-Anpassung basierend auf Spread
    """
    
    # Typische Spreads nach Asset-Klasse (als Fallback)
    TYPICAL_SPREADS = {
        'crypto': 0.003,           # 0.3%
        'commodity_energy': 0.002, # 0.2%
        'commodity_metal': 0.0015, # 0.15%
        'commodity_agric': 0.004,  # 0.4% (oft höher)
        'forex_major': 0.0001,     # 0.01%
        'forex_minor': 0.0003,     # 0.03%
        'index': 0.001,            # 0.1%
    }
    
    # Max akzeptabler Spread pro Asset-Klasse (in %)
    MAX_SPREAD_THRESHOLDS = {
        'crypto': 0.5,
        'commodity_energy': 0.3,
        'forex_major': 0.02,
        'forex_minor': 0.05,
        'commodity_metal': 0.2,
        'commodity_agric': 0.5,
        'index': 0.15,
    }
    
    # Spread-Buffer Multiplikatoren nach Trading-Modus
    SPREAD_MODE_MULTIPLIERS = {
        'aggressive': 1.2,
        'standard': 1.5,
        'conservative': 2.0
    }
    
    @classmethod
    async def get_live_spread(
        cls,
        platform_name: str,
        symbol: str,
        fallback_price: float = None
    ) -> Tuple[Optional[float], Optional[float], float]:
        """
        Holt den aktuellen Spread vom Broker.
        
        Returns:
            Tuple[bid, ask, spread] - None-Werte wenn nicht verfügbar
        """
        try:
            from multi_platform_connector import multi_platform
            
            price_data = await multi_platform.get_symbol_price(platform_name, symbol)
            
            if price_data:
                bid = price_data.get('bid')
                ask = price_data.get('ask')
                spread = ask - bid if ask and bid and ask > bid else 0
                
                logger.debug(f"📊 Live Spread für {symbol}: Bid={bid}, Ask={ask}, Spread={spread}")
                return bid, ask, spread
                
        except Exception as e:
            logger.debug(f"Spread-Abruf fehlgeschlagen: {e}")
        
        # Fallback: Approximation
        if fallback_price:
            asset_class = cls._detect_asset_class(symbol)
            spread_factor = cls.TYPICAL_SPREADS.get(asset_class, 0.002)
            
            bid = fallback_price * (1 - spread_factor / 2)
            ask = fallback_price * (1 + spread_factor / 2)
            spread = ask - bid
            
            logger.debug(f"📊 Spread-Approximation für {symbol}: {spread:.4f} ({spread_factor*100:.3f}%)")
            return bid, ask, spread
        
        return None, None, 0.0
    
    @classmethod
    def classify_spread(
        cls,
        spread: float,
        price: float,
        asset_class: str = None
    ) -> Dict[str, Any]:
        """
        Klassifiziert einen Spread und gibt Empfehlungen.
        
        Returns:
            Dict mit status, percent, warning, etc.
        """
        spread_percent = (spread / price * 100) if price > 0 else 0
        
        max_threshold = cls.MAX_SPREAD_THRESHOLDS.get(asset_class, 0.3)
        
        if spread_percent <= max_threshold * 0.5:
            status = SpreadStatus.EXCELLENT
            warning = None
        elif spread_percent <= max_threshold:
            status = SpreadStatus.ACCEPTABLE
            warning = None
        elif spread_percent <= max_threshold * 1.5:
            status = SpreadStatus.HIGH
            warning = f"Spread ({spread_percent:.3f}%) über Normal"
        else:
            status = SpreadStatus.EXTREME
            warning = f"⚠️ EXTREMER Spread ({spread_percent:.3f}%)!"
        
        return {
            'spread': spread,
            'spread_percent': spread_percent,
            'status': status.value,
            'max_threshold': max_threshold,
            'warning': warning,
            'is_acceptable': status in [SpreadStatus.EXCELLENT, SpreadStatus.ACCEPTABLE]
        }
    
    @classmethod
    def calculate_spread_adjusted_sl(
        cls,
        original_sl_distance: float,
        spread: float,
        trading_mode: str = 'standard'
    ) -> Tuple[float, float]:
        """
        Berechnet den Spread-angepassten SL-Abstand.
        
        Returns:
            Tuple[adjusted_sl_distance, spread_buffer_applied]
        """
        if spread <= 0:
            return original_sl_distance, 0.0
        
        multiplier = cls.SPREAD_MODE_MULTIPLIERS.get(trading_mode, 1.5)
        spread_buffer = spread * multiplier
        
        adjusted_sl = original_sl_distance + spread_buffer
        
        return adjusted_sl, spread_buffer
    
    @classmethod
    def _detect_asset_class(cls, symbol: str) -> str:
        """Erkennt die Asset-Klasse basierend auf dem Symbol-Namen."""
        symbol_upper = symbol.upper()
        
        # Crypto
        if any(c in symbol_upper for c in ['BTC', 'ETH', 'BITCOIN', 'ETHEREUM', 'CRYPTO']):
            return 'crypto'
        
        # Energie
        if any(c in symbol_upper for c in ['OIL', 'WTI', 'BRENT', 'GAS', 'CRUDE']):
            return 'commodity_energy'
        
        # Metalle
        if any(c in symbol_upper for c in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'COPPER', 'ZINC', 'XAU', 'XAG']):
            return 'commodity_metal'
        
        # Agrar
        if any(c in symbol_upper for c in ['WHEAT', 'CORN', 'SOYBEAN', 'COFFEE', 'SUGAR', 'COCOA']):
            return 'commodity_agric'
        
        # Forex
        if any(c in symbol_upper for c in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD']):
            if any(m in symbol_upper for m in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']):
                return 'forex_major'
            return 'forex_minor'
        
        # Indizes
        if any(c in symbol_upper for c in ['NASDAQ', 'SPX', 'DOW', 'DAX', 'FTSE', 'INDEX', '100', '500']):
            return 'index'
        
        return 'commodity_metal'  # Default


class TradeSettingsService:
    """
    V3.1.0: Service für Trade-Settings Management.
    
    Zentrale Logik für:
    - Speichern von Trade-Settings (inkl. Spread-Daten)
    - Abrufen von Settings für KI-Überwachung
    """
    
    @classmethod
    async def save_trade_settings(
        cls,
        ticket: str,
        trade_data: Dict[str, Any],
        spread_info: Dict[str, Any] = None
    ) -> bool:
        """
        Speichert Trade-Settings inkl. Spread-Informationen.
        """
        try:
            from database_v2 import get_trades_db
            trades_db = await get_trades_db()
            
            settings_doc = {
                'ticket': str(ticket),
                'symbol': trade_data.get('symbol'),
                'platform': trade_data.get('platform'),
                'type': trade_data.get('type'),
                'entry_price': trade_data.get('entry_price'),
                'stop_loss': trade_data.get('stop_loss'),
                'take_profit': trade_data.get('take_profit'),
                'strategy': trade_data.get('strategy', '4pillar_autonomous'),
                'confidence': trade_data.get('confidence', 0),
                'trading_mode': trade_data.get('trading_mode', 'standard'),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # V3.1.0: Spread-Informationen hinzufügen
            if spread_info:
                settings_doc.update({
                    'spread': spread_info.get('spread', 0),
                    'spread_percent': spread_info.get('spread_percent', 0),
                    'spread_status': spread_info.get('status', 'UNKNOWN'),
                    'bid_at_entry': spread_info.get('bid'),
                    'ask_at_entry': spread_info.get('ask'),
                    'sl_percent': trade_data.get('sl_percent', 0),
                    'tp_percent': trade_data.get('tp_percent', 0),
                    'atr': trade_data.get('atr', 0)
                })
            
            await trades_db.save_trade_settings(f"mt5_{ticket}", settings_doc)
            logger.info(f"💾 Trade-Settings gespeichert: #{ticket}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Trade-Settings speichern fehlgeschlagen: {e}")
            return False
    
    @classmethod
    async def get_trade_settings(cls, ticket: str) -> Optional[Dict[str, Any]]:
        """
        Holt Trade-Settings für ein Ticket.
        """
        try:
            from database_v2 import get_trades_db
            trades_db = await get_trades_db()
            
            return await trades_db.get_trade_settings(f"mt5_{ticket}")
            
        except Exception as e:
            logger.error(f"❌ Trade-Settings abrufen fehlgeschlagen: {e}")
            return None


# Export
__all__ = ['SpreadService', 'SpreadStatus', 'TradeSettingsService']
