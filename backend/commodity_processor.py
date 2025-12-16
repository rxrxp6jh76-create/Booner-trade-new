"""
Commodity Data Processor for Multi-Commodity Trading
"""

import logging
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import OrderedDict
import time

logger = logging.getLogger(__name__)

# Global reference to platform connector (will be set by server.py)
_platform_connector = None

def set_platform_connector(connector):
    """Set the platform connector for fetching MetaAPI data"""
    global _platform_connector
    _platform_connector = connector


# Handelszeiten (UTC) - Wichtig für AI Trading Bot
MARKET_HOURS = {
    # Edelmetalle - 24/5 (Sonntag 22:00 - Freitag 21:00 UTC)
    "GOLD": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    "SILVER": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    "PLATINUM": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    "PALLADIUM": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    
    # Energie - 24/5 (Sonntag 22:00 - Freitag 21:00 UTC)
    "WTI_CRUDE": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    "BRENT_CRUDE": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    "NATURAL_GAS": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    
    # Industriemetalle - 24/5 (Sonntag 22:00 - Freitag 21:00 UTC)
    "COPPER": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    
    # Agrar - Börsenzeiten (Montag-Freitag 08:30-20:00 UTC)
    "WHEAT": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    "CORN": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    "SOYBEANS": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    "COFFEE": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    "SUGAR": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    "COCOA": {"opens": "08:30", "closes": "20:00", "days": [0,1,2,3,4], "24_5": False, "display": "Mo-Fr 08:30-20:00 UTC"},
    
    # Forex - 24/5 (Sonntag 22:00 - Freitag 21:00 UTC)
    "EURUSD": {"opens": "22:00", "closes": "21:00", "days": [0,1,2,3,4], "24_5": True, "display": "24/5 (So 22:00 - Fr 21:00 UTC)"},
    
    # Crypto - 24/7
    "BITCOIN": {"opens": "00:00", "closes": "23:59", "days": [0,1,2,3,4,5,6], "24_7": True, "display": "24/7 (Immer geöffnet)"}
}

def is_market_open(commodity_id: str) -> bool:
    """
    Prüft ob der Markt für ein Commodity aktuell geöffnet ist
    
    Returns:
        True wenn Markt offen, False wenn geschlossen
    """
    try:
        if commodity_id not in MARKET_HOURS:
            logger.warning(f"Keine Handelszeiten für {commodity_id} definiert - assume open")
            return True
        
        hours = MARKET_HOURS[commodity_id]
        now_utc = datetime.now(timezone.utc)
        current_weekday = now_utc.weekday()  # 0=Montag, 6=Sonntag
        current_time = now_utc.strftime("%H:%M")
        
        # Crypto 24/7
        if hours.get("24_7"):
            return True
        
        # Prüfe Wochentag
        if current_weekday not in hours["days"]:
            return False
        
        # 24/5 Märkte (z.B. Gold, Öl)
        if hours.get("24_5"):
            # Sonntag ab 22:00 UTC bis Freitag 21:00 UTC
            if current_weekday == 6:  # Sonntag
                return current_time >= hours["opens"]
            elif current_weekday == 4:  # Freitag
                return current_time <= hours["closes"]
            else:  # Mo-Do
                return True
        
        # Normale Börsenzeiten
        return hours["opens"] <= current_time <= hours["closes"]
        
    except Exception as e:
        logger.error(f"Fehler bei Marktzeiten-Prüfung für {commodity_id}: {e}")
        return True  # Im Zweifel als offen annehmen

def get_next_market_open(commodity_id: str) -> str:
    """
    Gibt die nächste Marktöffnungszeit zurück
    
    Returns:
        String mit nächster Öffnungszeit (z.B. "Sonntag 22:00 UTC")
    """
    try:
        if commodity_id not in MARKET_HOURS:
            return "Unbekannt"
        
        hours = MARKET_HOURS[commodity_id]
        
        if hours.get("24_7"):
            return "24/7 geöffnet"
        
        if hours.get("24_5"):
            return "Sonntag 22:00 UTC"
        
        now_utc = datetime.now(timezone.utc)
        current_weekday = now_utc.weekday()
        
        # Wenn heute ein Handelstag
        if current_weekday in hours["days"]:
            return f"Heute {hours['opens']} UTC"
        
        # Nächster Handelstag (Montag)
        return f"Montag {hours['opens']} UTC"
        
    except Exception as e:
        logger.error(f"Fehler bei nächster Öffnungszeit für {commodity_id}: {e}")
        return "Unbekannt"

