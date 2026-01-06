"""
📈 Booner Trade V3.1.0 - Trade Routes

Enthält alle handelsbezogenen API-Endpunkte:
- Trade-Ausführung
- Trade-Liste
- Trade-Schließung
- Trade-Statistiken
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

trade_router = APIRouter(prefix="/trades", tags=["Trades"])


# ═══════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════

class TradeExecuteRequest(BaseModel):
    """Request model for trade execution"""
    trade_type: str = Field(..., description="BUY or SELL")
    price: float = Field(..., description="Entry price")
    commodity: str = Field(..., description="Commodity ID")
    quantity: Optional[float] = Field(None, description="Position size (auto if None)")
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = "day"


class TradeCloseRequest(BaseModel):
    """Request model for closing a trade"""
    trade_id: str
    reason: Optional[str] = "manual"


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL MAPPING
# ═══════════════════════════════════════════════════════════════════════

SYMBOL_TO_COMMODITY = {
    'XAUUSD': 'GOLD',
    'XAGUSD': 'SILVER',
    'XPTUSD': 'PLATINUM',
    'XPDUSD': 'PALLADIUM',
    'PL': 'PLATINUM',
    'PA': 'PALLADIUM',
    'USOILCash': 'WTI_CRUDE',
    'WTI_F6': 'WTI_CRUDE',
    'UKOUSD': 'BRENT_CRUDE',
    'CL': 'BRENT_CRUDE',
    'NGASCash': 'NATURAL_GAS',
    'NG': 'NATURAL_GAS',
    'HGF6': 'COPPER',
    'COPPER': 'COPPER',
    'BTCUSD': 'BITCOIN',
    'ETHUSD': 'ETHEREUM',
    'WHEAT': 'WHEAT',
    'CORN': 'CORN',
    'SOYBEAN': 'SOYBEANS',
    'COFFEE': 'COFFEE',
    'SUGAR': 'SUGAR',
    'COTTON': 'COTTON',
    'COCOA': 'COCOA',
    'ZINC': 'ZINC',
    'USDJPY': 'USDJPY',
    'US100Cash': 'NASDAQ100'
}


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@trade_router.get("/list")
async def get_trades(status: Optional[str] = None):
    """Get all trades - real MT5 positions + closed DB trades"""
    try:
        import database as db
        from multi_platform_connector import multi_platform
        
        logger.info("🔍 /trades/list aufgerufen")
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        # Load trade settings for fast lookup
        try:
            from database import trade_settings as trade_settings_collection
            cursor = await trade_settings_collection.find({})
            all_settings = await cursor.to_list(10000)
            trade_settings_map = {ts['trade_id']: ts for ts in all_settings if 'trade_id' in ts}
        except Exception as e:
            logger.warning(f"Could not load trade settings: {e}")
            trade_settings_map = {}
        
        # Load ticket-strategy mapping
        ticket_strategy_map = {}
        try:
            from database_v2 import db_manager
            ticket_strategy_map = await db_manager.trades_db.get_all_ticket_strategies()
        except:
            pass
        
        live_mt5_positions = []
        
        for platform_name in active_platforms:
            if 'MT5_LIBERTEX' in platform_name or 'MT5_ICMARKETS' in platform_name:
                try:
                    positions = await multi_platform.get_open_positions(platform_name)
                    
                    for pos in positions:
                        mt5_symbol = pos.get('symbol', 'UNKNOWN')
                        commodity_id = SYMBOL_TO_COMMODITY.get(mt5_symbol, mt5_symbol)
                        ticket = str(pos.get('ticket', pos.get('id')))
                        
                        trade_id = f"mt5_{ticket}"
                        ts = trade_settings_map.get(trade_id, {})
                        
                        # Determine strategy
                        strategy = ts.get('strategy') or ticket_strategy_map.get(ticket) or 'day'
                        
                        trade = {
                            'id': trade_id,
                            'trade_type': 'BUY' if pos.get('type') == 'POSITION_TYPE_BUY' else 'SELL',
                            'commodity': commodity_id,
                            'entry_price': pos.get('price_open') or pos.get('openPrice'),
                            'current_price': pos.get('current_price') or pos.get('currentPrice'),
                            'quantity': pos.get('volume'),
                            'profit': pos.get('profit'),
                            'status': 'OPEN',
                            'platform': platform_name,
                            'ticket': ticket,
                            'stop_loss': ts.get('stop_loss') or pos.get('stopLoss'),
                            'take_profit': ts.get('take_profit') or pos.get('takeProfit'),
                            'strategy': strategy,
                            'open_time': pos.get('time') or pos.get('openTime'),
                            'source': 'MT5_LIVE'
                        }
                        live_mt5_positions.append(trade)
                        
                except Exception as e:
                    logger.error(f"Error fetching positions from {platform_name}: {e}")
        
        # Get closed trades from DB
        closed_trades = []
        try:
            cursor = await db.trades.find({"status": "CLOSED"})
            closed_list = await cursor.to_list(100)
            for trade in closed_list:
                trade['source'] = 'DB_CLOSED'
                closed_trades.append(trade)
        except:
            pass
        
        # Combine and filter
        all_trades = live_mt5_positions + closed_trades
        
        if status:
            all_trades = [t for t in all_trades if t.get('status') == status]
        
        return {
            "trades": all_trades,
            "count": len(all_trades),
            "live_count": len(live_mt5_positions),
            "closed_count": len(closed_trades)
        }
        
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.get("/stats")
async def get_trade_stats():
    """Get trading statistics"""
    try:
        import database as db
        from multi_platform_connector import multi_platform
        
        stats = {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0.0,
            "win_rate": 0.0,
            "avg_profit": 0.0,
            "avg_loss": 0.0
        }
        
        # Get trades
        trades_response = await get_trades()
        trades = trades_response.get("trades", [])
        
        stats["total_trades"] = len(trades)
        stats["open_trades"] = len([t for t in trades if t.get('status') == 'OPEN'])
        stats["closed_trades"] = len([t for t in trades if t.get('status') == 'CLOSED'])
        
        closed_with_profit = [t for t in trades if t.get('status') == 'CLOSED' and t.get('profit') is not None]
        
        if closed_with_profit:
            stats["winning_trades"] = len([t for t in closed_with_profit if t['profit'] > 0])
            stats["losing_trades"] = len([t for t in closed_with_profit if t['profit'] < 0])
            stats["total_profit"] = sum(t['profit'] for t in closed_with_profit)
            
            if len(closed_with_profit) > 0:
                stats["win_rate"] = (stats["winning_trades"] / len(closed_with_profit)) * 100
            
            winners = [t['profit'] for t in closed_with_profit if t['profit'] > 0]
            losers = [t['profit'] for t in closed_with_profit if t['profit'] < 0]
            
            if winners:
                stats["avg_profit"] = sum(winners) / len(winners)
            if losers:
                stats["avg_loss"] = sum(losers) / len(losers)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching trade stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/close")
async def close_trade(request: TradeCloseRequest):
    """Close a trade by ID"""
    try:
        from multi_platform_connector import multi_platform
        import database as db
        
        trade_id = request.trade_id
        logger.info(f"🔴 Close trade request: {trade_id}")
        
        # Check if MT5 trade
        if trade_id.startswith("mt5_"):
            ticket = trade_id.replace("mt5_", "")
            
            # Try to close on all active platforms
            settings = await db.trading_settings.find_one({"id": "trading_settings"})
            active_platforms = settings.get('active_platforms', []) if settings else []
            
            for platform in active_platforms:
                if 'MT5' in platform:
                    try:
                        result = await multi_platform.close_position(platform, int(ticket))
                        if result and result.get('success'):
                            logger.info(f"✅ Trade {ticket} closed on {platform}")
                            
                            # Update DB
                            await db.trades.update_one(
                                {"id": trade_id},
                                {"$set": {
                                    "status": "CLOSED",
                                    "closed_at": datetime.now(timezone.utc).isoformat(),
                                    "close_reason": request.reason
                                }}
                            )
                            
                            return {
                                "success": True,
                                "trade_id": trade_id,
                                "platform": platform,
                                "message": f"Trade {ticket} closed successfully"
                            }
                    except Exception as e:
                        logger.warning(f"Could not close on {platform}: {e}")
            
            raise HTTPException(status_code=404, detail=f"Trade {ticket} not found on any platform")
        
        # DB trade
        else:
            await db.trades.update_one(
                {"id": trade_id},
                {"$set": {
                    "status": "CLOSED",
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "close_reason": request.reason
                }}
            )
            return {"success": True, "trade_id": trade_id, "message": "Trade marked as closed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/close/{trade_id}")
async def close_trade_by_id(trade_id: str, reason: str = "manual"):
    """Close a trade by path parameter"""
    return await close_trade(TradeCloseRequest(trade_id=trade_id, reason=reason))


@trade_router.delete("/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a trade from database"""
    try:
        import database as db
        
        result = await db.trades.delete_one({"id": trade_id})
        
        if result.deleted_count > 0:
            return {"success": True, "message": f"Trade {trade_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/delete-all-closed")
