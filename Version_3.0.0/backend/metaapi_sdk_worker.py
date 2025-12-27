"""
MetaAPI SDK Worker - Separater Prozess für SDK Verbindungen
Dieser Worker läuft in einem eigenen Prozess mit eigenem Event Loop
um Konflikte mit dem Haupt-FastAPI Event Loop zu vermeiden.
"""

import asyncio
import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

# Setup Logging with Rotation
from logging.handlers import RotatingFileHandler
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            log_dir / 'metaapi_worker.log',
            maxBytes=5*1024*1024,
            backupCount=2
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('metaapi_sdk_worker')

# Set Event Loop Policy for macOS compatibility
if sys.platform == 'darwin':  # macOS
    logger.info("🍎 Setting macOS-compatible asyncio policy")
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


class MetaAPISDKWorker:
    """
    Dedizierter Worker für MetaAPI SDK Verbindungen
    Läuft in eigenem Prozess, eigener Event Loop
    """
    
    def __init__(self, token: str, account_id: str):
        self.token = token
        self.account_id = account_id
        self.api = None
        self.account = None
        self.connection = None
        self.connected = False
        
    async def setup_sdk(self):
        """SDK initialisieren mit macOS-spezifischen Fixes"""
        try:
            logger.info(f"🔧 Initializing MetaAPI SDK for {self.account_id}")
            
            # DESKTOP FIX: Monkey-patch für .metaapi Cache
            current_path = Path(__file__).parent
            if '/Applications/' in str(current_path) or '.app/Contents/Resources' in str(current_path):
                logger.info("🔧 Desktop App detected - applying monkey-patch...")
                
                from metaapi_cloud_sdk.metaapi.filesystem_history_database import FilesystemHistoryDatabase
                
                user_metaapi_dir = Path.home() / 'Library' / 'Application Support' / 'Booner Trade' / '.metaapi-sdk-cache'
                user_metaapi_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"📁 MetaAPI cache directory: {user_metaapi_dir}")
                
                original_get_db_location = FilesystemHistoryDatabase._get_db_location
                
                async def patched_get_db_location(self, account_id, application):
                    return str(user_metaapi_dir / f"{account_id}-{application}.db")
                
                FilesystemHistoryDatabase._get_db_location = patched_get_db_location
                logger.info("✅ Monkey-patch applied successfully")
            
            # Initialize SDK with optimal timeouts for macOS
            from metaapi_cloud_sdk import MetaApi
            
            opts = {
                'application': 'BooneTrader',
                'requestTimeout': 120000,  # 2 minutes
                'connectTimeout': 120000,  # 2 minutes
                'retryOpts': {
                    'retries': 5,
                    'minDelayInSeconds': 2,
                    'maxDelayInSeconds': 60
                }
            }
            
            self.api = MetaApi(self.token, opts)
            logger.info("✅ MetaAPI SDK initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ SDK setup failed: {e}", exc_info=True)
            return False
    
    async def connect(self):
        """Verbindung herstellen"""
        try:
            logger.info(f"🔄 Connecting to account {self.account_id}...")
            
            # Get account
            self.account = await self.api.metatrader_account_api.get_account(self.account_id)
            logger.info(f"✅ Account retrieved: {self.account_id}")
            
            # Get streaming connection
            self.connection = self.account.get_streaming_connection()
            logger.info("✅ Streaming connection object created")
            
            # Connect
            await self.connection.connect()
            logger.info("✅ WebSocket connected")
            
            # Wait for synchronization
            logger.info("⏳ Waiting for terminal synchronization...")
            await self.connection.wait_synchronized()
            logger.info("✅ Terminal synchronized")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}", exc_info=True)
            self.connected = False
            return False
    
    async def get_account_info(self):
        """Account Informationen abrufen"""
        try:
            if not self.connected or not self.connection:
                return None
            
            terminal_state = self.connection.terminal_state
            account_info = terminal_state.account_information
            
            if not account_info:
                return None
            
            return {
                'balance': account_info.get('balance', 0),
                'equity': account_info.get('equity', 0),
                'margin': account_info.get('margin', 0),
                'freeMargin': account_info.get('freeMargin', 0),
                'leverage': account_info.get('leverage', 1),
                'connected': terminal_state.connected,
                'connectedToBroker': terminal_state.connected_to_broker
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def get_positions(self):
        """Offene Positionen abrufen"""
        try:
            if not self.connected or not self.connection:
                return []
            
            terminal_state = self.connection.terminal_state
            positions = terminal_state.positions
            
            return [{
                'ticket': str(p.get('id', '')),
                'symbol': p.get('symbol', ''),
                'type': p.get('type', ''),
                'volume': p.get('volume', 0),
                'price_open': p.get('openPrice', 0),
                'price_current': p.get('currentPrice', 0),
                'profit': p.get('profit', 0),
                'swap': p.get('swap', 0),
                'commission': p.get('commission', 0)
            } for p in positions]
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def create_market_order(self, symbol: str, order_type: str, volume: float, 
                                  sl: float = None, tp: float = None):
        """Market Order erstellen"""
        try:
            if not self.connected or not self.connection:
                return {'success': False, 'error': 'Not connected'}
            
            logger.info(f"📈 Creating market order: {symbol} {order_type} {volume}")
            
            # Create trade
            result = await self.connection.create_market_buy_order(
                symbol=symbol,
                volume=volume,
                stop_loss=sl,
                take_profit=tp
            ) if order_type.upper() == 'BUY' else await self.connection.create_market_sell_order(
                symbol=symbol,
                volume=volume,
                stop_loss=sl,
                take_profit=tp
            )
            
            logger.info(f"✅ Order created: {result}")
            
            return {
                'success': True,
                'orderId': result.get('orderId'),
                'positionId': result.get('positionId')
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {'success': False, 'error': str(e)}
    
    async def close_position(self, position_id: str):
        """Position schließen"""
        try:
            if not self.connected or not self.connection:
                return False
            
            logger.info(f"🔴 Closing position {position_id}")
            
            await self.connection.close_position(position_id)
            logger.info(f"✅ Position closed: {position_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    async def run_worker(self):
        """Worker Hauptschleife"""
        logger.info("🚀 MetaAPI SDK Worker starting...")
        
        # Setup SDK
        if not await self.setup_sdk():
            logger.error("❌ SDK setup failed, worker exiting")
            return
        
        # Connect
        if not await self.connect():
            logger.error("❌ Connection failed, worker exiting")
            return
        
        logger.info("✅ Worker ready and connected!")
        
        # Keep alive loop
        while True:
            try:
                await asyncio.sleep(10)
                
                # Health check
                if self.connected:
                    account_info = await self.get_account_info()
                    if account_info:
                        balance = account_info.get('balance', 0)
                        logger.debug(f"💰 Balance: {balance:.2f}")
                else:
                    logger.warning("⚠️ Connection lost, attempting reconnect...")
                    await self.connect()
                    
            except asyncio.CancelledError:
                logger.info("🛑 Worker cancelled, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)


async def main():
    """Worker Entry Point"""
    # Get credentials from environment
    token = os.environ.get('METAAPI_TOKEN')
    account_id = os.environ.get('METAAPI_ACCOUNT_ID')
    
    if not token or not account_id:
        logger.error("❌ METAAPI_TOKEN and METAAPI_ACCOUNT_ID must be set!")
        sys.exit(1)
    
    logger.info(f"🔧 Starting worker for account: {account_id[:8]}...")
    
    # Create and run worker
    worker = MetaAPISDKWorker(token, account_id)
    await worker.run_worker()


if __name__ == '__main__':
    try:
        # Use asyncio.run for proper event loop management on macOS
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}", exc_info=True)
        sys.exit(1)
