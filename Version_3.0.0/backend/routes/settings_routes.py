"""
⚙️ Booner Trade V3.1.0 - Settings Routes

Enthält alle einstellungsbezogenen API-Endpunkte:
- Trading Settings
- Bot Control
- Risk Settings
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

settings_router = APIRouter(tags=["Settings"])


# ═══════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════

class TradingSettingsUpdate(BaseModel):
    """Model for updating trading settings"""
    auto_trading: Optional[bool] = None
    trading_mode: Optional[str] = None  # conservative, standard, aggressive
    trading_strategy: Optional[str] = None
    enabled_commodities: Optional[List[str]] = None
    active_platforms: Optional[List[str]] = None
    default_platform: Optional[str] = None
    lot_size: Optional[float] = None
    max_portfolio_risk_percent: Optional[float] = None
    max_positions: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@settings_router.get("/settings")
async def get_settings():
    """Get current trading settings"""
    try:
        import database as db
        from commodity_processor import COMMODITIES
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if not settings:
            # Return defaults
            settings = {
                "id": "trading_settings",
                "auto_trading": False,
                "trading_mode": "standard",
                "trading_strategy": "DAY",
                "enabled_commodities": list(COMMODITIES.keys()),
                "active_platforms": ["MT5_LIBERTEX_DEMO"],
                "default_platform": "MT5_LIBERTEX_DEMO",
                "lot_size": 0.01,
                "max_portfolio_risk_percent": 20.0,
                "max_positions": 5
            }
        
        # Ensure all 20 commodities are included
        if 'enabled_commodities' not in settings or len(settings['enabled_commodities']) < 20:
            settings['enabled_commodities'] = list(COMMODITIES.keys())
        
        return settings
        
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@settings_router.post("/settings")
async def update_settings(updates: TradingSettingsUpdate):
    """Update trading settings"""
    try:
        import database as db
        
        # Get current settings
        current = await db.trading_settings.find_one({"id": "trading_settings"})
        if not current:
            current = {"id": "trading_settings"}
        
        # Apply updates
        update_dict = updates.model_dump(exclude_none=True)
        update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        for key, value in update_dict.items():
            current[key] = value
        
        # Save
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": current},
            upsert=True
        )
        
        # Update trading mode in intelligence system
        if 'trading_mode' in update_dict:
            try:
                from autonomous_trading_intelligence import AutonomousTradingIntelligence
                AutonomousTradingIntelligence.set_trading_mode(update_dict['trading_mode'])
                logger.info(f"✅ Trading mode updated to: {update_dict['trading_mode']}")
            except Exception as e:
                logger.warning(f"Could not update trading mode: {e}")
        
        return current
        
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@settings_router.post("/settings/reset")
async def reset_settings():
    """Reset settings to defaults"""
    try:
        import database as db
        from commodity_processor import COMMODITIES
        
        defaults = {
            "id": "trading_settings",
            "auto_trading": False,
            "trading_mode": "standard",
            "trading_strategy": "DAY",
            "enabled_commodities": list(COMMODITIES.keys()),
            "active_platforms": ["MT5_LIBERTEX_DEMO"],
            "default_platform": "MT5_LIBERTEX_DEMO",
            "lot_size": 0.01,
            "max_portfolio_risk_percent": 20.0,
            "max_positions": 5,
            "reset_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": defaults},
            upsert=True
        )
        
        return {"success": True, "message": "Settings reset to defaults", "settings": defaults}
        
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# BOT CONTROL
# ═══════════════════════════════════════════════════════════════════════

@settings_router.get("/bot/status")
async def get_bot_status():
    """Get trading bot status"""
    try:
        import database as db
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Check if multi_bot_manager is running
        bot_running = False
        try:
            from multi_bot_system import multi_bot_manager
            if multi_bot_manager:
                bot_running = multi_bot_manager.is_running
        except:
            pass
        
        return {
            "auto_trading": settings.get('auto_trading', False) if settings else False,
            "bot_running": bot_running,
            "trading_mode": settings.get('trading_mode', 'standard') if settings else 'standard',
            "active_platforms": settings.get('active_platforms', []) if settings else [],
            "enabled_commodities": len(settings.get('enabled_commodities', [])) if settings else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@settings_router.post("/bot/start")
async def start_bot():
    """Start the trading bot"""
    try:
        import database as db
        from database_v2 import db_manager
        from multi_bot_system import MultiBotManager
        
        global multi_bot_manager
        
        # Update settings
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"auto_trading": True}},
            upsert=True
        )
        
        # Start bot
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        async def get_settings():
            return await db.trading_settings.find_one({"id": "trading_settings"})
        
        multi_bot_manager = MultiBotManager(db_manager, get_settings)
        await multi_bot_manager.start_all()
        
        return {"success": True, "message": "Trading bot started"}
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@settings_router.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    try:
        import database as db
        
        global multi_bot_manager
        
        # Update settings
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"auto_trading": False}}
        )
        
        # Stop bot
        if multi_bot_manager:
            await multi_bot_manager.stop_all()
        
        return {"success": True, "message": "Trading bot stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# RISK SETTINGS
# ═══════════════════════════════════════════════════════════════════════

@settings_router.get("/risk/status")
async def get_risk_status():
    """Get current risk status"""
    try:
        import database as db
        from multi_platform_connector import multi_platform
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        max_risk = settings.get('max_portfolio_risk_percent', 20.0) if settings else 20.0
        
        # Calculate current exposure
        total_exposure = 0
        total_balance = 0
        
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        for platform in active_platforms:
            try:
                account = await multi_platform.get_account_info(platform)
                if account:
                    total_balance += account.get('balance', 0)
                
                positions = await multi_platform.get_open_positions(platform)
                for pos in positions:
                    price = pos.get('price_open') or pos.get('openPrice', 0)
                    volume = pos.get('volume', 0)
                    total_exposure += price * volume
            except:
                pass
        
        exposure_percent = (total_exposure / total_balance * 100) if total_balance > 0 else 0
        
        return {
            "max_risk_percent": max_risk,
            "current_exposure_percent": round(exposure_percent, 2),
            "total_exposure": round(total_exposure, 2),
            "total_balance": round(total_balance, 2),
            "risk_available": max_risk - exposure_percent,
            "can_open_new_trades": exposure_percent < max_risk
        }
        
    except Exception as e:
        logger.error(f"Error getting risk status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global variable for bot manager
multi_bot_manager = None

# Export
__all__ = ['settings_router', 'TradingSettingsUpdate']