async def delete_all_closed_trades():
    """Delete all closed trades from database"""
    try:
        import database as db
        
        result = await db.trades.delete_many({"status": "CLOSED"})
        
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "message": f"Deleted {result.deleted_count} closed trades"
        }
        
    except Exception as e:
        logger.error(f"Error deleting closed trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/close-all-profitable")
async def close_all_profitable_trades():
    """
    V3.2.7: Schließt alle Trades die aktuell im Plus sind.
    Iteriert über alle offenen MT5 Positionen und schließt profitable.
    """
    try:
        from multi_platform_connector import multi_platform
        import database as db
        
        logger.info("💰 Close All Profitable Trades gestartet...")
        
        # Hole Settings für aktive Plattformen
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', ['MT5_Libertex', 'MT5_ICMarkets']) if settings else ['MT5_Libertex', 'MT5_ICMarkets']
        
        closed_trades = []
        skipped_trades = []
        errors = []
        total_profit = 0
        
        for platform in active_platforms:
            if 'MT5' not in platform:
                continue
                
            try:
                # Hole alle Positionen für diese Plattform
                positions = await multi_platform.get_positions(platform)
                
                if not positions:
                    continue
                
                logger.info(f"📊 {platform}: {len(positions)} offene Positionen gefunden")
                
                for pos in positions:
                    try:
                        profit = pos.get('profit') or pos.get('unrealizedProfit') or 0
                        ticket = pos.get('id') or pos.get('ticket')
                        symbol = pos.get('symbol', 'UNKNOWN')
                        
                        # Nur profitable Trades schließen
                        if profit > 0:
                            logger.info(f"💰 Schließe profitablen Trade: {symbol} (Ticket: {ticket}, Profit: €{profit:.2f})")
                            
                            # Trade schließen
                            result = await multi_platform.close_position(platform, str(ticket))
                            
                            if result:
                                closed_trades.append({
                                    'ticket': ticket,
                                    'symbol': symbol,
                                    'profit': profit,
                                    'platform': platform
                                })
                                total_profit += profit
                                logger.info(f"✅ Trade {ticket} geschlossen: +€{profit:.2f}")
                            else:
                                errors.append({
                                    'ticket': ticket,
                                    'symbol': symbol,
                                    'error': 'Close failed'
                                })
                        else:
                            skipped_trades.append({
                                'ticket': ticket,
                                'symbol': symbol,
                                'profit': profit,
                                'reason': 'Nicht im Plus' if profit < 0 else 'Breakeven'
                            })
                            
                    except Exception as e:
                        logger.error(f"❌ Fehler beim Schließen von {pos.get('symbol')}: {e}")
                        errors.append({
                            'ticket': pos.get('id'),
                            'symbol': pos.get('symbol'),
                            'error': str(e)
                        })
                        
            except Exception as e:
                logger.error(f"❌ Fehler bei Plattform {platform}: {e}")
                errors.append({
                    'platform': platform,
                    'error': str(e)
                })
        
        # Zusammenfassung loggen
        logger.info(f"💰 Close All Profitable abgeschlossen:")
        logger.info(f"   ✅ Geschlossen: {len(closed_trades)}")
        logger.info(f"   ⏭️ Übersprungen: {len(skipped_trades)}")
        logger.info(f"   ❌ Fehler: {len(errors)}")
        logger.info(f"   💵 Gesamt-Profit: €{total_profit:.2f}")
        
        return {
            "success": True,
            "closed_count": len(closed_trades),
            "skipped_count": len(skipped_trades),
            "error_count": len(errors),
            "total_profit": round(total_profit, 2),
            "closed_trades": closed_trades,
            "skipped_trades": skipped_trades[:10],  # Nur erste 10 zur Übersicht
            "errors": errors,
            "message": f"✅ {len(closed_trades)} profitable Trades geschlossen, Gesamt-Profit: €{total_profit:.2f}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error closing profitable trades: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/{trade_id}/settings")
