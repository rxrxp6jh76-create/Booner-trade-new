"""
Trailing Stop Logic for Dynamic Stop Loss Management
V2.3.37 FIX: Korrigiert für SQLite (vorher MongoDB-Syntax)
"""

import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


async def update_trailing_stops(db, current_prices: Dict[str, float], settings):
    """
    Update trailing stops for all open positions
    
    Args:
        db: Database manager with trades_db
        current_prices: Dict mapping commodity_id to current price
        settings: Trading settings with trailing stop configuration
    """
    if not settings or not settings.get('use_trailing_stop', False):
        return
    
    trailing_distance = settings.get('trailing_stop_distance', 1.5) / 100  # Convert % to decimal
    
    try:
        # V2.3.37 FIX: Korrigiert für SQLite - Hole offene Trades aus der DB
        open_trades = await db.trades_db.get_open_trades() if hasattr(db, 'trades_db') else []
        
        if not open_trades:
            return
        
        updated_count = 0
        for trade in open_trades:
            commodity = trade.get('commodity', 'WTI_CRUDE')
            current_price = current_prices.get(commodity)
            
            if not current_price:
                continue
            
            trade_type = trade.get('type')
            entry_price = trade.get('entry_price')
            current_stop_loss = trade.get('stop_loss')
            
            if not entry_price:
                continue
            
            new_stop_loss = None
            
            # BUY Trade: Move stop loss UP if price moves UP
            if trade_type == 'BUY':
                # Calculate new trailing stop (below current price)
                potential_stop = current_price * (1 - trailing_distance)
                
                # Only update if new stop is higher than current stop (or no stop set)
                if not current_stop_loss or potential_stop > current_stop_loss:
                    new_stop_loss = round(potential_stop, 2)
            
            # SELL Trade: Move stop loss DOWN if price moves DOWN
            elif trade_type == 'SELL':
                # Calculate new trailing stop (above current price)
                potential_stop = current_price * (1 + trailing_distance)
                
                # Only update if new stop is lower than current stop (or no stop set)
                if not current_stop_loss or potential_stop < current_stop_loss:
                    new_stop_loss = round(potential_stop, 2)
            
            # Update stop loss if changed
            if new_stop_loss and new_stop_loss != current_stop_loss:
                try:
                    # V2.3.37 FIX: Korrigiert für SQLite
                    if hasattr(db, 'trades_db'):
                        await db.trades_db.update_trade_stop_loss(trade['id'], new_stop_loss)
                    updated_count += 1
                    
                    logger.info(
                        f"Trailing Stop updated for {commodity} {trade_type} trade: "
                        f"Stop Loss {current_stop_loss or 'N/A'} -> {new_stop_loss} "
                        f"(Price: {current_price}, Distance: {trailing_distance * 100:.1f}%)"
                    )
                except Exception as update_err:
                    logger.debug(f"Could not update trailing stop: {update_err}")
        
        if updated_count > 0:
            logger.info(f"Updated {updated_count} trailing stops")
    
    except Exception as e:
        logger.error(f"Error updating trailing stops: {e}")


async def check_stop_loss_triggers(db, current_prices: Dict[str, float]) -> List[Dict]:
    """
    Check if any positions should be closed due to stop loss
    
    Args:
        db: Database manager with trades_db
        current_prices: Dict mapping commodity_id to current price
    
    Returns:
        List of trade dicts that should be closed
    """
    try:
        # V2.3.37 FIX: Korrigiert für SQLite - Hole offene Trades aus der DB
        open_trades = await db.trades_db.get_open_trades() if hasattr(db, 'trades_db') else []
        
        if not open_trades:
            return []
        
        trades_to_close = []
        
        for trade in open_trades:
            commodity = trade.get('commodity', 'WTI_CRUDE')
            current_price = current_prices.get(commodity)
            
            if not current_price:
                continue
            
            trade_type = trade.get('type')
            stop_loss = trade.get('stop_loss')
            take_profit = trade.get('take_profit')
            
            # Check stop loss
            if stop_loss:
                if trade_type == 'BUY' and current_price <= stop_loss:
                    trades_to_close.append({
                        'id': trade['id'],
                        'reason': 'STOP_LOSS',
                        'exit_price': current_price
                    })
                    logger.info(f"Stop Loss triggered for {commodity} BUY: {current_price} <= {stop_loss}")
                
                elif trade_type == 'SELL' and current_price >= stop_loss:
                    trades_to_close.append({
                        'id': trade['id'],
                        'reason': 'STOP_LOSS',
                        'exit_price': current_price
                    })
                    logger.info(f"Stop Loss triggered for {commodity} SELL: {current_price} >= {stop_loss}")
            
            # Check take profit
            if take_profit:
                if trade_type == 'BUY' and current_price >= take_profit:
                    trades_to_close.append({
                        'id': trade['id'],
                        'reason': 'TAKE_PROFIT',
                        'exit_price': current_price
                    })
                    logger.info(f"Take Profit triggered for {commodity} BUY: {current_price} >= {take_profit}")
                
                elif trade_type == 'SELL' and current_price <= take_profit:
                    trades_to_close.append({
                        'id': trade['id'],
                        'reason': 'TAKE_PROFIT',
                        'exit_price': current_price
                    })
                    logger.info(f"Take Profit triggered for {commodity} SELL: {current_price} <= {take_profit}")
        
        return trades_to_close
    
    except Exception as e:
        logger.error(f"Error checking stop loss triggers: {e}")
        return []
