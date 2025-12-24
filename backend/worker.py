#!/usr/bin/env python3
"""
MetaApi Worker Process
Handles MetaApi connections and monitoring separately from main API
"""

import os
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import database as db_module
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from logging.handlers import RotatingFileHandler
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] WORKER: %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'worker.log'),
            maxBytes=5*1024*1024,
            backupCount=2
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SQLite Database Collections
db = type('DB', (), {
    'trading_settings': db_module.trading_settings,
    'trades': db_module.trades,
    'trade_settings': db_module.trade_settings,
    'market_data': db_module.market_data,
    'market_data_history': db_module.market_data_history
})()

try:
    from metaapi_cloud_sdk import MetaApi
    METAAPI_AVAILABLE = True
    logger.info("✅ MetaApi SDK available")
except ImportError:
    METAAPI_AVAILABLE = False
    logger.warning("⚠️  MetaApi SDK not available")

from trailing_stop import update_trailing_stops, check_stop_loss_triggers
from ai_position_manager import manage_open_positions

try:
    from ai_trading_bot import AITradingBot
    AI_TRADING_BOT_AVAILABLE = True
    logger.info("✅ AI Trading Bot available")
except ImportError:
    AI_TRADING_BOT_AVAILABLE = False
    logger.warning("⚠️  AI Trading Bot not available")


class MetaApiWorker:
    """Worker for MetaApi connections and monitoring"""
    
    def __init__(self):
        self.metaapi = None
        self.accounts = {}
        self.connections = {}
        self.scheduler = AsyncIOScheduler()
        self.running = False
        self.ai_bot = None
        self.bot_task = None
        
    async def initialize(self):
        """Initialize MetaApi connections"""
        if not METAAPI_AVAILABLE:
            logger.error("❌ MetaApi SDK not available")
            return False
            
        try:
            token = os.getenv('METAAPI_TOKEN')
            if not token:
                logger.error("❌ METAAPI_TOKEN not found")
                return False
                
            self.metaapi = MetaApi(token)
            logger.info("✅ MetaApi initialized")
            
            settings = await db.trading_settings.find_one({"id": "trading_settings"})
            if settings:
                await self.connect_platforms(settings)
            else:
                logger.info("⏳ Waiting for configuration...")
            
            return True
        except Exception as e:
            logger.error(f"❌ Init failed: {e}")
            return False
    
    async def connect_platforms(self, settings):
        """Connect enabled platforms"""
        platforms = {
            'MT5_ICMARKETS': settings.get('use_icmarkets_mt5', False),
            'MT5_LIBERTEX': settings.get('use_libertex_mt5', False),
            'BITPANDA': settings.get('use_bitpanda', False)
        }
        
        for platform, enabled in platforms.items():
            if enabled:
                account_id = settings.get(f'{platform.lower()}_account_id')
                if account_id:
                    await self.connect_account(platform, account_id)
    
    async def connect_account(self, platform, account_id):
        """Connect with retry"""
        for attempt in range(3):
            try:
                logger.info(f"🔌 Connecting {platform} (Attempt {attempt + 1}/3)...")
                
                account = await self.metaapi.metatrader_account_api.get_account(account_id)
                
                if account.state != 'DEPLOYED':
                    logger.info(f"📦 Deploying {platform}...")
                    await account.deploy()
                    await asyncio.sleep(5)
                
                if account.connection_status != 'CONNECTED':
                    await account.wait_connected()
                
                connection = account.get_streaming_connection()
                await connection.connect()
                await connection.wait_synchronized()
                
                self.accounts[platform] = account
                self.connections[platform] = connection
                
                logger.info(f"✅ {platform} connected!")
                return True
                
            except Exception as e:
                logger.error(f"❌ {platform} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(5 * (attempt + 1))
        return False
    
    async def start_ai_bot(self):
        """Start AI Trading Bot if enabled"""
        try:
            settings = await db.trading_settings.find_one({"id": "trading_settings"})
            if settings and settings.get('auto_trading', False) and AI_TRADING_BOT_AVAILABLE:
                logger.info("🤖 Auto-Trading enabled - starting AI Trading Bot...")
                self.ai_bot = AITradingBot()
                if await self.ai_bot.initialize():
                    self.bot_task = asyncio.create_task(self.ai_bot.run_forever())
                    logger.info("✅ AI Trading Bot started")
                else:
                    logger.error("❌ AI Trading Bot failed to initialize")
            else:
                logger.info("ℹ️  Auto-Trading disabled or bot not available")
        except Exception as e:
            logger.error(f"⚠️ AI Bot start failed: {e}")
    
    async def start_monitoring(self):
        """Start background tasks"""
        logger.info("🚀 Starting monitoring...")
        
        # Start AI Trading Bot
        await self.start_ai_bot()
        
        self.scheduler.add_job(
            self.update_stops,
            'interval',
            seconds=30,
            id='stops'
        )
        
        self.scheduler.add_job(
            self.manage_positions,
            'interval',
            minutes=5,
            id='positions'
        )
        
        self.scheduler.add_job(
            self.check_connections,
            'interval',
            minutes=2,
            id='health'
        )
        
        self.scheduler.start()
        self.running = True
        logger.info("✅ Monitoring started")
    
    async def update_stops(self):
        try:
            cursor = await db.trades.find({"status": "OPEN"})
            trades = await cursor.to_list(None)
            if trades:
                await update_trailing_stops(db, logger)
                await check_stop_loss_triggers(db, self.connections, logger)
        except Exception as e:
            logger.error(f"Stop update error: {e}")
    
    async def manage_positions(self):
        # V2.5.1: DEAKTIVIERT - ai_position_manager schließt Trades zu früh!
        # Die Logik war zu aggressiv (schloss bei 1% Gewinn + Signalwechsel)
        # try:
        #     await manage_open_positions(db, self.connections, logger)
        # except Exception as e:
        #     logger.error(f"Position mgmt error: {e}")
        pass
    
    async def check_connections(self):
        for platform, connection in list(self.connections.items()):
            try:
                account = self.accounts.get(platform)
                if account and account.connection_status != 'CONNECTED':
                    logger.warning(f"⚠️  Reconnecting {platform}...")
                    await self.connect_account(platform, account.id)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def shutdown(self):
        logger.info("🛑 Shutting down...")
        self.running = False
        
        # Stop AI Bot
        if self.bot_task and not self.bot_task.done():
            self.bot_task.cancel()
            try:
                await self.bot_task
            except asyncio.CancelledError:
                pass
        
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        for connection in self.connections.values():
            try:
                await connection.close()
            except:
                pass


async def main():
    logger.info("=" * 60)
    logger.info("🚀 MetaApi Worker Starting with SQLite...")
    logger.info("=" * 60)
    
    # Initialize SQLite database
    await db_module.init_database()
    logger.info("✅ SQLite Datenbank initialisiert")
    
    worker = MetaApiWorker()
    
    if await worker.initialize():
        await worker.start_monitoring()
        logger.info("✅ Worker ready and monitoring")
        try:
            while worker.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await worker.shutdown()
            await db_module.close_database()
    else:
        logger.error("❌ Worker initialization failed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}")
