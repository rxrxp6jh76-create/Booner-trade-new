"""
MetaAPI Cloud Connector - Echte MT5 Verbindung über MetaAPI REST API
"""

import logging
import os
import aiohttp
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MetaAPIConnector:
    """MetaAPI Cloud connection handler for real MT5 trading"""
    
    def __init__(self, account_id: str, token: str):
        self.account_id = account_id
        self.token = token
        # MetaAPI base URL - London region for ICMarketsEU-Demo
        self.base_url = "https://mt-client-api-v1.london.agiliumtrade.ai"
        self.connected = False
        self.balance = 0.0
        self.equity = 0.0
        self.margin = 0.0
        self.free_margin = 0.0
        
        # CACHING für Stabilität
        self._account_info_cache = None
        self._account_info_cache_time = None
        self._positions_cache = None
        self._positions_cache_time = None
        self._cache_ttl = 5  # 5 Sekunden Cache
        
        logger.info(f"MetaAPI Connector initialized: Account={account_id}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for MetaAPI"""
        return {
            "auth-token": self.token,
            "Content-Type": "application/json"
        }
    
    async def connect(self) -> bool:
        """Connect to MetaAPI and verify account"""
        try:
            # Test connection by getting account info
            account_info = await self.get_account_info()
            if account_info:
                self.connected = True
                logger.info(f"✅ Connected to MetaAPI: {self.account_id}")
                logger.info(f"Balance: {account_info.get('balance')} {account_info.get('currency')}")
                return True
            else:
                logger.error("Failed to connect to MetaAPI")
                return False
        except Exception as e:
            logger.error(f"MetaAPI connection error: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get current account information (with caching)"""
        try:
            # Check cache
            now = datetime.now().timestamp()
            if (self._account_info_cache and self._account_info_cache_time and 
                now - self._account_info_cache_time < self._cache_ttl):
                logger.debug(f"Using cached account info for {self.account_id}")
                return self._account_info_cache
            
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/account-information"
            
            # Create SSL context that doesn't verify certificates
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Update internal state
                        self.balance = data.get('balance', 0.0)
                        self.equity = data.get('equity', 0.0)
                        self.margin = data.get('margin', 0.0)
                        self.free_margin = data.get('freeMargin', 0.0)
                        
                        # Prepare return data
                        result = {
                            "balance": self.balance,
                            "equity": self.equity,
                            "margin": self.margin,
                            "free_margin": self.free_margin,
                            "profit": data.get('profit', 0.0),
                            "currency": data.get('currency', 'USD'),
                            "leverage": data.get('leverage', 100),
                            "login": data.get('login', self.account_id),
                            "server": data.get('server', 'MetaAPI'),
                            "trade_mode": "REAL" if data.get('type') == 'cloud' else data.get('type', 'UNKNOWN').upper(),
                            "name": data.get('name', 'MetaTrader Account'),
                            "broker": data.get('broker', 'Unknown')
                        }
                        
                        # Cache it
                        self._account_info_cache = result
                        self._account_info_cache_time = now
                        
                        logger.info(f"MetaAPI Account Info: Balance={self.balance}, Equity={self.equity}")
                        return result
                    elif response.status == 429:
                        logger.warning("MetaAPI rate limit hit for account info, using cached data")
                        return self._account_info_cache
                    else:
                        error_text = await response.text()
                        logger.error(f"MetaAPI error {response.status}: {error_text}")
                        return self._account_info_cache  # Return cached on error
        except Exception as e:
            logger.error(f"Error getting MetaAPI account info: {e}")
            return self._account_info_cache  # Return cached on error
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions from MetaAPI (with caching)"""
        try:
            # Check cache
            now = datetime.now().timestamp()
            if (self._positions_cache is not None and self._positions_cache_time and 
                now - self._positions_cache_time < self._cache_ttl):
                logger.debug(f"Using cached positions for {self.account_id}")
                return self._positions_cache
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/positions"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        positions = await response.json()
                        
                        result = []
                        for pos in positions:
                            result.append({
                                "ticket": pos.get('id', ''),
                                "symbol": pos.get('symbol', ''),
                                "type": pos.get('type', 'BUY').upper(),
                                "volume": pos.get('volume', 0.0),
                                "price_open": pos.get('openPrice', 0.0),
                                "price_current": pos.get('currentPrice', 0.0),
                                "profit": pos.get('profit', 0.0),
                                "swap": pos.get('swap', 0.0),
                                "time": pos.get('time', ''),
                                "sl": pos.get('stopLoss'),
                                "tp": pos.get('takeProfit')
                            })
                        
                        # Cache it
                        self._positions_cache = result
                        self._positions_cache_time = now
                        
                        logger.info(f"MetaAPI Positions: {len(result)} open")
                        return result
                    elif response.status == 429:
                        logger.warning("MetaAPI rate limit hit for positions, using cached data")
                        return self._positions_cache if self._positions_cache is not None else []
                    else:
                        error_text = await response.text()
                        logger.error(f"MetaAPI positions error {response.status}: {error_text}")
                        return self._positions_cache if self._positions_cache is not None else []
        except Exception as e:
            logger.error(f"Error getting MetaAPI positions: {e}")
            return self._positions_cache if self._positions_cache is not None else []
    
    async def get_symbols(self) -> List[Dict[str, Any]]:
        """Get all available symbols from MetaAPI broker"""
        try:
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/symbols"
            
            # Create SSL context that doesn't verify certificates
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        symbols = await response.json()
                        logger.info(f"✅ Retrieved {len(symbols)} symbols from MetaAPI")
                        return symbols
                    else:
                        error_text = await response.text()
                        logger.error(f"MetaAPI symbols error {response.status}: {error_text}")
                        return []
        except Exception as e:
            logger.error(f"Error getting MetaAPI symbols: {e}")
            return []
    
    async def create_market_order(self, symbol: str, order_type: str, volume: float,
                                 sl: Optional[float] = None,
                                 tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Create a market order via MetaAPI (alias for place_order)"""
        return await self.place_order(symbol, order_type, volume, None, sl, tp)
    
    async def place_order(self, symbol: str, order_type: str, volume: float, 
                         price: Optional[float] = None,
                         sl: Optional[float] = None, 
                         tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a trading order via MetaAPI"""
        try:
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/trade"
            
            # Prepare order payload - MARKET ORDER (kein Preis!)
            payload = {
                "actionType": "ORDER_TYPE_BUY" if order_type.upper() == "BUY" else "ORDER_TYPE_SELL",
                "symbol": symbol,
                "volume": volume
            }
            
            # Stop Loss und Take Profit hinzufügen
            if sl:
                payload["stopLoss"] = sl
            if tp:
                payload["takeProfit"] = tp
            
            # WICHTIG: openPrice NICHT bei Market Orders!
            # Nur bei Limit/Pending Orders verwenden
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self._get_headers(), 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status in [200, 201]:
                        result = await response.json()
                        
                        # DEBUG: Log komplette Response
                        logger.info(f"MetaAPI Response: {result}")
                        
                        # Extrahiere Ticket - versuche verschiedene Felder
                        ticket = (result.get('orderId') or 
                                 result.get('positionId') or 
                                 result.get('stringCode') or
                                 result.get('numericCode') or
                                 'unknown')
                        
                        logger.info(f"✅ MetaAPI Order placed: {order_type} {volume} {symbol} - Ticket: {ticket}")
                        
                        return {
                            "success": True,
                            "ticket": ticket,
                            "volume": volume,
                            "price": result.get('price', price or 0.0),
                            "type": order_type,
                            "response": result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"MetaAPI order failed {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error placing MetaAPI order: {e}")
            return None
    
    async def get_symbol_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current price (tick) for a symbol from MetaAPI
        
        Args:
            symbol: Trading symbol (e.g., 'XAUUSD', 'XAGUSD')
        
        Returns:
            Dict with bid, ask, time
        """
        try:
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/symbols/{symbol}/current-tick"
            
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        tick = await response.json()
                        return {
                            'symbol': symbol,
                            'bid': tick.get('bid', 0.0),
                            'ask': tick.get('ask', 0.0),
                            'price': (tick.get('bid', 0.0) + tick.get('ask', 0.0)) / 2,
                            'time': tick.get('time', '')
                        }
                    else:
                        return None
        except Exception as e:
            logger.debug(f"Error fetching tick for {symbol}: {e}")
            return None
    
    async def get_candles(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical candle data from MetaAPI
        
        Args:
            symbol: Trading symbol (e.g., 'XAUUSD', 'XAGUSD')
            timeframe: Timeframe - '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
            limit: Number of candles to retrieve (max 1000)
        
        Returns:
            List of candle data with OHLCV
        """
        try:
            # Map timeframe to MetaAPI format
            timeframe_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
            }
            tf = timeframe_map.get(timeframe, '1h')
            
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/historical-market-data/symbols/{symbol}/timeframes/{tf}/candles"
            
            # Create SSL context
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params={"limit": min(limit, 1000)},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Retrieved {len(data)} candles for {symbol} ({tf})")
                        return data
                    else:
                        error_text = await response.text()
                        logger.warning(f"MetaAPI candles unavailable for {symbol}: {response.status}")
                        return None
        except Exception as e:
            logger.warning(f"Error fetching MetaAPI candles for {symbol}: {e}")
            return None
    
    async def close_position(self, position_id: str) -> bool:
        """Close an open position via MetaAPI"""
        try:
            url = f"{self.base_url}/users/current/accounts/{self.account_id}/trade"
            
            payload = {
                "actionType": "POSITION_CLOSE_ID",
                "positionId": position_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=self._get_headers(), 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status in [200, 201]:
                        logger.info(f"✅ MetaAPI Position {position_id} closed")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"MetaAPI close failed {response.status}: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error closing MetaAPI position: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MetaAPI (no action needed for REST API)"""
        self.connected = False
        logger.info("Disconnected from MetaAPI")


# Global MetaAPI connector instance
_metaapi_connector: Optional[MetaAPIConnector] = None

async def get_metaapi_connector(account_id: str = None, token: str = None) -> MetaAPIConnector:
    """Get or create MetaAPI connector instance"""
    global _metaapi_connector
    
    # Use environment variables if not provided
    if account_id is None:
        account_id = os.environ.get('METAAPI_ACCOUNT_ID')
    if token is None:
        token = os.environ.get('METAAPI_TOKEN')
    
    if not account_id or not token:
        raise ValueError("MetaAPI credentials not provided")
    
    if _metaapi_connector is None:
        _metaapi_connector = MetaAPIConnector(account_id, token)
        await _metaapi_connector.connect()
    
    return _metaapi_connector