# Commodity definitions - Multi-Platform Support mit separaten MT5 Brokern
# MT5 Libertex: Erweiterte Auswahl
# MT5 ICMarkets: Nur Edelmetalle + WTI_F6, BRENT_F6
# Bitpanda: Alle Rohstoffe verfügbar
COMMODITIES = {
    # Precious Metals (Spot prices)
    # Libertex: ✅ XAUUSD, XAGUSD, PL, PA | ICMarkets: ✅ | Bitpanda: ✅
    "GOLD": {
        "name": "Gold", 
        "symbol": "GC=F", 
        "mt5_libertex_symbol": "XAUUSD",
        "mt5_icmarkets_symbol": "XAUUSD", 
        "bitpanda_symbol": "GOLD",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SILVER": {
        "name": "Silber", 
        "symbol": "SI=F", 
        "mt5_libertex_symbol": "XAGUSD",
        "mt5_icmarkets_symbol": "XAGUSD", 
        "bitpanda_symbol": "SILVER",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "PLATINUM": {
        "name": "Platin", 
        "symbol": "PL=F", 
        "mt5_libertex_symbol": "PL",
        "mt5_icmarkets_symbol": "XPTUSD", 
        "bitpanda_symbol": "PLATINUM",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "PALLADIUM": {
        "name": "Palladium", 
        "symbol": "PA=F", 
        "mt5_libertex_symbol": "PA",
        "mt5_icmarkets_symbol": "XPDUSD", 
        "bitpanda_symbol": "PALLADIUM",
        "category": "Edelmetalle", 
        "unit": "USD/oz", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    
    # Energy Commodities
    # Libertex: ✅ CL (WTI), BRN (Brent), NG (Gas) | ICMarkets: ✅ | Bitpanda: ✅
    "WTI_CRUDE": {
        "name": "WTI Crude Oil", 
        "symbol": "CL=F", 
        "mt5_libertex_symbol": "CL",
        "mt5_icmarkets_symbol": "WTI_F6", 
        "bitpanda_symbol": "OIL_WTI",
        "category": "Energie", 
        "unit": "USD/Barrel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "BRENT_CRUDE": {
        "name": "Brent Crude Oil", 
        "symbol": "BZ=F", 
        "mt5_libertex_symbol": "BRN",
        "mt5_icmarkets_symbol": "BRENT_F6", 
        "bitpanda_symbol": "OIL_BRENT",
        "category": "Energie", 
        "unit": "USD/Barrel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "NATURAL_GAS": {
        "name": "Natural Gas", 
        "symbol": "NG=F", 
        "mt5_libertex_symbol": "NG",
        "mt5_icmarkets_symbol": None, 
        "bitpanda_symbol": "NATURAL_GAS",
        "category": "Energie", 
        "unit": "USD/MMBtu", 
        "platforms": ["MT5_LIBERTEX", "BITPANDA"]
    },
    
    # Metals (Industrial)
    "COPPER": {
        "name": "Kupfer", 
        "symbol": "HG=F", 
        "mt5_libertex_symbol": "COPPER",
        "mt5_icmarkets_symbol": "COPPER", 
        "bitpanda_symbol": "COPPER",
        "category": "Industriemetalle", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    
    # Agricultural Commodities
    # Libertex: ✅ WHEAT, SOYBEAN, COFFEE, SUGAR, COCOA, CORN | ICMarkets: teilweise
    "WHEAT": {
        "name": "Weizen", 
        "symbol": "ZW=F", 
        "mt5_libertex_symbol": "WHEAT",
        "mt5_icmarkets_symbol": "Wheat_H6", 
        "bitpanda_symbol": "WHEAT",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "CORN": {
        "name": "Mais", 
        "symbol": "ZC=F", 
        "mt5_libertex_symbol": "CORN",
        "mt5_icmarkets_symbol": "Corn_H6", 
        "bitpanda_symbol": "CORN",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SOYBEANS": {
        "name": "Sojabohnen", 
        "symbol": "ZS=F", 
        "mt5_libertex_symbol": "SOYBEAN",
        "mt5_icmarkets_symbol": "Sbean_F6", 
        "bitpanda_symbol": "SOYBEANS",
        "category": "Agrar", 
        "unit": "USD/Bushel", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "COFFEE": {
        "name": "Kaffee", 
        "symbol": "KC=F", 
        "mt5_libertex_symbol": "COFFEE",
        "mt5_icmarkets_symbol": "Coffee_H6", 
        "bitpanda_symbol": "COFFEE",
        "category": "Agrar", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "SUGAR": {
        "name": "Zucker", 
        "symbol": "SB=F", 
        "mt5_libertex_symbol": "SUGAR",
        "mt5_icmarkets_symbol": "Sugar_H6", 
        "bitpanda_symbol": "SUGAR",
        "category": "Agrar", 
        "unit": "USD/lb", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    "COCOA": {
        "name": "Kakao", 
        "symbol": "CC=F", 
        "mt5_libertex_symbol": "COCOA",
        "mt5_icmarkets_symbol": "Cocoa_H6", 
        "bitpanda_symbol": "COCOA",
        "category": "Agrar", 
        "unit": "USD/ton", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    },
    
    # Forex - Major Currency Pairs
    "EURUSD": {
        "name": "EUR/USD", 
        "symbol": "EURUSD=X", 
        "mt5_libertex_symbol": "EURUSD",
        "mt5_icmarkets_symbol": "EURUSD", 
        "bitpanda_symbol": None,
        "category": "Forex", 
        "unit": "Exchange Rate", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS"]
    },
    
    # Crypto - 24/7 Trading!
    "BITCOIN": {
        "name": "Bitcoin", 
        "symbol": "BTC-USD", 
        "mt5_libertex_symbol": "BTCUSD",
        "mt5_icmarkets_symbol": "BTCUSD", 
        "bitpanda_symbol": "BTC",
        "category": "Crypto", 
        "unit": "USD", 
        "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]
    }
}



def get_commodities_with_hours():
    """
    Gibt COMMODITIES mit Handelszeiten zurück
    """
    commodities_with_hours = {}
    for commodity_id, commodity_data in COMMODITIES.items():
        commodity_with_hours = commodity_data.copy()
        
        # Füge Handelszeiten hinzu
        if commodity_id in MARKET_HOURS:
            market_hours = MARKET_HOURS[commodity_id]
            commodity_with_hours['market_hours'] = market_hours.get('display', 'Nicht verfügbar')
            commodity_with_hours['market_open'] = is_market_open(commodity_id)
        else:
            commodity_with_hours['market_hours'] = 'Nicht verfügbar'
            commodity_with_hours['market_open'] = True
        
        commodities_with_hours[commodity_id] = commodity_with_hours
    
    return commodities_with_hours


# Simple cache for current price fetching (separate from OHLCV cache)
# REDUCED for memory efficiency
_price_cache = OrderedDict()
_price_cache_expiry = OrderedDict()
MAX_PRICE_CACHE_SIZE = 20  # Reduced from 50

def fetch_commodity_data(commodity_id: str):
    """
    Fetch commodity data with caching and MetaAPI priority
    Priority: MetaAPI (live broker data) → Cached yfinance → Fresh yfinance
    """
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
        
        # Check cache first (5 minutes for current price)
        cache_key = f"price_{commodity_id}"
        now = datetime.now()
        
        if cache_key in _price_cache and cache_key in _price_cache_expiry:
            if now < _price_cache_expiry[cache_key]:
                logger.debug(f"Returning cached price data for {commodity_id}")
                return _price_cache[cache_key]
        
        commodity = COMMODITIES[commodity_id]
        
        # Priority 1: Try to get live data from MetaAPI (if available)
        if _platform_connector is not None:
            metaapi_supported = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "EURUSD"]
            
            if commodity_id in metaapi_supported:
                try:
                    # Try ICMarkets first
                    symbol = commodity.get('mt5_icmarkets_symbol')
                    if symbol:
                        for platform_key in ['MT5_ICMARKETS_DEMO', 'MT5_ICMARKETS']:
                            if platform_key in _platform_connector.platforms:
                                platform_data = _platform_connector.platforms[platform_key]
                                if platform_data.get('active'):
                                    # MetaAPI data is already being streamed, just return minimal hist
                                    # Create a simple DataFrame with recent price
                                    hist = pd.DataFrame({
                                        'Close': [0],  # Placeholder, will be updated by live stream
                                        'Open': [0],
                                        'High': [0],
                                        'Low': [0],
                                        'Volume': [0]
                                    })
                                    logger.info(f"✅ Using MetaAPI streaming data for {commodity_id}")
                                    
                                    # Cache for 5 minutes
                                    if len(_price_cache) >= MAX_PRICE_CACHE_SIZE:
                                        _price_cache.popitem(last=False)
                                        _price_cache_expiry.popitem(last=False)
                                    
                                    _price_cache[cache_key] = hist
                                    _price_cache_expiry[cache_key] = now + timedelta(minutes=5)
                                    return hist
                    
                    # Try Libertex as fallback
                    symbol = commodity.get('mt5_libertex_symbol')
                    if symbol:
                        for platform_key in ['MT5_LIBERTEX_DEMO', 'MT5_LIBERTEX_REAL', 'MT5_LIBERTEX']:
                            if platform_key in _platform_connector.platforms:
                                platform_data = _platform_connector.platforms[platform_key]
                                if platform_data.get('active'):
                                    hist = pd.DataFrame({
                                        'Close': [0],
                                        'Open': [0],
                                        'High': [0],
                                        'Low': [0],
                                        'Volume': [0]
                                    })
                                    logger.info(f"✅ Using MetaAPI streaming data (Libertex) for {commodity_id}")
                                    
                                    # Cache for 5 minutes
                                    if len(_price_cache) >= MAX_PRICE_CACHE_SIZE:
                                        _price_cache.popitem(last=False)
                                        _price_cache_expiry.popitem(last=False)
                                    
                                    _price_cache[cache_key] = hist
                                    _price_cache_expiry[cache_key] = now + timedelta(minutes=5)
                                    return hist
                except Exception as e:
                    logger.warning(f"MetaAPI check failed for {commodity_id}: {e}, falling back to yfinance")
        
        # Priority 2: yfinance with longer cache (30 minutes to avoid rate limits)
        ticker = yf.Ticker(commodity["symbol"])
        
        # Add delay to avoid rate limiting (only if not cached)
        time.sleep(0.5)
        
        # Get historical data (reduced period to avoid rate limits)
        hist = ticker.history(period="5d", interval="1h")
        
        if hist.empty or len(hist) == 0:
            logger.warning(f"No data received for {commodity['name']}")
            # Return stale cache if available
            if cache_key in _price_cache:
                logger.warning(f"Returning stale cached data for {commodity_id}")
                return _price_cache[cache_key]
            return None
        
        # Cache for 30 minutes (longer to avoid rate limits)
        if len(_price_cache) >= MAX_PRICE_CACHE_SIZE:
            _price_cache.popitem(last=False)
            _price_cache_expiry.popitem(last=False)
        
        _price_cache[cache_key] = hist
        _price_cache_expiry[cache_key] = now + timedelta(minutes=30)
        
        return hist
    except Exception as e:
        logger.error(f"Error fetching {commodity_id} data: {e}")
        # Try to return cached data even if expired
        cache_key = f"price_{commodity_id}"
        if cache_key in _price_cache:
            logger.warning(f"Error occurred, returning stale cached data for {commodity_id}")
            return _price_cache[cache_key]
        return None


import time
from datetime import timedelta

# Cache for OHLCV data to avoid rate limiting
# MEMORY FIX: LRU Cache mit maximaler Größe
from collections import OrderedDict

MAX_CACHE_SIZE = 30  # Reduced from 100 for memory efficiency
_ohlcv_cache = OrderedDict()
_cache_expiry = OrderedDict()

async def fetch_metaapi_candles(commodity_id: str, timeframe: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
    """
    Fetch historical candle data from MetaAPI for supported commodities
    
    Args:
        commodity_id: Commodity identifier (e.g., 'GOLD', 'SILVER', 'WTI_CRUDE')
        timeframe: Timeframe - '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
        limit: Number of candles
    
    Returns:
        pandas DataFrame with OHLCV data or None if not available
    """
    try:
        if commodity_id not in COMMODITIES:
            return None
        
        commodity = COMMODITIES[commodity_id]
        
        # Check if MetaAPI is available for this commodity
        if _platform_connector is None:
            return None
        
        # Try ICMarkets first (primary broker)
        symbol = commodity.get('mt5_icmarkets_symbol')
        if symbol and 'MT5_ICMARKETS' in _platform_connector.platforms:
            connector = _platform_connector.platforms['MT5_ICMARKETS'].get('connector')
            if connector:
                candles = await connector.get_candles(symbol, timeframe, limit)
                if candles and len(candles) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(candles)
                    # Rename columns to match yfinance format
                    if 'time' in df.columns:
                        df['Date'] = pd.to_datetime(df['time'])
                        df.set_index('Date', inplace=True)
                    if 'open' in df.columns:
                        df.rename(columns={
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        }, inplace=True)
                    logger.info(f"✅ Fetched {len(df)} candles from MetaAPI for {commodity_id}")
                    return df
        
        # Fallback to Libertex if ICMarkets unavailable
        symbol = commodity.get('mt5_libertex_symbol')
        if symbol and 'MT5_LIBERTEX' in _platform_connector.platforms:
            connector = _platform_connector.platforms['MT5_LIBERTEX'].get('connector')
            if connector:
                candles = await connector.get_candles(symbol, timeframe, limit)
                if candles and len(candles) > 0:
                    df = pd.DataFrame(candles)
                    if 'time' in df.columns:
                        df['Date'] = pd.to_datetime(df['time'])
                        df.set_index('Date', inplace=True)
                    if 'open' in df.columns:
                        df.rename(columns={
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        }, inplace=True)
                    logger.info(f"✅ Fetched {len(df)} candles from MetaAPI Libertex for {commodity_id}")
                    return df
        
        return None
    except Exception as e:
        logger.warning(f"MetaAPI candles unavailable for {commodity_id}: {e}")
        return None


async def fetch_historical_ohlcv_async(commodity_id: str, timeframe: str = "1d", period: str = "1mo"):
    """
    Fetch historical OHLCV data with timeframe selection (Async version)
    Hybrid approach: MetaAPI (preferred) → yfinance with extended cache
    
    Args:
        commodity_id: Commodity identifier (e.g., 'GOLD', 'WTI_CRUDE')
        timeframe: Interval - '1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1wk', '1mo'
        period: Data period - '2h', '1d', '5d', '1wk', '2wk', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'
    
    Returns:
        pandas DataFrame with OHLCV data and indicators
    """
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
        
        # Check cache first (extended to 24 hours for yfinance data)
        cache_key = f"{commodity_id}_{timeframe}_{period}"
        now = datetime.now()
        
        if cache_key in _ohlcv_cache and cache_key in _cache_expiry:
            if now < _cache_expiry[cache_key]:
                logger.info(f"Returning cached data for {commodity_id}")
                return _ohlcv_cache[cache_key]
        
        commodity = COMMODITIES[commodity_id]
        
        # Priority 1: Try MetaAPI for supported commodities (Gold, Silver, Platinum, WTI, Brent)
        import asyncio
        metaapi_supported = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE"]
        
        if commodity_id in metaapi_supported:
            try:
                # Map period to number of candles
                period_to_limit = {
                    '2h': 120,      # 2 hours with 1m candles
                    '1d': 24,       # 1 day with 1h candles
                    '5d': 120,      # 5 days
                    '1wk': 168,     # 1 week
                    '2wk': 336,     # 2 weeks
                    '1mo': 720,     # 1 month
                    '3mo': 2160,    # 3 months
                    '6mo': 4320,    # 6 months
                    '1y': 8760,     # 1 year
                    '2y': 17520,    # 2 years
                    '5y': 43800,    # 5 years
                    'max': 1000     # Max available
                }
                limit = period_to_limit.get(period, 720)
                
                # Convert timeframe for MetaAPI
                tf_map = {'1d': '1h', '1wk': '4h', '1mo': '1d'}
                metaapi_tf = tf_map.get(timeframe, timeframe)
                
                metaapi_data = await fetch_metaapi_candles(commodity_id, metaapi_tf, limit)
                if metaapi_data is not None and not metaapi_data.empty:
                    # Cache for 1 hour (MetaAPI data is fresh)
                    # MEMORY FIX: Evict oldest if cache is full
                    if len(_ohlcv_cache) >= MAX_CACHE_SIZE:
                        _ohlcv_cache.popitem(last=False)  # Remove oldest (FIFO)
                        _cache_expiry.popitem(last=False)
                    
                    _ohlcv_cache[cache_key] = metaapi_data
                    _cache_expiry[cache_key] = now + timedelta(hours=1)
                    return metaapi_data
                else:
                    logger.info(f"MetaAPI unavailable for {commodity_id}, falling back to yfinance")
            except Exception as e:
                logger.warning(f"MetaAPI fetch failed for {commodity_id}: {e}, using yfinance")
        
        # Priority 2: yfinance with extended caching (24h)
        ticker = yf.Ticker(commodity["symbol"])
        
        # Timeframe mapping
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '1d': '1d', '1wk': '1wk', '1mo': '1mo'
        }
        
        # Period validation (includes 2h, 1wk, 2wk)
        valid_periods = ['2h', '1d', '5d', '1wk', '2wk', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            period = '1mo'
        
        interval = interval_map.get(timeframe, '1d')
        
        # yfinance period mapping (yfinance doesn't support '2h', '1wk', '2wk')
        # For short intraday intervals (1m, 5m, 15m, 30m), we need to fetch enough data
        yf_period_map = {
            '2h': '1d',     # yfinance doesn't support 2h, use 1d (then filter)
            '1wk': '1wk',   # yfinance supports 1wk
            '2wk': '1mo',   # yfinance doesn't support 2wk, use 1mo (then filter)
        }
        
        # Special handling for very short timeframes (1m, 5m)
        # yfinance limits: 1m = max 7d, 5m = max 60d
        if interval in ['1m', '5m', '15m', '30m'] and period in ['2h', '1d']:
            yf_period = '1d'  # Ensure we get enough intraday data
        elif interval in ['1m', '5m'] and period in ['5d', '1wk']:
            yf_period = '5d'  # For 1-5min intervals, limit to 5d for stability
        else:
            yf_period = yf_period_map.get(period, period)
        
        # Get historical data with specified timeframe
        logger.info(f"Fetching {commodity['name']} data: period={period} (yf_period={yf_period}), interval={interval}")
        
        # Add delay to avoid rate limiting
        time.sleep(0.5)
        
        hist = ticker.history(period=yf_period, interval=interval)
        
        if hist.empty or len(hist) == 0:
            logger.warning(f"No data received for {commodity['name']}")
            return None
        
        # Filter data if we requested 2h but got 1d (for intraday intervals)
        if period == '2h' and yf_period == '1d':
            # Filter to last 2 hours of data
            # Make cutoff_time timezone-aware to match hist.index
            import pandas as pd
            cutoff_time = pd.Timestamp.now(tz=hist.index.tz) - timedelta(hours=2)
            hist = hist[hist.index >= cutoff_time]
            logger.info(f"Filtered to last 2 hours: {len(hist)} candles")
        
        # Filter data if we requested 2wk but got 1mo
        if period == '2wk' and yf_period == '1mo':
            # Filter to last 2 weeks of data
            import pandas as pd
            cutoff_time = pd.Timestamp.now(tz=hist.index.tz) - timedelta(weeks=2)
            hist = hist[hist.index >= cutoff_time]
            logger.info(f"Filtered to last 2 weeks: {len(hist)} candles")
        
        # Add indicators
        hist = calculate_indicators(hist)
        
        # Cache successful result (24 hours for yfinance to avoid rate limiting)
        # MEMORY FIX: Evict oldest if cache is full
        if len(_ohlcv_cache) >= MAX_CACHE_SIZE:
            _ohlcv_cache.popitem(last=False)  # Remove oldest (FIFO)
            _cache_expiry.popitem(last=False)
        
        _ohlcv_cache[cache_key] = hist
        _cache_expiry[cache_key] = now + timedelta(hours=24)
        
        return hist
    except Exception as e:
        logger.error(f"Error fetching historical data for {commodity_id}: {e}")
        # If rate limited, try to return cached data even if expired
        if cache_key in _ohlcv_cache:
            logger.warning(f"Rate limited, returning stale cached data for {commodity_id}")
            return _ohlcv_cache[cache_key]
        return None



def fetch_historical_ohlcv(commodity_id: str, timeframe: str = "1d", period: str = "1mo"):
    """
    Synchronous wrapper for fetch_historical_ohlcv_async
    For backwards compatibility with synchronous code
    """
    import asyncio
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context - return a future
            logger.warning("fetch_historical_ohlcv called from async context - use fetch_historical_ohlcv_async instead")
            # Create a new thread to run the async function
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetch_historical_ohlcv_async(commodity_id, timeframe, period))
                return future.result()
        else:
            # We're in a sync context - use asyncio.run
            return asyncio.run(fetch_historical_ohlcv_async(commodity_id, timeframe, period))
    except RuntimeError:
        # No event loop - use asyncio.run
        return asyncio.run(fetch_historical_ohlcv_async(commodity_id, timeframe, period))


def calculate_indicators(df):
    """Calculate technical indicators"""
    try:
        # Safety check
        if df is None or df.empty:
            logger.warning("Cannot calculate indicators on None or empty DataFrame")
            return None
        
        # Check if required column exists
        if 'Close' not in df.columns:
            logger.error("DataFrame missing 'Close' column")
            return None
        
        # SMA
        sma_indicator = SMAIndicator(close=df['Close'], window=20)
        df['SMA_20'] = sma_indicator.sma_indicator()
        
        # EMA
        ema_indicator = EMAIndicator(close=df['Close'], window=20)
        df['EMA_20'] = ema_indicator.ema_indicator()
        
        # RSI
        rsi_indicator = RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi_indicator.rsi()
        
        # MACD
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_histogram'] = macd.macd_diff()
        
        return df
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None  # Return None on error instead of broken df


def generate_signal(latest_data):
    """Generate trading signal based on indicators - REALISTISCHE Strategie"""
    try:
        rsi = latest_data.get('RSI')
        macd = latest_data.get('MACD')
        macd_signal = latest_data.get('MACD_signal')
        price = latest_data.get('Close')
        ema = latest_data.get('EMA_20')
        sma = latest_data.get('SMA_20')
        
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
            return "HOLD", "NEUTRAL"
        
        # Determine trend
        trend = "NEUTRAL"
        if not pd.isna(ema) and not pd.isna(price):
            if price > ema * 1.002:
                trend = "UP"
            elif price < ema * 0.998:
                trend = "DOWN"
        
        # REALISTISCHE TRADING STRATEGIE
        signal = "HOLD"
        
        # BUY Bedingungen (konservativ):
        # 1. RSI überverkauft UND positives MACD Momentum
        if rsi < 35 and macd > macd_signal:
            signal = "BUY"
        
        # 2. Starker Aufwärtstrend mit Bestätigung
        elif trend == "UP" and rsi < 60 and macd > macd_signal:
            signal = "BUY"
        
        # SELL Bedingungen (konservativ):
        # 1. RSI überkauft UND negatives MACD Momentum
        elif rsi > 65 and macd < macd_signal:
            signal = "SELL"
        
        # 2. Starker Abwärtstrend mit Bestätigung
        elif trend == "DOWN" and rsi > 40 and macd < macd_signal:
            signal = "SELL"
        
        return signal, trend
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD", "NEUTRAL"


async def calculate_position_size(balance: float, price: float, db, max_risk_percent: float = 20.0, free_margin: float = None, platform: str = "MT5", multi_platform_connector=None) -> float:
    """Calculate position size ensuring max portfolio risk per platform and considering free margin
    
    Args:
        multi_platform_connector: Optional multi_platform instance to avoid circular imports
    """
    try:
        # WICHTIG: Hole offene Trades LIVE von MT5, nicht aus der lokalen DB!
        # Die DB enthält keine offenen Trades mehr - sie werden nur live abgerufen
        open_trades = []
        total_exposure = 0.0
        
        # Versuche live Positionen von MT5 zu holen
        if multi_platform_connector:
            try:
                # Hole live Positionen von MT5
                positions = await multi_platform_connector.get_open_positions(platform)
                
                # Berechne Exposure von allen offenen Positionen
                for pos in positions:
                    entry_price = pos.get('price_open', 0) or pos.get('openPrice', 0)
                    volume = pos.get('volume', 0)
                    if entry_price and volume:
                        # Exposure = Entry Price * Volume (in Lots)
                        total_exposure += entry_price * volume
                
                logger.info(f"📊 [{platform}] Found {len(positions)} open positions, Total Exposure: {total_exposure:.2f} EUR")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch live positions from {platform}: {e}")
        
        # Fallback: Versuche aus DB (für Backward-Kompatibilität oder wenn kein connector)
        if total_exposure == 0:
            try:
                open_trades = await db.trades.find({"status": "OPEN", "platform": platform}).to_list(100)
                total_exposure = sum([trade.get('entry_price', 0) * trade.get('quantity', 0) for trade in open_trades])
                if total_exposure > 0:
                    logger.info(f"📊 [{platform}] Fallback to DB: {len(open_trades)} open trades, Exposure: {total_exposure:.2f}")
            except Exception as e:
                logger.debug(f"DB fallback failed: {e}")
                pass
        
        # Calculate available capital (max_risk_percent of balance minus current exposure)
        max_portfolio_value = balance * (max_risk_percent / 100)
        available_capital = max(0, max_portfolio_value - total_exposure)
        
        # WICHTIG: Wenn free_margin übergeben wurde, limitiere auf verfügbare Margin
        if free_margin is not None and free_margin < 500:
            # Bei wenig freier Margin (< 500 EUR), nutze nur 20% davon für neue Order
            max_order_value = free_margin * 0.2
            available_capital = min(available_capital, max_order_value)
            logger.warning(f"⚠️ Geringe freie Margin ({free_margin:.2f} EUR) - Order auf {max_order_value:.2f} EUR limitiert")
        
        # WICHTIG: Wenn kein verfügbares Kapital mehr, KEINE neue Position erlauben!
        if available_capital <= 0:
            logger.error(f"❌ [{platform}] Portfolio-Risiko überschritten! Exposure: {total_exposure:.2f} / Max: {max_portfolio_value:.2f} ({max_risk_percent}% von {balance:.2f})")
            return 0.0  # KEIN Trade erlaubt!
        
        # Calculate lot size
        if available_capital > 0 and price > 0:
            lot_size = round(available_capital / price, 2)  # 2 Dezimalstellen
            # Minimum 0.01 (Broker-Minimum), maximum 0.1 für Sicherheit
            lot_size = max(0.01, min(lot_size, 0.1))
        else:
            lot_size = 0.01  # Minimum Lot Size (Broker-Standard)
        
        logger.info(f"✅ [{platform}] Position size: {lot_size} lots (Balance: {balance:.2f}, Free Margin: {free_margin}, Price: {price:.2f}, Exposure: {total_exposure:.2f}/{max_portfolio_value:.2f}, Available: {available_capital:.2f})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.001  # Minimum fallback
