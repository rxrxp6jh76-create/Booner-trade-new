"""
Commodity Market Hours Manager
Verwaltet individuelle Handelszeiten für jedes Asset/Commodity
"""

from datetime import datetime, timezone, time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Default Handelszeiten für alle Commodities
DEFAULT_MARKET_HOURS = {
    # Edelmetalle - 24/5 (Sonntag 22:00 - Freitag 21:00 UTC)
    "GOLD": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],  # Mo-Fr (0=Montag, 6=Sonntag)
        "open_time": "22:00",  # UTC
        "close_time": "21:00",  # UTC
        "is_24_5": True,  # Öffnet Sonntag Abend, schließt Freitag Abend
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "SILVER": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "PLATINUM": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "PALLADIUM": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    
    # Energie - 24/5
    "WTI_CRUDE": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "BRENT_CRUDE": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "NATURAL_GAS": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    
    # Industriemetalle - 24/5
    "COPPER": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    
    # Agrar - Börsenzeiten (Montag-Freitag 08:30-20:00 UTC)
    "WHEAT": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    "CORN": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    "SOYBEANS": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    "COFFEE": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    "SUGAR": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    "COCOA": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "08:30",
        "close_time": "20:00",
        "is_24_5": False,
        "description": "Montag-Freitag 08:30-20:00 UTC"
    },
    
    # Forex - 24/5
    "EURUSD": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "GBPUSD": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    "USDJPY": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4],
        "open_time": "22:00",
        "close_time": "21:00",
        "is_24_5": True,
        "description": "24/5 - Sonntag 22:00 bis Freitag 21:00 UTC"
    },
    
    # Crypto - 24/7
    "BITCOIN": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4, 5, 6],  # Jeden Tag
        "open_time": "00:00",
        "close_time": "23:59",
        "is_24_7": True,
        "description": "24/7 - Immer geöffnet"
    },
    "ETHEREUM": {
        "enabled": True,
        "days": [0, 1, 2, 3, 4, 5, 6],
        "open_time": "00:00",
        "close_time": "23:59",
        "is_24_7": True,
        "description": "24/7 - Immer geöffnet"
    }
}


def is_market_open(commodity_id: str, market_hours: Optional[Dict] = None, current_time: Optional[datetime] = None) -> bool:
    """
    Prüft ob ein spezifisches Commodity aktuell handelbar ist
    
    Args:
        commodity_id: ID des Commodities (z.B. "GOLD", "WTI_CRUDE")
        market_hours: Optional - Custom Handelszeiten (aus DB)
        current_time: Optional - Zeitpunkt zum Prüfen (default: jetzt UTC)
    
    Returns:
        True wenn Markt offen, False wenn geschlossen
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Hole Handelszeiten (Custom oder Default)
    if market_hours and commodity_id in market_hours:
        hours = market_hours[commodity_id]
    elif commodity_id in DEFAULT_MARKET_HOURS:
        hours = DEFAULT_MARKET_HOURS[commodity_id]
    else:
        # Unbekanntes Commodity - Standard 24/5
        logger.warning(f"Keine Handelszeiten für {commodity_id} definiert - verwende Standard 24/5")
        hours = {
            "enabled": True,
            "days": [0, 1, 2, 3, 4],
            "open_time": "00:00",
            "close_time": "23:59",
            "is_24_5": True
        }
    
    # Check ob Handelszeiten deaktiviert sind
    if not hours.get("enabled", True):
        return False
    
    # Check Wochentag (0=Montag, 6=Sonntag)
    current_weekday = current_time.weekday()
    
    # Für 24/7 Märkte (Crypto)
    if hours.get("is_24_7", False):
        return True
    
    # Für 24/5 Märkte (Forex, Edelmetalle, Energie)
    if hours.get("is_24_5", False):
        # Öffnet Sonntag Abend (6), schließt Freitag Abend (4)
        # Montag (0) bis Donnerstag (3): Immer offen
        if current_weekday in [0, 1, 2, 3]:
            return True
        
        # Sonntag (6): Offen ab open_time
        if current_weekday == 6:
            open_time_str = hours.get("open_time", "22:00")
            open_hour, open_min = map(int, open_time_str.split(":"))
            open_time_obj = time(open_hour, open_min)
            current_time_obj = current_time.time()
            return current_time_obj >= open_time_obj
        
        # Freitag (4): Offen bis close_time
        if current_weekday == 4:
            close_time_str = hours.get("close_time", "21:00")
            close_hour, close_min = map(int, close_time_str.split(":"))
            close_time_obj = time(close_hour, close_min)
            current_time_obj = current_time.time()
            return current_time_obj <= close_time_obj
        
        # Samstag (5): Geschlossen
        return False
    
    # Für normale Börsenzeiten (Agrar, Aktien)
    if current_weekday not in hours.get("days", [0, 1, 2, 3, 4]):
        return False
    
    # Prüfe Tageszeit
    open_time_str = hours.get("open_time", "00:00")
    close_time_str = hours.get("close_time", "23:59")
    
    open_hour, open_min = map(int, open_time_str.split(":"))
    close_hour, close_min = map(int, close_time_str.split(":"))
    
    open_time_obj = time(open_hour, open_min)
    close_time_obj = time(close_hour, close_min)
    current_time_obj = current_time.time()
    
    return open_time_obj <= current_time_obj <= close_time_obj


async def get_market_hours(db, use_cache: bool = True) -> Dict:
    """
    Holt die konfigurierten Marktöffnungszeiten aus der Datenbank.
    Fällt auf DEFAULT_MARKET_HOURS zurück wenn nichts konfiguriert ist.
    
    V2.3.35 FIX: Verwendet trading_settings statt separater Collection
    """
    try:
        # Lade aus trading_settings (market_hours Feld)
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if settings and 'market_hours' in settings:
            saved_hours = settings.get('market_hours', {})
            # Merge mit Defaults
            result = {**DEFAULT_MARKET_HOURS}
            for commodity_id, hours in saved_hours.items():
                if commodity_id in result:
                    result[commodity_id].update(hours)
                else:
                    result[commodity_id] = hours
            return result
        
        return DEFAULT_MARKET_HOURS
        
    except Exception as e:
        logger.error(f"Error loading market hours: {e}")
        return DEFAULT_MARKET_HOURS


async def update_market_hours(db, commodity_id: str, hours_config: Dict):
    """
    Aktualisiert die Handelszeiten für ein bestimmtes Commodity.
    
    V2.3.35 FIX: Speichert in trading_settings.market_hours
    """
    try:
        # Hole aktuelle Settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if not settings:
            settings = {"id": "trading_settings", "market_hours": {}}
        
        # Update market_hours
        market_hours = settings.get('market_hours', {})
        market_hours[commodity_id] = hours_config
        
        # Speichere zurück
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"market_hours": market_hours}},
            upsert=True
        )
        
        logger.info(f"✅ Handelszeiten für {commodity_id} gespeichert: {hours_config}")
        return hours_config
        
    except Exception as e:
        logger.error(f"Error updating market hours for {commodity_id}: {e}")
        raise
