"""
📊 Booner Trade V3.1.0 - Market Routes

Enthält alle marktbezogenen API-Endpunkte:
- Marktdaten abrufen
- OHLCV-Daten
- Live-Ticks
- Handelszeiten
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone, timedelta
import pandas as pd

logger = logging.getLogger(__name__)

market_router = APIRouter(prefix="/market", tags=["Market Data"])


@market_router.get("/all")
async def get_all_markets():
    """Get current market data for all enabled commodities"""
    try:
        import database as db
        from commodity_processor import COMMODITIES
        
        enabled = list(COMMODITIES.keys())
        
        results = {}
        for commodity_id in enabled:
            market_data = await db.market_data.find_one({"commodity": commodity_id})
            if market_data:
                results[commodity_id] = market_data
        
        commodities_list = []
        for commodity_id in enabled:
            if commodity_id in COMMODITIES:
                commodity_info = COMMODITIES[commodity_id].copy()
                commodity_info['id'] = commodity_id
                commodity_info['marketData'] = results.get(commodity_id)
                commodities_list.append(commodity_info)
        
        return {
            "markets": results,
            "enabled_commodities": enabled,
            "commodities": commodities_list
        }
    except Exception as e:
        logger.error(f"Error fetching all markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.get("/current")
async def get_current_market_legacy():
    """Legacy endpoint - redirects to /market/all"""
    return await get_all_markets()


@market_router.get("/live-ticks")
async def get_live_ticks():
    """
    Get LIVE tick prices from MetaAPI for all available commodities.
    Returns real-time broker prices (Bid/Ask) - NO CACHING!
    """
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        live_prices = {}
        
        connector = None
        if 'MT5_ICMARKETS' in multi_platform.platforms and multi_platform.platforms['MT5_ICMARKETS'].get('active'):
            connector = multi_platform.platforms['MT5_ICMARKETS'].get('connector')
        elif 'MT5_LIBERTEX' in multi_platform.platforms and multi_platform.platforms['MT5_LIBERTEX'].get('active'):
            connector = multi_platform.platforms['MT5_LIBERTEX'].get('connector')
        
        if not connector:
            logger.debug("No MetaAPI connector active for live ticks")
            return {"error": "MetaAPI not connected", "live_prices": {}}
        
        for commodity_id, commodity_info in COMMODITIES.items():
            symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
            
            if symbol:
                tick = await connector.get_symbol_price(symbol)
                if tick:
                    live_prices[commodity_id] = {
                        'commodity': commodity_id,
                        'name': commodity_info.get('name'),
                        'symbol': symbol,
                        'price': tick['price'],
                        'bid': tick['bid'],
                        'ask': tick['ask'],
                        'time': tick['time'],
                        'source': 'MetaAPI_LIVE'
                    }
        
        logger.info(f"✅ Fetched {len(live_prices)} live tick prices")
        
        return {
            "live_prices": live_prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "MetaAPI",
            "count": len(live_prices)
        }
        
    except Exception as e:
        logger.error(f"Error fetching live ticks: {e}")
        return {"error": str(e), "live_prices": {}}


@market_router.get("/ohlcv-simple/{commodity}")
async def get_simple_ohlcv(commodity: str, timeframe: str = "5m", period: str = "1d"):
    """
    Simplified OHLCV endpoint when yfinance is rate-limited.
    Returns recent market data from DB and current live tick.
    """
    try:
        import database as db
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        result = {
            "commodity": commodity,
            "timeframe": timeframe,
            "period": period,
            "data": [],
            "current_price": None,
            "source": "database"
        }
        
        # Get historical data from database
        cursor = await db.market_data_history.find({"commodity": commodity})
        history = await cursor.to_list(500)
        
        if history:
            for item in sorted(history, key=lambda x: x.get('timestamp', '')):
                result["data"].append({
                    'timestamp': item.get('timestamp'),
                    'price': item.get('price'),
                    'rsi': item.get('rsi'),
                    'macd': item.get('macd')
                })
        
        # Try to get current live price
        if commodity in COMMODITIES:
            commodity_info = COMMODITIES[commodity]
            symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
            
            if symbol:
                try:
                    for platform_name in ['MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_DEMO']:
                        price_data = await multi_platform.get_symbol_price(platform_name, symbol)
                        if price_data:
                            result["current_price"] = price_data.get('bid')
                            result["source"] = "live"
                            break
                except:
                    pass
        
        return result
        
    except Exception as e:
        logger.error(f"Error in simple OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.get("/history")
async def get_market_history(limit: int = 100):
    """Get historical market data (snapshot history from DB)"""
    try:
        import database as db
        
        cursor = await db.market_data.find({})
        data = await cursor.to_list(limit)
        
        data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        data = data[:limit]
        
        for item in data:
            if isinstance(item.get('timestamp'), str):
                try:
                    item['timestamp'] = datetime.fromisoformat(
                        item['timestamp'].replace('Z', '+00:00')
                    ).isoformat()
                except:
                    pass
        
        return {"data": list(reversed(data))}
    except Exception as e:
        logger.error(f"Error fetching market history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.get("/ohlcv/{commodity}")
async def get_ohlcv_data(
    commodity: str,
    timeframe: str = "1d",
    period: str = "1mo"
):
    """
    Get OHLCV candlestick data with technical indicators.
    
    Parameters:
    - commodity: Commodity ID (GOLD, WTI_CRUDE, etc.)
    - timeframe: Chart interval (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1wk, 1mo)
    - period: Data period (2h, 1d, 5d, 1wk, 2wk, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
    """
    try:
        from commodity_processor import fetch_historical_ohlcv_async
        
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1wk', '1mo']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        valid_periods = ['2h', '1d', '5d', '1wk', '2wk', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        df = await fetch_historical_ohlcv_async(commodity, timeframe=timeframe, period=period)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for {commodity}")
        
        df_reset = df.reset_index()
        data = []
        
        for _, row in df_reset.iterrows():
            data.append({
                'timestamp': row['Datetime'].isoformat() if 'Datetime' in df_reset.columns else row['Date'].isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'sma_20': float(row['SMA_20']) if 'SMA_20' in row and not pd.isna(row['SMA_20']) else None,
                'ema_20': float(row['EMA_20']) if 'EMA_20' in row and not pd.isna(row['EMA_20']) else None,
                'rsi': float(row['RSI']) if 'RSI' in row and not pd.isna(row['RSI']) else None,
                'macd': float(row['MACD']) if 'MACD' in row and not pd.isna(row['MACD']) else None,
                'macd_signal': float(row['MACD_Signal']) if 'MACD_Signal' in row and not pd.isna(row['MACD_Signal']) else None,
                'macd_histogram': float(row['MACD_Histogram']) if 'MACD_Histogram' in row and not pd.isna(row['MACD_Histogram']) else None,
            })
        
        return {
            'success': True,
            'commodity': commodity,
            'timeframe': timeframe,
            'period': period,
            'data_points': len(data),
            'data': data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLCV data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.get("/hours")
async def get_market_hours_status():
    """Get current market hours status for all enabled commodities"""
    try:
        import database as db
        from commodity_market_hours import get_market_hours, is_market_open
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            settings = {"enabled_commodities": ["WTI_CRUDE"]}
        
        enabled_commodities = settings.get('enabled_commodities', ['WTI_CRUDE'])
        market_hours = await get_market_hours(db)
        
        result = {}
        for commodity in enabled_commodities:
            hours = market_hours.get(commodity, {})
            is_open = is_market_open(commodity, hours)
            result[commodity] = {
                "is_open": is_open,
                "hours": hours,
                "current_time_utc": datetime.now(timezone.utc).isoformat()
            }
        
        return {"market_hours": result}
        
    except Exception as e:
        logger.error(f"Error fetching market hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.get("/hours/all")
async def get_all_market_hours():
    """Get market hours for all commodities"""
    try:
        import database as db
        from commodity_market_hours import get_market_hours
        from commodity_processor import COMMODITIES
        
        market_hours = await get_market_hours(db)
        
        result = {}
        for commodity_id in COMMODITIES.keys():
            result[commodity_id] = market_hours.get(commodity_id, {
                "monday": "00:00-24:00",
                "tuesday": "00:00-24:00",
                "wednesday": "00:00-24:00",
                "thursday": "00:00-24:00",
                "friday": "00:00-24:00",
                "saturday": "closed",
                "sunday": "closed"
            })
        
        return {"market_hours": result, "count": len(result)}
        
    except Exception as e:
        logger.error(f"Error fetching all market hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.post("/hours/update")
async def update_market_hours(commodity: str, hours: Dict[str, str]):
    """Update market hours for a specific commodity"""
    try:
        import database as db
        
        await db.market_hours.update_one(
            {"commodity": commodity},
            {"$set": {"hours": hours, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        return {"success": True, "commodity": commodity, "hours": hours}
        
    except Exception as e:
        logger.error(f"Error updating market hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@market_router.post("/refresh")
async def refresh_market_data(clear_cache: bool = False):
    """Force refresh market data for all commodities"""
    try:
        from commodity_processor import COMMODITIES, fetch_commodity_data
        import database as db
        
        if clear_cache:
            # Clear existing market data
            await db.market_data.delete_many({})
            logger.info("🧹 Market data cache cleared")
        
        refreshed = []
        for commodity_id in COMMODITIES.keys():
            try:
                data = await fetch_commodity_data(commodity_id)
                if data:
                    await db.market_data.update_one(
                        {"commodity": commodity_id},
                        {"$set": data},
                        upsert=True
                    )
                    refreshed.append(commodity_id)
            except Exception as e:
                logger.warning(f"Failed to refresh {commodity_id}: {e}")
        
        return {
            "success": True,
            "cache_cleared": clear_cache,
            "refreshed_count": len(refreshed),
            "refreshed": refreshed
        }
        
    except Exception as e:
        logger.error(f"Error refreshing market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['market_router']
