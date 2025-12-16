"""
Multi-Platform Connector - SDK Version (Stabil & Zuverlässig!)
Verwendet offizielles metaapi-python-sdk statt REST API
Unterstützt: MT5 Libertex Demo, MT5 ICMarkets Demo, MT5 Libertex REAL
"""

import logging
import os
from typing import Optional, Dict, List, Any
from metaapi_sdk_connector import MetaAPISDKConnector

logger = logging.getLogger(__name__)

class MultiPlatformConnectorSDK:
    """Manages connections to multiple MT5 platforms using SDK"""
    
    def __init__(self):
        self.platforms = {}
        self.metaapi_token = os.environ.get('METAAPI_TOKEN', '')
        
        # Initialize MT5 Libertex Demo
        libertex_demo_id = os.environ.get('METAAPI_ACCOUNT_ID', '5cc9abd1-671a-447e-ab93-5abbfe0ed941')
        self.platforms['MT5_LIBERTEX_DEMO'] = {
            'type': 'MT5',
            'name': 'MT5 Libertex Demo',
            'account_id': libertex_demo_id,
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0,
            'is_real': False
        }
        
        # Initialize MT5 ICMarkets Demo
        icmarkets_demo_id = os.environ.get('METAAPI_ICMARKETS_ACCOUNT_ID', 'd2605e89-7bc2-4144-9f7c-951edd596c39')
        self.platforms['MT5_ICMARKETS_DEMO'] = {
            'type': 'MT5',
            'name': 'MT5 ICMarkets Demo',
            'account_id': icmarkets_demo_id,
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0,
            'is_real': False
        }
        
        # Initialize MT5 Libertex REAL (wenn verfügbar)
        libertex_real_id = os.environ.get('METAAPI_LIBERTEX_REAL_ACCOUNT_ID', '')
        if libertex_real_id and libertex_real_id != 'PLACEHOLDER_REAL_ACCOUNT_ID':
            self.platforms['MT5_LIBERTEX_REAL'] = {
                'type': 'MT5',
                'name': '💰 MT5 Libertex REAL 💰',
                'account_id': libertex_real_id,
                'region': 'london',
                'connector': None,
                'active': False,
                'balance': 0.0,
                'is_real': True  # WICHTIG: Echtgeld-Account!
            }
            logger.warning("⚠️  REAL MONEY ACCOUNT activated: MT5_LIBERTEX_REAL")
        else:
            logger.info("ℹ️  Real Account nicht konfiguriert (nur Demo-Accounts verfügbar)")
        
        logger.info(f"MultiPlatformConnectorSDK initialized with {len(self.platforms)} platform(s)")
    
    async def connect_platform(self, platform_name: str) -> bool:
        """Connect to a specific platform using SDK"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return False
            
            platform = self.platforms[platform_name]
            
            # Already connected?
            if platform.get('active') and platform.get('connector'):
                # Verify connection is still alive
                connector = platform['connector']
                if await connector.is_connected():
                    logger.debug(f"ℹ️  {platform_name} already connected, reusing...")
                    return True
                else:
                    logger.warning(f"⚠️  {platform_name} connection lost, reconnecting...")
            
            # Create new SDK connector
            logger.info(f"🔄 Connecting to {platform_name} via SDK...")
            connector = MetaAPISDKConnector(
                account_id=platform['account_id'],
                token=self.metaapi_token
            )
            
            # Connect
            success = await connector.connect()
            if success:
                # Get account info
                account_info = await connector.get_account_info()
                
                platform['connector'] = connector
                platform['active'] = True
                platform['balance'] = account_info.get('balance', 0.0) if account_info else 0.0
                
                logger.info(f"✅ SDK Connected: {platform_name} | Balance: €{platform['balance']:.2f}")
                return True
            else:
                logger.error(f"❌ Failed to connect {platform_name}")
                return False
            
        except Exception as e:
            logger.error(f"Error connecting to {platform_name}: {e}", exc_info=True)
            return False
    
    async def disconnect_platform(self, platform_name: str) -> bool:
        """Disconnect from a specific platform"""
        try:
            if platform_name in self.platforms:
                platform = self.platforms[platform_name]
                if platform.get('connector'):
                    await platform['connector'].disconnect()
                platform['active'] = False
                platform['connector'] = None
                logger.info(f"Disconnected from {platform_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disconnecting from {platform_name}: {e}")
            return False
    
    async def get_account_info(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Get account information for a specific platform"""
        try:
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # Connect if not active
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if platform['connector']:
                account_info = await platform['connector'].get_account_info()
                if account_info:
                    # Update cached balance
                    platform['balance'] = account_info.get('balance', 0.0)
                return account_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {platform_name}: {e}")
            return None
    
    async def get_positions(self, platform_name: str) -> List[Dict[str, Any]]:
        """Get open positions from a platform"""
        try:
            if platform_name not in self.platforms:
                return []
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if platform['connector']:
                return await platform['connector'].get_positions()
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting positions from {platform_name}: {e}")
            return []
    
    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from all active platforms"""
        all_positions = []
        
        for platform_name, platform_data in self.platforms.items():
            try:
                positions = await self.get_positions(platform_name)
                
                # Add platform info to each position
                for pos in positions:
                    pos['platform'] = platform_name
                    pos['platform_name'] = platform_data['name']
                
                all_positions.extend(positions)
            except Exception as e:
                logger.error(f"Error fetching positions from {platform_name}: {e}")
        
        return all_positions
    
    async def execute_trade(self, platform_name: str, symbol: str, 
                           order_type: str, volume: float, 
                           sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Execute a trade on a specific platform"""
        try:
            if platform_name not in self.platforms:
                return {'success': False, 'error': f'Unknown platform: {platform_name}'}
            
            platform = self.platforms[platform_name]
            
            # SAFETY CHECK: Warnung bei Real Account
            if platform.get('is_real', False):
                logger.warning(f"⚠️⚠️⚠️  EXECUTING REAL MONEY TRADE on {platform_name}! ⚠️⚠️⚠️")
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                return {'success': False, 'error': 'Platform not connected'}
            
            # Execute trade via SDK
            result = await platform['connector'].create_market_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                sl=sl,
                tp=tp
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade on {platform_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def close_position(self, platform_name: str, position_id: str) -> bool:
        """Close a position on a specific platform"""
        try:
            if platform_name not in self.platforms:
                return False
            
            platform = self.platforms[platform_name]
            
            # SAFETY CHECK
            if platform.get('is_real', False):
                logger.warning(f"⚠️⚠️⚠️  CLOSING REAL MONEY POSITION on {platform_name}! ⚠️⚠️⚠️")
            
            if not platform['connector']:
                return False
            
            return await platform['connector'].close_position(position_id)
            
        except Exception as e:
            logger.error(f"Error closing position on {platform_name}: {e}")
            return False
    
    def get_platform_status(self) -> List[Dict[str, Any]]:
        """Get status of all platforms"""
        status_list = []
        
        for platform_name, platform_data in self.platforms.items():
            status_list.append({
                'platform': platform_name,
                'name': platform_data['name'],
                'type': platform_data['type'],
                'connected': platform_data['active'],
                'balance': platform_data['balance'],
                'is_real': platform_data.get('is_real', False)
            })
        
        return status_list
    
    async def disconnect_all(self):
        """Disconnect from all platforms"""
        for platform_name in list(self.platforms.keys()):
            await self.disconnect_platform(platform_name)
        logger.info("All platforms disconnected")


# Global instance
multi_platform_sdk = None

def get_multi_platform_sdk():
    """Get or create global MultiPlatformConnectorSDK instance"""
    global multi_platform_sdk
    if multi_platform_sdk is None:
        multi_platform_sdk = MultiPlatformConnectorSDK()
    return multi_platform_sdk