async def update_trade_settings(trade_id: str, settings: Dict[str, Any]):
    """Update settings for a specific trade"""
    try:
        import database as db
        from database import trade_settings as trade_settings_collection
        
        settings['trade_id'] = trade_id
        settings['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        await trade_settings_collection.update_one(
            {"trade_id": trade_id},
            {"$set": settings},
            upsert=True
        )
        
        return {"success": True, "trade_id": trade_id, "settings": settings}
        
    except Exception as e:
        logger.error(f"Error updating trade settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.get("/{trade_id}/settings")
async def get_trade_settings(trade_id: str):
    """Get settings for a specific trade"""
    try:
        from database import trade_settings as trade_settings_collection
        
        settings = await trade_settings_collection.find_one({"trade_id": trade_id})
        
        if settings:
            return settings
        else:
            return {"trade_id": trade_id, "message": "No settings found"}
        
    except Exception as e:
        logger.error(f"Error fetching trade settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/{trade_id}/update-strategy")
async def update_trade_strategy(trade_id: str, strategy: str):
    """Update the strategy for a specific trade"""
    try:
        from database_v2 import db_manager
        import database as db
        
        # Update in database_v2
        ticket = trade_id.replace("mt5_", "")
        await db_manager.trades_db.save_ticket_strategy(ticket, strategy)
        
        # Also update trade_settings
        from database import trade_settings as trade_settings_collection
        await trade_settings_collection.update_one(
            {"trade_id": trade_id},
            {"$set": {"strategy": strategy, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        return {"success": True, "trade_id": trade_id, "strategy": strategy}
        
    except Exception as e:
        logger.error(f"Error updating trade strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/sync-settings")
async def sync_trade_settings():
    """Sync trade settings with current MT5 positions"""
    try:
        import database as db
        from multi_platform_connector import multi_platform
        from database import trade_settings as trade_settings_collection
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        synced = []
        
        for platform in active_platforms:
            if 'MT5' in platform:
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    
                    for pos in positions:
                        ticket = str(pos.get('ticket', pos.get('id')))
                        trade_id = f"mt5_{ticket}"
                        
                        # Check if settings exist
                        existing = await trade_settings_collection.find_one({"trade_id": trade_id})
                        
                        if not existing:
                            # Create default settings
                            new_settings = {
                                "trade_id": trade_id,
                                "ticket": ticket,
                                "platform": platform,
                                "symbol": pos.get('symbol'),
                                "stop_loss": pos.get('stopLoss'),
                                "take_profit": pos.get('takeProfit'),
                                "strategy": "day",
                                "created_at": datetime.now(timezone.utc).isoformat()
                            }
                            await trade_settings_collection.insert_one(new_settings)
                            synced.append(trade_id)
                            
                except Exception as e:
                    logger.warning(f"Error syncing {platform}: {e}")
        
        return {
            "success": True,
            "synced_count": len(synced),
            "synced_trades": synced
        }
        
    except Exception as e:
        logger.error(f"Error syncing trade settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@trade_router.post("/cleanup")
async def cleanup_trades():
    """Clean up orphaned and old trades"""
    try:
        import database as db
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Delete old closed trades
        result = await db.trades.delete_many({
            "status": "CLOSED",
            "closed_at": {"$lt": cutoff.isoformat()}
        })
        
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "message": f"Cleaned up {result.deleted_count} old trades"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['trade_router', 'TradeExecuteRequest', 'TradeCloseRequest', 'SYMBOL_TO_COMMODITY']
