"""
🔌 Booner Trade V3.1.0 - Platform Routes

Enthält alle plattformbezogenen API-Endpunkte:
- MT5 Endpoints
- MetaAPI Endpoints
- Bitpanda Endpoints
- Multi-Platform Connector
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

platform_router = APIRouter(tags=["Platforms"])


# ═══════════════════════════════════════════════════════════════════════
# PLATFORMS OVERVIEW
# ═══════════════════════════════════════════════════════════════════════

@platform_router.get("/platforms/status")
async def get_platforms_status():
    """Get status of all trading platforms"""
    try:
        from multi_platform_connector import multi_platform
        
        status = {}
        for name, platform in multi_platform.platforms.items():
            status[name] = {
                "active": platform.get('active', False),
                "type": platform.get('type', 'unknown'),
                "last_connected": platform.get('last_connected'),
                "error": platform.get('error')
            }
        
        return {
            "platforms": status,
            "active_count": len([p for p in status.values() if p['active']]),
            "total_count": len(status)
        }
        
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.post("/platforms/{platform_name}/connect")
async def connect_platform(platform_name: str):
    """Connect to a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        success = await multi_platform.connect_platform(platform_name)
        
        if success:
            return {"success": True, "platform": platform_name, "message": "Connected"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to connect to {platform_name}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.post("/platforms/{platform_name}/disconnect")
async def disconnect_platform(platform_name: str):
    """Disconnect from a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        if platform_name in multi_platform.platforms:
            multi_platform.platforms[platform_name]['active'] = False
            multi_platform.platforms[platform_name]['connector'] = None
            return {"success": True, "platform": platform_name, "message": "Disconnected"}
        else:
            raise HTTPException(status_code=404, detail=f"Platform {platform_name} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/platforms/{platform_name}/account")
async def get_platform_account(platform_name: str):
    """Get account info for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        account_info = await multi_platform.get_account_info(platform_name)
        
        if account_info:
            return {
                "success": True,
                "platform": platform_name,
                "account": account_info
            }
        else:
            return {
                "success": False,
                "platform": platform_name,
                "message": "Could not fetch account info"
            }
        
    except Exception as e:
        logger.error(f"Error getting account info for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/platforms/{platform_name}/positions")
async def get_platform_positions(platform_name: str):
    """Get open positions for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        positions = await multi_platform.get_open_positions(platform_name)
        
        return {
            "success": True,
            "platform": platform_name,
            "positions": positions,
            "count": len(positions)
        }
        
    except Exception as e:
        logger.error(f"Error getting positions for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# MT5 SPECIFIC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@platform_router.get("/mt5/account")
async def get_mt5_account():
    """Get MT5 account information"""
    try:
        from multi_platform_connector import multi_platform
        
        # Try all MT5 platforms
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            account = await multi_platform.get_account_info(platform_name)
            if account:
                return {
                    "success": True,
                    "platform": platform_name,
                    "balance": account.get('balance'),
                    "equity": account.get('equity'),
                    "margin": account.get('margin'),
                    "free_margin": account.get('freeMargin') or account.get('free_margin'),
                    "profit": account.get('profit'),
                    "currency": account.get('currency', 'EUR')
                }
        
        return {"success": False, "message": "No MT5 connection available"}
        
    except Exception as e:
        logger.error(f"Error getting MT5 account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/mt5/positions")
async def get_mt5_positions():
    """Get all open MT5 positions"""
    try:
        from multi_platform_connector import multi_platform
        
        all_positions = []
        
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            try:
                positions = await multi_platform.get_open_positions(platform_name)
                for pos in positions:
                    pos['platform'] = platform_name
                all_positions.extend(positions)
            except:
                pass
        
        return {
            "success": True,
            "positions": all_positions,
            "count": len(all_positions)
        }
        
    except Exception as e:
        logger.error(f"Error getting MT5 positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/mt5/status")
async def get_mt5_status():
    """Get MT5 connection status"""
    try:
        from multi_platform_connector import multi_platform
        
        status = {}
        for name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            if name in multi_platform.platforms:
                platform = multi_platform.platforms[name]
                status[name] = {
                    "active": platform.get('active', False),
                    "has_connector": platform.get('connector') is not None
                }
        
        return {
            "mt5_status": status,
            "any_connected": any(s['active'] for s in status.values())
        }
        
    except Exception as e:
        logger.error(f"Error getting MT5 status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/mt5/symbols")
async def get_mt5_symbols():
    """Get available MT5 symbols"""
    try:
        from commodity_processor import COMMODITIES
        
        symbols = []
        for commodity_id, info in COMMODITIES.items():
            symbol_info = {
                "commodity_id": commodity_id,
                "name": info.get('name'),
                "mt5_libertex": info.get('mt5_libertex_symbol'),
                "mt5_icmarkets": info.get('mt5_icmarkets_symbol')
            }
            symbols.append(symbol_info)
        
        return {"symbols": symbols, "count": len(symbols)}
        
    except Exception as e:
        logger.error(f"Error getting MT5 symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.post("/mt5/order")
async def execute_mt5_order(
    symbol: str,
    action: str,
    volume: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    platform: str = "MT5_LIBERTEX_DEMO"
):
    """Execute a direct MT5 order"""
    try:
        from multi_platform_connector import multi_platform
        
        result = await multi_platform.execute_trade(
            platform_name=platform,
            symbol=symbol,
            action=action,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        if result and result.get('success'):
            return {
                "success": True,
                "order": result,
                "platform": platform
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Order failed: {result.get('error', 'Unknown error') if result else 'No response'}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing MT5 order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.post("/mt5/close/{ticket}")
async def close_mt5_position(ticket: int, platform: str = "MT5_LIBERTEX_DEMO"):
    """Close a specific MT5 position"""
    try:
        from multi_platform_connector import multi_platform
        
        result = await multi_platform.close_position(platform, ticket)
        
        if result and result.get('success'):
            return {"success": True, "ticket": ticket, "message": "Position closed"}
        else:
            raise HTTPException(status_code=400, detail="Failed to close position")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing MT5 position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/mt5/history")
async def get_mt5_history(days: int = 7):
    """Get MT5 trade history"""
    try:
        from multi_platform_connector import multi_platform
        from datetime import timedelta
        
        history = []
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
            try:
                if platform_name in multi_platform.platforms:
                    connector = multi_platform.platforms[platform_name].get('connector')
                    if connector and hasattr(connector, 'get_history_orders_by_time_range'):
                        orders = await connector.get_history_orders_by_time_range(start_time, datetime.now(timezone.utc))
                        if orders:
                            for order in orders:
                                order['platform'] = platform_name
                            history.extend(orders)
            except Exception as e:
                logger.warning(f"Could not get history from {platform_name}: {e}")
        
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting MT5 history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# METAAPI ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@platform_router.post("/metaapi/update-ids")
async def update_metaapi_ids(
    libertex_id: Optional[str] = None,
    icmarkets_id: Optional[str] = None
):
    """Update MetaAPI account IDs"""
    try:
        import os
        from pathlib import Path
        
        env_path = Path(__file__).parent.parent / '.env'
        
        # Read current .env
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update IDs
        new_lines = []
        for line in lines:
            if libertex_id and line.startswith('METAAPI_ACCOUNT_ID='):
                new_lines.append(f'METAAPI_ACCOUNT_ID={libertex_id}\n')
            elif icmarkets_id and line.startswith('METAAPI_ICMARKETS_ACCOUNT_ID='):
                new_lines.append(f'METAAPI_ICMARKETS_ACCOUNT_ID={icmarkets_id}\n')
            else:
                new_lines.append(line)
        
        # Write back
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        return {
            "success": True,
            "message": "MetaAPI IDs updated. Restart backend to apply.",
            "libertex_id": libertex_id,
            "icmarkets_id": icmarkets_id
        }
        
    except Exception as e:
        logger.error(f"Error updating MetaAPI IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# BITPANDA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@platform_router.get("/bitpanda/account")
async def get_bitpanda_account():
    """Get Bitpanda account information"""
    try:
        from multi_platform_connector import multi_platform
        
        if 'BITPANDA' in multi_platform.platforms:
            platform = multi_platform.platforms['BITPANDA']
            return {
                "success": True,
                "connected": platform.get('active', False),
                "balance": platform.get('balance', 0),
                "currency": "EUR"
            }
        
        return {"success": False, "message": "Bitpanda not configured"}
        
    except Exception as e:
        logger.error(f"Error getting Bitpanda account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.get("/bitpanda/status")
async def get_bitpanda_status():
    """Get Bitpanda connection status"""
    try:
        from multi_platform_connector import multi_platform
        
        if 'BITPANDA' in multi_platform.platforms:
            platform = multi_platform.platforms['BITPANDA']
            return {
                "configured": True,
                "active": platform.get('active', False),
                "type": platform.get('type', 'crypto')
            }
        
        return {"configured": False, "active": False}
        
    except Exception as e:
        logger.error(f"Error getting Bitpanda status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@platform_router.post("/sync/positions")
async def sync_all_positions():
    """Sync positions across all platforms"""
    try:
        from multi_platform_connector import multi_platform
        import database as db
        
        synced = []
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        for platform in active_platforms:
            try:
                positions = await multi_platform.get_open_positions(platform)
                synced.append({
                    "platform": platform,
                    "positions": len(positions)
                })
            except:
                synced.append({
                    "platform": platform,
                    "positions": 0,
                    "error": "Failed to sync"
                })
        
        return {
            "success": True,
            "synced": synced,
            "total_positions": sum(s['positions'] for s in synced)
        }
        
    except Exception as e:
        logger.error(f"Error syncing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['platform_router']
