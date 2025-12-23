"""
Multi-Platform Connector - SDK VERSION (Viel stabiler!)
Migrated from REST API to official metaapi-python-sdk
Supports: MT5 Libertex Demo, MT5 ICMarkets Demo, MT5 Libertex REAL
Removed: Bitpanda (as requested)
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from metaapi_sdk_connector import MetaAPISDKConnector

# CRITICAL: Load .env BEFORE reading environment variables!
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)  # FORCE override system env

logger = logging.getLogger(__name__)

class MultiPlatformConnector:
    """Manages connections to multiple MT5 platforms using stable SDK"""
    
    def __init__(self):
        self.platforms = {}
        self.metaapi_token = os.environ.get('METAAPI_TOKEN', '')
        self._metaapi_client = None  # Shared MetaApi client to prevent multiple instances
        
        # MT5 Libertex Demo
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
        
        # MT5 ICMarkets Demo
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
        
        # MT5 Libertex REAL (wenn in .env konfiguriert)
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
                'is_real': True  # ECHTES GELD!
            }
            logger.warning("⚠️  REAL MONEY ACCOUNT available: MT5_LIBERTEX_REAL")
        else:
            logger.info("ℹ️  Libertex Real Account not configured (only Demo available)")
        
        # MT5 ICMarkets REAL (wenn in .env konfiguriert)
        icmarkets_real_id = os.environ.get('METAAPI_ICMARKETS_REAL_ACCOUNT_ID', '')
        if icmarkets_real_id and icmarkets_real_id != 'PLACEHOLDER_REAL_ACCOUNT_ID':
            self.platforms['MT5_ICMARKETS_REAL'] = {
                'type': 'MT5',
                'name': '💰 MT5 ICMarkets REAL 💰',
                'account_id': icmarkets_real_id,
                'region': 'london',
                'connector': None,
                'active': False,
                'balance': 0.0,
                'is_real': True  # ECHTES GELD!
            }
            logger.warning("⚠️  REAL MONEY ACCOUNT available: MT5_ICMARKETS_REAL")
        else:
            logger.info("ℹ️  ICMarkets Real Account not configured (only Demo available)")
        
        # Legacy compatibility mappings
        if 'MT5_LIBERTEX_DEMO' in self.platforms:
            self.platforms['MT5_LIBERTEX'] = self.platforms['MT5_LIBERTEX_DEMO']
            self.platforms['LIBERTEX'] = self.platforms['MT5_LIBERTEX_DEMO']  # Short alias
        if 'MT5_ICMARKETS_DEMO' in self.platforms:
            self.platforms['MT5_ICMARKETS'] = self.platforms['MT5_ICMARKETS_DEMO']
            self.platforms['ICMARKETS'] = self.platforms['MT5_ICMARKETS_DEMO']  # Short alias
        
        logger.info(f"MultiPlatformConnector (SDK) initialized with {len(self.platforms)} platform(s)")
    
    async def connect_platform(self, platform_name: str) -> bool:
        """Connect to platform using stable SDK"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return False
            
            platform = self.platforms[platform_name]
            
            # Already connected?
            if platform.get('active') and platform.get('connector'):
                connector = platform['connector']
                if await connector.is_connected():
                    logger.debug(f"ℹ️  {platform_name} already connected")
                    return True
                else:
                    logger.warning(f"⚠️  {platform_name} connection lost, reconnecting...")
            
            # Check if we should force REST API mode (Desktop environment)
            import os
            force_rest_api = os.environ.get('USE_REST_API_ONLY', 'false').lower() == 'true'
            disable_sdk = os.environ.get('DISABLE_SDK', 'false').lower() == 'true'
            
            connector = None
            success = False
            
            # DESKTOP MODE: Force REST API only
            if force_rest_api or disable_sdk:
                logger.info(f"🔄 DESKTOP MODE: Using REST API only (SDK disabled)")
                try:
                    from metaapi_connector import MetaAPIConnector
                    connector = MetaAPIConnector(
                        account_id=platform['account_id'],
                        token=self.metaapi_token
                    )
                    success = await connector.connect()
                    if success:
                        logger.info("✅ Connected via REST API (Desktop Mode)")
                except Exception as rest_error:
                    logger.error(f"❌ REST API connection failed: {rest_error}")
                    success = False
            else:
                # SERVER MODE: Try SDK first (works on both Server and Desktop with monkey-patch)
                try:
                    logger.info(f"🔄 Connecting to {platform_name} via SDK...")
                    # Initialize shared MetaApi client if not already done
                    if not self._metaapi_client:
                        from metaapi_cloud_sdk import MetaApi
                        opts = {
                            'application': 'MetaApi',
                            'requestTimeout': 60000,
                            'connectTimeout': 60000,
                            'retryOpts': {
                                'retries': 3,
                                'minDelayInSeconds': 1,
                                'maxDelayInSeconds': 30
                            }
                        }
                        self._metaapi_client = MetaApi(self.metaapi_token, opts)
                        logger.info("✅ Shared MetaApi client initialized")
                    
                    connector = MetaAPISDKConnector(
                        account_id=platform['account_id'],
                        token=self.metaapi_token,
                        shared_api_client=self._metaapi_client
                    )
                    success = await connector.connect()
                except Exception as sdk_error:
                    logger.warning(f"⚠️  SDK failed ({sdk_error}), trying REST API fallback...")
                    try:
                        from metaapi_connector import MetaAPIConnector
                        connector = MetaAPIConnector(
                            account_id=platform['account_id'],
                            token=self.metaapi_token
                        )
                        success = await connector.connect()
                        if success:
                            logger.info("✅ Connected via REST API fallback")
                    except Exception as rest_error:
                        logger.error(f"❌ REST API fallback failed: {rest_error}")
                        success = False
            if success:
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
        """Disconnect from platform"""
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
        """Get account information"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if platform['connector']:
                account_info = await platform['connector'].get_account_info()
                if account_info:
                    platform['balance'] = account_info.get('balance', 0.0)
                return account_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {platform_name}: {e}")
            return None
    
    async def execute_trade(self, platform_name: str, symbol: str, action: str, 
                           volume: float, stop_loss: float = None, 
                           take_profit: float = None) -> Optional[Dict[str, Any]]:
        """Execute trade via SDK"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # SAFETY: Warnung bei Real Account
            if platform.get('is_real', False):
                logger.warning(f"⚠️⚠️⚠️  EXECUTING REAL MONEY TRADE on {platform_name}! ⚠️⚠️⚠️")
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return None
            
            # Execute via SDK
            result = await platform['connector'].create_market_order(
                symbol=symbol,
                order_type=action.upper(),
                volume=volume,
                sl=stop_loss,
                tp=take_profit
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade on {platform_name}: {e}")
            return None
    
    async def create_market_order(
        self,
        platform: str,
        symbol: str,
        order_type: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a market order on the specified platform
        """
        try:
            # Normalize platform name
            platform_name = platform
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform_obj = self.platforms[platform_name]
            
            # Connect if not connected
            if not platform_obj['active'] or not platform_obj['connector']:
                logger.info(f"Platform {platform_name} not connected, connecting now...")
                await self.connect_platform(platform_name)
            
            if not platform_obj['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return None
            
            logger.info(f"📈 Creating market order: {symbol} {order_type} {volume} on {platform_name}")
            
            # Execute via connector
            result = await platform_obj['connector'].create_market_order(
                symbol=symbol,
                order_type=order_type.upper(),
                volume=volume,
                sl=sl,
                tp=tp
            )
            
            if result:
                logger.info(f"✅ Order created: {result}")
            else:
                logger.error(f"❌ Failed to create order")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating market order on {platform}: {e}", exc_info=True)
            return None
    
    async def get_open_positions(self, platform_name: str) -> List[Dict[str, Any]]:
        """Get open positions - DIREKT von MT5, keine Deduplizierung"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return []
            
            platform = self.platforms[platform_name]
            
            if not platform['active'] or not platform['connector']:
                return []
            
            # Hole Positionen DIREKT vom SDK (MT5-Sync)
            positions = await platform['connector'].get_positions()
            
            # Filter nur offensichtliche Fehler (TRADE_RETCODE)
            clean_positions = []
            for pos in positions:
                ticket = pos.get('ticket') or pos.get('id') or pos.get('positionId')
                symbol = pos.get('symbol', '')
                
                # Skip nur error positions
                if ticket and 'TRADE_RETCODE' in str(ticket):
                    continue
                if 'TRADE_RETCODE' in symbol:
                    continue
                
                clean_positions.append(pos)
            
            logger.info(f"{platform_name}: {len(clean_positions)} open positions from MT5")
            return clean_positions
            
        except Exception as e:
            logger.error(f"Error getting positions for {platform_name}: {e}")
            return []
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Alias for compatibility"""
        # Return positions from all active platforms
        all_positions = []
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            if platform_name in self.platforms:
                positions = await self.get_open_positions(platform_name)
                for pos in positions:
                    pos['platform'] = platform_name
                all_positions.extend(positions)
        return all_positions
    
    def get_active_platforms(self) -> List[str]:
        """Get list of active platforms"""
        return [name for name, platform in self.platforms.items() 
                if platform['active'] and name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']]
    
    def get_platform_status(self) -> Dict[str, Any]:
        """Get status of all platforms"""
        # Only return actual platforms, not legacy aliases
        actual_platforms = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']
        return {
            name: {
                'active': platform['active'],
                'balance': platform['balance'],
                'name': platform['name'],
                'is_real': platform.get('is_real', False)
            }
            for name, platform in self.platforms.items()
            if name in actual_platforms
        }
    
    async def close_position(self, platform_name: str, position_id: str) -> dict:
        """
        Schließe Position auf Platform
        
        V2.3.31: Gibt jetzt dict mit Details zurück statt nur bool
        Returns: {'success': bool, 'error': str|None, 'error_type': str|None}
        """
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return {'success': False, 'error': f'Unbekannte Plattform: {platform_name}', 'error_type': 'UNKNOWN_PLATFORM'}
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return {'success': False, 'error': 'Plattform nicht verbunden', 'error_type': 'NOT_CONNECTED'}
            
            # Close via SDK - V2.3.31: Jetzt mit detaillierter Rückgabe
            result = await platform['connector'].close_position(position_id)
            
            # Handle both old (bool) and new (dict) return types
            if isinstance(result, bool):
                # Legacy: bool return
                if result:
                    logger.info(f"✅ Position {position_id} geschlossen auf {platform_name}")
                    return {'success': True, 'error': None, 'error_type': None}
                else:
                    return {'success': False, 'error': 'Position konnte nicht geschlossen werden', 'error_type': 'UNKNOWN'}
            else:
                # New: dict return with details
                if result.get('success'):
                    logger.info(f"✅ Position {position_id} geschlossen auf {platform_name}")
                else:
                    logger.warning(f"⚠️ Position {position_id}: {result.get('error_type')} - {result.get('error')}")
                return result
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return {'success': False, 'error': str(e), 'error_type': 'EXCEPTION'}
    
    async def get_closed_trades(self, start_time: str = None, end_time: str = None, 
                                platform_filter: str = None) -> List[Dict[str, Any]]:
        """
        V2.3.37: Hole geschlossene Trades von ALLEN aktiven MT5-Plattformen
        
        Args:
            start_time: ISO Format oder None (default: letzte 30 Tage)
            end_time: ISO Format oder None (default: jetzt)
            platform_filter: Optional - nur von dieser Plattform
        
        Returns:
            Liste aller geschlossenen Trades mit MT5-Daten
        """
        from datetime import datetime, timezone, timedelta
        
        # Default: Letzte 30 Tage
        if not end_time:
            end_dt = datetime.now(timezone.utc)
            end_time = end_dt.isoformat()
        else:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
        if not start_time:
            start_dt = end_dt - timedelta(days=30)
            start_time = start_dt.isoformat()
        
        all_trades = []
        platforms_to_check = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']
        
        if platform_filter:
            platforms_to_check = [platform_filter]
        
        for platform_name in platforms_to_check:
            if platform_name not in self.platforms:
                continue
                
            platform = self.platforms[platform_name]
            
            # Verbinde falls nötig
            if not platform['active'] or not platform['connector']:
                try:
                    await self.connect_platform(platform_name)
                except Exception as e:
                    logger.warning(f"Could not connect to {platform_name}: {e}")
                    continue
            
            if not platform['connector']:
                continue
            
            try:
                # Hole Deals von dieser Plattform
                deals = await platform['connector'].get_deals_by_time_range(
                    start_time, end_time, offset=0, limit=1000
                )
                
                if not deals:
                    logger.info(f"{platform_name}: Keine Deals gefunden")
                    continue
                
                # Füge Plattform-Info hinzu und filtere nur CLOSE-Deals
                for deal in deals:
                    deal['platform'] = platform_name
                    deal['platform_name'] = platform['name']
                    deal['is_real'] = platform.get('is_real', False)
                    
                    # Nur geschlossene Positionen (DEAL_ENTRY_OUT)
                    entry_type = deal.get('entryType', '')
                    if entry_type in ['DEAL_ENTRY_OUT', 'DEAL_ENTRY_INOUT']:
                        all_trades.append(deal)
                
                logger.info(f"✅ {platform_name}: {len([d for d in deals if d.get('entryType') in ['DEAL_ENTRY_OUT', 'DEAL_ENTRY_INOUT']])} geschlossene Trades")
                
            except Exception as e:
                logger.error(f"Error getting closed trades from {platform_name}: {e}")
                continue
        
        # Sortiere nach Zeit (neueste zuerst)
        all_trades.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        logger.info(f"📊 Total: {len(all_trades)} geschlossene Trades von allen Plattformen")
        return all_trades

    async def modify_position(self, ticket: str, stop_loss: float = None, 
                             take_profit: float = None, platform: str = 'MT5_LIBERTEX_DEMO') -> bool:
        """
        Modify existing position SL/TP via MetaAPI
        
        Args:
            ticket: Position ticket ID
            stop_loss: New stop loss price
            take_profit: New take profit price
            platform: Platform name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Handle legacy platform names
            if platform in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform = 'MT5_LIBERTEX_DEMO'
            elif platform in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform = 'MT5_ICMARKETS_DEMO'
            
            if platform not in self.platforms:
                logger.error(f"Unknown platform: {platform}")
                return False
            
            platform_obj = self.platforms[platform]
            
            # Connect if needed
            if not platform_obj['active'] or not platform_obj['connector']:
                logger.info(f"Connecting to {platform} for position modification...")
                await self.connect_platform(platform)
            
            if not platform_obj['connector']:
                logger.error(f"Platform {platform} not connected")
                return False
            
            # Modify via SDK
            logger.info(f"Modifying position {ticket} on {platform}: SL={stop_loss}, TP={take_profit}")
            
            result = await platform_obj['connector'].modify_position(
                position_id=ticket,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if result:
                logger.info(f"✅ Successfully modified position {ticket} on {platform}")
                return True
            else:
                logger.error(f"❌ Failed to modify position {ticket} on {platform} - SDK returned False")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error modifying position {ticket} on {platform}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# Global instance
multi_platform = MultiPlatformConnector()
