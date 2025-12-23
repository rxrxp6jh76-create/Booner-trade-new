"""
MetaAPI SDK Connector - Stabile WebSocket-Verbindung
Nutzt den offiziellen MetaAPI Cloud SDK für persistente Verbindungen

macOS ARM64 kompatibel mit expliziter Event Loop Policy
"""

import logging
import os
import sys
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from metaapi_cloud_sdk import MetaApi

logger = logging.getLogger(__name__)

# CRITICAL: Set Event Loop Policy for macOS compatibility
if sys.platform == 'darwin':  # macOS
    try:
        # Use default policy for macOS (works best with MetaAPI SDK)
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        logger.info("✅ macOS asyncio policy set")
    except Exception as e:
        logger.warning(f"⚠️ Could not set event loop policy: {e}")

class MetaAPISDKConnector:
    """MetaAPI SDK-basierter Connector - viel stabiler!"""
    
    def __init__(self, account_id: str, token: str, shared_api_client=None):
        self.account_id = account_id
        self.token = token
        
        # Use shared MetaApi client if provided, otherwise create new one
        if shared_api_client:
            self.api = shared_api_client
            logger.info(f"MetaAPI SDK Connector initialized (shared client): {account_id}")
        else:
            # DESKTOP FIX: History Storage im User-Verzeichnis (nicht im App-Bundle!)
            from pathlib import Path
            import os
            
            # Prüfe ob wir im App-Bundle laufen
            current_path = Path(__file__).parent
            if '/Applications/' in str(current_path) or '.app/Contents/Resources' in str(current_path):
                # Desktop App: Nutze User-Verzeichnis für MetaAPI History
                history_path = Path.home() / 'Library' / 'Application Support' / 'Booner Trade' / '.metaapi'
                history_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"📁 MetaAPI History Storage: {history_path}")
                # Setze Working Directory für MetaAPI SDK
                os.chdir(history_path.parent)
            
            # Configure MetaApi SDK with connection limits to avoid rate limiting
            # DESKTOP: Längere Timeouts für stabile Verbindung
            opts = {
                'application': 'MetaApi',
                'requestTimeout': 120000,  # 2 Minuten (erhöht für Desktop)
                'connectTimeout': 120000,  # 2 Minuten (erhöht für Desktop)
                'retryOpts': {
                    'retries': 5,  # Mehr retries
                    'minDelayInSeconds': 2,
                    'maxDelayInSeconds': 60
                }
            }
            self.api = MetaApi(token, opts)
            logger.info(f"MetaAPI SDK Connector initialized (new client): {account_id}")
        
        self.account = None
        self.connection = None
        self.connected = False
    
    async def connect(self):
        """Verbinde mit MetaAPI über SDK"""
        try:
            # DESKTOP FIX: Monkey-patch FilesystemHistoryDatabase BEFORE first use
            # The SDK hardcodes .metaapi path - we need to override _get_db_location
            from pathlib import Path
            import os
            
            current_path = Path(__file__).parent
            if '/Applications/' in str(current_path) or '.app/Contents/Resources' in str(current_path):
                # We're in Desktop App Bundle - monkey-patch the database
                logger.info("🔧 Monkey-patching MetaAPI FilesystemHistoryDatabase for Desktop...")
                
                try:
                    from metaapi_cloud_sdk.metaapi.filesystem_history_database import FilesystemHistoryDatabase
                    
                    # Create writable directory in User folder
                    user_metaapi_dir = Path.home() / 'Library' / 'Application Support' / 'Booner Trade' / '.metaapi'
                    user_metaapi_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 MetaAPI History will use: {user_metaapi_dir}")
                    
                    # Monkey-patch die _get_db_location Methode
                    # WICHTIG: Muss ein DICT mit allen Datei-Pfaden zurückgeben, nicht nur einen String!
                    original_get_db_location = FilesystemHistoryDatabase._get_db_location
                    
                    async def patched_get_db_location(self, account_id, application):
                        """Return paths dict in user directory instead of current directory"""
                        base_path = user_metaapi_dir / f"{account_id}-{application}"
                        return {
                            'dealsFile': str(base_path) + '-deals.db',
                            'historyOrdersFile': str(base_path) + '-historyOrders.db',
                            'ordersFile': str(base_path) + '-orders.db',
                            'positionsFile': str(base_path) + '-positions.db'
                        }
                    
                    FilesystemHistoryDatabase._get_db_location = patched_get_db_location
                    logger.info("✅ FilesystemHistoryDatabase monkey-patched successfully (returns dict)")
                    
                except Exception as patch_error:
                    logger.warning(f"⚠️  Monkey-patch failed: {patch_error}, SDK may fail")
            
            # Account abrufen
            self.account = await self.api.metatrader_account_api.get_account(self.account_id)
            
            # PYTHON 3.14 FIX: Region manuell setzen falls None
            if not hasattr(self.account, 'region') or self.account.region is None:
                logger.warning(f"⚠️  Account region is None, forcing region='london'")
                self.account.region = 'london'
            else:
                logger.info(f"Account region: {self.account.region}")
            
            # Warte bis deployed
            if self.account.state != 'DEPLOYED':
                logger.info(f"Account {self.account_id} wird deployed...")
                await self.account.deploy()
                await self.account.wait_deployed()
            
            # Verbindung erstellen - ONLY ONE CONNECTION PER ACCOUNT
            # Reusing the same connection object prevents multiple subscriptions
            logger.info(f"Creating streaming connection for {self.account_id}...")
            self.connection = self.account.get_streaming_connection()
            
            # PYTHON 3.11/3.14 FIX: WebSocket Client vorinitialisieren
            # Das SDK hat einen Bug wo _socket_instances nicht richtig initialisiert wird
            region = self.account.region if self.account.region else 'london'
            logger.info(f"Monkey-patching WebSocket client for region: {region}")
            
            # Zugriff auf interne Objekte
            if hasattr(self.connection, '_metaApiWebsocketClient'):
                ws_client = self.connection._metaApiWebsocketClient
                logger.info("Found _metaApiWebsocketClient")
            elif hasattr(self.connection, '_meta_api_websocket_client'):
                ws_client = self.connection._meta_api_websocket_client
                logger.info("Found _meta_api_websocket_client")
            else:
                logger.warning("WebSocket client attribute not found, trying alternatives...")
                # Versuche alle Attribute zu listen
                ws_attrs = [attr for attr in dir(self.connection) if 'websocket' in attr.lower() or 'client' in attr.lower()]
                logger.info(f"Available attributes: {ws_attrs}")
                ws_client = None
                for attr in ws_attrs:
                    try:
                        ws_client = getattr(self.connection, attr)
                        if ws_client and hasattr(ws_client, '_socket_instances'):
                            logger.info(f"✅ Found WebSocket client via {attr}")
                            break
                    except:
                        pass
            
            # Initialisiere _socket_instances
            if ws_client and hasattr(ws_client, '_socket_instances'):
                if not isinstance(ws_client._socket_instances, dict):
                    logger.warning("_socket_instances is not a dict, initializing...")
                    ws_client._socket_instances = {}
                
                # Initialisiere alle Regionen
                for r in ['london', 'new-york', 'singapore', region]:
                    if r and r not in ws_client._socket_instances:
                        logger.info(f"Initializing _socket_instances['{r}']")
                        ws_client._socket_instances[r] = {}
                
                logger.info(f"✅ WebSocket _socket_instances initialized: {list(ws_client._socket_instances.keys())}")
            else:
                logger.error("❌ Could not patch WebSocket client!")
            
            logger.info(f"Connecting to MetaAPI...")
            await self.connection.connect()
            
            # Warte bis verbunden und synchronisiert
            # WICHTIG: Erhöhter Timeout für ICMarkets (braucht länger)
            logger.info(f"Waiting for synchronization (this may take up to 2 minutes)...")
            sync_opts = {
                'timeoutInSeconds': 180,  # 3 Minuten Timeout (statt Default 60s)
                'intervalInMilliseconds': 1000  # Prüfe jede Sekunde
            }
            await self.connection.wait_synchronized(sync_opts)
            
            self.connected = True
            logger.info(f"✅ MetaAPI SDK verbunden: {self.account_id}")
            return True
            
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "No error message"
            logger.error(f"MetaAPI SDK Verbindungsfehler ({error_type}): {error_msg}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self.connected = False
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Hole Account-Informationen"""
        try:
            if not self.connection:
                return getattr(self, '_cached_account_info', None)
            
            # Get terminal state which contains account information
            terminal_state = self.connection.terminal_state
            if not terminal_state:
                logger.warning("Terminal state not available yet")
                return getattr(self, '_cached_account_info', None)
            
            # Access account information from terminal state
            account_info = terminal_state.account_information
            
            result = {
                'balance': account_info.get('balance', 0) if account_info else 0,
                'equity': account_info.get('equity', 0) if account_info else 0,
                'margin': account_info.get('margin', 0) if account_info else 0,
                'freeMargin': account_info.get('freeMargin', 0) if account_info else 0,
                'free_margin': account_info.get('freeMargin', 0) if account_info else 0,
                'leverage': account_info.get('leverage', 0) if account_info else 0,
                'connected': terminal_state.connected if hasattr(terminal_state, 'connected') else False,
                'connectedToBroker': terminal_state.connected_to_broker if hasattr(terminal_state, 'connected_to_broker') else False
            }
            
            # Cache the result for fast access
            self._cached_account_info = result
            
            return result
        except Exception as e:
            logger.error(f"Error getting account info: {e}", exc_info=True)
            return getattr(self, '_cached_account_info', None)
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Hole offene Positionen"""
        try:
            if not self.connection:
                return []
            
            terminal_state = self.connection.terminal_state
            if not terminal_state:
                return []
            
            positions = terminal_state.positions if hasattr(terminal_state, 'positions') else []
            
            result = []
            for pos in positions:
                # Handle both dict and object types
                if isinstance(pos, dict):
                    result.append({
                        'ticket': pos.get('id'),
                        'id': pos.get('id'),
                        'positionId': pos.get('id'),
                        'symbol': pos.get('symbol'),
                        'type': pos.get('type'),
                        'volume': pos.get('volume'),
                        'price_open': pos.get('openPrice'),
                        'openPrice': pos.get('openPrice'),
                        'price_current': pos.get('currentPrice'),
                        'currentPrice': pos.get('currentPrice'),
                        'profit': pos.get('profit'),
                        'unrealizedProfit': pos.get('profit'),
                        'swap': pos.get('swap'),
                        'time': pos.get('time'),
                        'openTime': pos.get('time'),
                        'updateTime': pos.get('updateTime'),
                        'sl': pos.get('stopLoss'),
                        'stopLoss': pos.get('stopLoss'),
                        'tp': pos.get('takeProfit'),
                        'takeProfit': pos.get('takeProfit')
                    })
                else:
                    result.append({
                        'ticket': pos.id if hasattr(pos, 'id') else None,
                        'id': pos.id if hasattr(pos, 'id') else None,
                        'positionId': pos.id if hasattr(pos, 'id') else None,
                        'symbol': pos.symbol if hasattr(pos, 'symbol') else None,
                        'type': pos.type if hasattr(pos, 'type') else None,
                        'volume': pos.volume if hasattr(pos, 'volume') else None,
                        'price_open': pos.openPrice if hasattr(pos, 'openPrice') else None,
                        'openPrice': pos.openPrice if hasattr(pos, 'openPrice') else None,
                        'price_current': pos.currentPrice if hasattr(pos, 'currentPrice') else None,
                        'currentPrice': pos.currentPrice if hasattr(pos, 'currentPrice') else None,
                        'profit': pos.profit if hasattr(pos, 'profit') else None,
                        'unrealizedProfit': pos.profit if hasattr(pos, 'profit') else None,
                        'swap': pos.swap if hasattr(pos, 'swap') else None,
                        'time': pos.time if hasattr(pos, 'time') else None,
                        'openTime': pos.time if hasattr(pos, 'time') else None,
                        'updateTime': pos.updateTime if hasattr(pos, 'updateTime') else None,
                        'sl': pos.stopLoss if hasattr(pos, 'stopLoss') else None,
                        'stopLoss': pos.stopLoss if hasattr(pos, 'stopLoss') else None,
                        'tp': pos.takeProfit if hasattr(pos, 'takeProfit') else None,
                        'takeProfit': pos.takeProfit if hasattr(pos, 'takeProfit') else None
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}", exc_info=True)
            return []
    
    async def create_market_order(self, symbol: str, order_type: str, volume: float, 
                                   sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Platziere Market Order mit Timeout-Handling"""
        try:
            if not self.connection:
                logger.error("SDK not connected!")
                return {'success': False, 'error': 'Not connected to trading platform'}
            
            logger.info(f"🔄 Placing order: {symbol} {order_type} {volume} lots (SL: {sl}, TP: {tp})")
            
            # Order ausführen mit asyncio.wait_for für Timeout
            import asyncio
            
            try:
                if order_type.upper() == 'BUY':
                    order_coro = self.connection.create_market_buy_order(
                        symbol=symbol,
                        volume=volume,
                        stop_loss=sl,
                        take_profit=tp
                    )
                else:
                    order_coro = self.connection.create_market_sell_order(
                        symbol=symbol,
                        volume=volume,
                        stop_loss=sl,
                        take_profit=tp
                    )
                
                # Warte max 30 Sekunden auf Antwort
                result = await asyncio.wait_for(order_coro, timeout=30.0)
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Order timeout after 30 seconds")
                return {'success': False, 'error': 'Order timeout - Platform nicht erreichbar (30s)'}
            
            logger.info(f"✅ Order platziert: {symbol} {order_type} {volume} Lots")
            
            return {
                'success': True,
                'orderId': result.orderId if hasattr(result, 'orderId') else result.get('orderId'),
                'positionId': result.positionId if hasattr(result, 'positionId') else result.get('positionId'),
                'message': f'Order executed: {symbol} {order_type} {volume} lots'
            }
            
        except Exception as e:
            logger.error(f"❌ Order execution error: {e}", exc_info=True)
            return {'success': False, 'error': f'Trade execution failed: {str(e)}'}
    
    async def close_position(self, position_id: str) -> dict:
        """
        Schließe Position
        
        Returns:
            dict: {'success': bool, 'error': str|None, 'error_type': str|None}
        """
        try:
            if not self.connection:
                return {'success': False, 'error': 'Keine Verbindung zur Plattform', 'error_type': 'NO_CONNECTION'}
            
            await self.connection.close_position(position_id)
            logger.info(f"✅ Position geschlossen: {position_id}")
            return {'success': True, 'error': None, 'error_type': None}
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # V2.3.31: Spezifische Fehlertypen für bessere UI-Rückmeldung
            if 'market' in error_msg and 'closed' in error_msg:
                logger.warning(f"⏸️ Position {position_id}: Markt geschlossen")
                return {
                    'success': False, 
                    'error': 'Die Börse ist gerade geschlossen. Bitte versuchen Sie es während der Handelszeiten erneut.',
                    'error_type': 'MARKET_CLOSED'
                }
            elif 'timed out' in error_msg or 'timeout' in error_msg:
                logger.warning(f"⏱️ Position {position_id}: Timeout")
                return {
                    'success': False,
                    'error': 'Zeitüberschreitung beim Schließen der Position. Bitte versuchen Sie es erneut.',
                    'error_type': 'TIMEOUT'
                }
            elif 'invalid' in error_msg and 'ticket' in error_msg:
                logger.warning(f"❓ Position {position_id}: Ungültiges Ticket")
                return {
                    'success': False,
                    'error': 'Position nicht gefunden. Möglicherweise wurde sie bereits geschlossen.',
                    'error_type': 'INVALID_TICKET'
                }
            elif 'not enough' in error_msg or 'margin' in error_msg:
                logger.warning(f"💰 Position {position_id}: Margin-Problem")
                return {
                    'success': False,
                    'error': 'Margin-Problem beim Schließen der Position.',
                    'error_type': 'MARGIN_ERROR'
                }
            else:
                logger.error(f"❌ Position {position_id}: {e}")
                return {
                    'success': False,
                    'error': f'Fehler beim Schließen: {str(e)[:100]}',
                    'error_type': 'UNKNOWN'
                }
    
    async def disconnect(self):
        """Verbindung trennen"""
        try:
            if self.connection:
                await self.connection.close()
            self.connected = False
            logger.info(f"MetaAPI SDK disconnected: {self.account_id}")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
    async def get_deals_by_time_range(self, start_time: str, end_time: str, offset: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        V2.3.37: Hole geschlossene Trades (Deals) von MT5 nach Zeitraum
        
        Args:
            start_time: ISO Format z.B. "2024-01-01T00:00:00.000Z"
            end_time: ISO Format z.B. "2024-12-31T23:59:59.999Z"
            offset: Pagination offset
            limit: Max Anzahl (max 1000)
        
        Returns:
            List von Deals mit allen Details
        """
        try:
            if not self.connection:
                logger.warning("No connection for get_deals_by_time_range")
                return []
            
            from datetime import datetime
            
            # Parse Zeitstempel falls Strings
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = start_time
                
            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_dt = end_time
            
            logger.info(f"📊 Fetching deals from {start_dt} to {end_dt}")
            
            # Hole Deals über die Connection
            import asyncio
            try:
                deals = await asyncio.wait_for(
                    self.connection.get_deals_by_time_range(start_dt, end_dt, offset, limit),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("get_deals_by_time_range timeout after 30s")
                return []
            
            if not deals:
                return []
            
            # Konvertiere zu einheitlichem Format
            result = []
            for deal in deals:
                if isinstance(deal, dict):
                    result.append({
                        'id': deal.get('id'),
                        'positionId': deal.get('positionId'),
                        'orderId': deal.get('orderId'),
                        'symbol': deal.get('symbol'),
                        'type': deal.get('type'),
                        'entryType': deal.get('entryType'),  # DEAL_ENTRY_IN, DEAL_ENTRY_OUT
                        'volume': deal.get('volume'),
                        'price': deal.get('price'),
                        'profit': deal.get('profit'),
                        'swap': deal.get('swap'),
                        'commission': deal.get('commission'),
                        'time': deal.get('time'),
                        'brokerTime': deal.get('brokerTime'),
                        'comment': deal.get('comment'),
                        'clientId': deal.get('clientId'),
                        'platform': 'mt5'
                    })
                else:
                    # Object Type
                    result.append({
                        'id': getattr(deal, 'id', None),
                        'positionId': getattr(deal, 'positionId', None),
                        'orderId': getattr(deal, 'orderId', None),
                        'symbol': getattr(deal, 'symbol', None),
                        'type': getattr(deal, 'type', None),
                        'entryType': getattr(deal, 'entryType', None),
                        'volume': getattr(deal, 'volume', None),
                        'price': getattr(deal, 'price', None),
                        'profit': getattr(deal, 'profit', None),
                        'swap': getattr(deal, 'swap', None),
                        'commission': getattr(deal, 'commission', None),
                        'time': getattr(deal, 'time', None),
                        'brokerTime': getattr(deal, 'brokerTime', None),
                        'comment': getattr(deal, 'comment', None),
                        'clientId': getattr(deal, 'clientId', None),
                        'platform': 'mt5'
                    })
            
            logger.info(f"✅ Fetched {len(result)} deals from MT5")
            return result
            
        except Exception as e:
            logger.error(f"Error getting deals by time range: {e}", exc_info=True)
            return []
    
    async def is_connected(self) -> bool:
        """Prüfe ob verbunden"""
        try:
            if not self.connection or not self.connection.terminal_state:
                return False
            return self.connection.terminal_state.connected and self.connection.terminal_state.connectedToBroker
        except:
            return False
    
    async def get_symbol_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current symbol price"""
        try:
            if not self.connection:
                return None
            
            # Get symbol price from terminal state
            terminal_state = self.connection.terminal_state
            if not terminal_state:
                return None
            
            # Access price data - terminal_state.price is a dict
            if hasattr(terminal_state, 'price'):
                prices = terminal_state.price
                # price is actually a method, we need to call it
                if callable(prices):
                    try:
                        # Try to get the price by calling the method
                        price_data = await prices(symbol)
                        if price_data:
                            return {
                                'symbol': symbol,
                                'bid': price_data.get('bid') if isinstance(price_data, dict) else getattr(price_data, 'bid', None),
                                'ask': price_data.get('ask') if isinstance(price_data, dict) else getattr(price_data, 'ask', None),
                                'time': price_data.get('time') if isinstance(price_data, dict) else getattr(price_data, 'time', None)
                            }
                    except:
                        pass
                elif isinstance(prices, dict) and symbol in prices:
                    price_data = prices[symbol]
                    return {
                        'symbol': symbol,
                        'bid': price_data.get('bid') if isinstance(price_data, dict) else getattr(price_data, 'bid', None),
                        'ask': price_data.get('ask') if isinstance(price_data, dict) else getattr(price_data, 'ask', None),
                        'time': price_data.get('time') if isinstance(price_data, dict) else getattr(price_data, 'time', None)
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error getting symbol price for {symbol}: {e}", exc_info=True)
            return None
    
    async def get_symbols(self) -> List[str]:
        """Get all available symbols"""
        try:
            if not self.connection:
                return []
            
            terminal_state = self.connection.terminal_state
            if not terminal_state:
                return []
            
            # Get specifications
            if hasattr(terminal_state, 'specifications'):
                specs = terminal_state.specifications
                if isinstance(specs, dict):
                    return list(specs.keys())
                elif isinstance(specs, list):
                    return [s.get('symbol') if isinstance(s, dict) else s.symbol for s in specs]
            
            return []
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []


async def test_sdk_connector():
    """Test-Funktion"""
    import os
    
    token = os.getenv('METAAPI_TOKEN')
    account_id = os.getenv('METAAPI_ACCOUNT_ID')
    
    connector = MetaAPISDKConnector(account_id, token)
    
    # Verbinden
    await connector.connect()
    
    # Account Info
    info = await connector.get_account_info()
    print(f"Balance: {info['balance']}, Equity: {info['equity']}")
    
    # Positionen
    positions = await connector.get_positions()
    print(f"Offene Positionen: {len(positions)}")
    
    # Disconnect
    await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(test_sdk_connector())
