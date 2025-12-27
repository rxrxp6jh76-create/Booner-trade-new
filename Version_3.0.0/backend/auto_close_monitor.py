"""
Auto-Close Monitor - Schließt Trades automatisch wenn Ziel erreicht
Für Trades die kein Take Profit im MT5 haben
"""
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
from logging.handlers import RotatingFileHandler
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'monitor.log'),
            maxBytes=5*1024*1024,
            backupCount=2
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def monitor_and_close_trades():
    """Monitor open trades and close if target reached"""
    
    # Connect to DB
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.getenv('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Get settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            logger.warning("No settings found")
            return
        
        tp_percent = settings.get('take_profit_percent', 0.2)
        
        # Get open trades from MT5
        from multi_platform_connector import multi_platform
        
        platforms = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']
        closed_count = 0
        
        for platform in platforms:
            try:
                positions = await multi_platform.get_open_positions(platform)
                
                for pos in positions:
                    entry_price = pos.get('price_open') or pos.get('openPrice') or pos.get('entry_price')
                    current_price = pos.get('price_current') or pos.get('currentPrice') or pos.get('price')
                    pos_type = pos.get('type')
                    ticket = pos.get('ticket') or pos.get('id')
                    
                    if not entry_price or not current_price:
                        continue
                    
                    # Calculate target
                    if 'BUY' in str(pos_type).upper():
                        target_price = entry_price * (1 + tp_percent / 100)
                        target_reached = current_price >= target_price
                    else:  # SELL
                        target_price = entry_price * (1 - tp_percent / 100)
                        target_reached = current_price <= target_price
                    
                    # Close if target reached
                    if target_reached:
                        logger.info(f"🎯 Target reached for {ticket}! Entry={entry_price}, Current={current_price}, Target={target_price}")
                        
                        # Close position
                        success = await multi_platform.close_position(platform, str(ticket))
                        
                        if success:
                            logger.info(f"✅ Auto-closed position {ticket}")
                            closed_count += 1
                        else:
                            logger.error(f"❌ Failed to close position {ticket}")
                
            except Exception as e:
                logger.error(f"Error monitoring {platform}: {e}")
        
        if closed_count > 0:
            logger.info(f"✅ Auto-closed {closed_count} positions that reached target")
        else:
            logger.info("✅ No positions reached target yet")
        
    except Exception as e:
        logger.error(f"Error in monitor: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(monitor_and_close_trades())
