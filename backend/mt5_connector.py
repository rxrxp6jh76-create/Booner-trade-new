"""
MetaTrader 5 Connector for Linux/Cloud environments
Supports direct MT5 connection on Windows or REST API for remote access
"""

import logging
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class MT5Connector:
    """MetaTrader 5 connection handler with fallback support"""
    
    def __init__(self, login: str, password: str, server: str):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False
        self.mt5_available = False
        self.balance = 0.0
        self.equity = 0.0
        self.margin = 0.0
        self.free_margin = 0.0
        
        # Try to import MT5 library
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.mt5_available = True
            logger.info("MetaTrader5 library available - direct connection possible")
        except ImportError:
            logger.warning("MetaTrader5 library not available - using REST API fallback")
            self.mt5 = None
            self.mt5_available = False
    
    async def connect(self) -> bool:
        """Connect to MT5 terminal"""
        try:
            if self.mt5_available:
                return await self._connect_direct()
            else:
                return await self._connect_rest_api()
        except Exception as e:
            logger.error(f"Failed to connect to MT5: {e}")
            return False
    
    async def _connect_direct(self) -> bool:
        """Direct connection using MT5 Python library (Windows only)"""
        try:
            # Initialize MT5
            if not self.mt5.initialize():
                logger.error(f"MT5 initialize() failed: {self.mt5.last_error()}")
                return False
            
            # Login to account
            authorized = self.mt5.login(
                login=int(self.login),
                password=self.password,
                server=self.server
            )
            
            if not authorized:
                logger.error(f"MT5 login failed: {self.mt5.last_error()}")
                self.mt5.shutdown()
                return False
            
            # Get account info
            account_info = self.mt5.account_info()
            if account_info:
                self.balance = account_info.balance
                self.equity = account_info.equity
                self.margin = account_info.margin
                self.free_margin = account_info.margin_free
                
                logger.info(f"✅ Connected to MT5: {self.server}")
                logger.info(f"Account: {self.login}, Balance: {self.balance:.2f} {account_info.currency}")
                self.connected = True
                return True
            else:
                logger.error("Failed to get account info")
                return False
                
        except Exception as e:
            logger.error(f"Error in direct MT5 connection: {e}")
            return False
    
    async def _connect_rest_api(self) -> bool:
        """
        Connect via REST API for remote MT5 access
        This requires a REST API bridge running on the machine with MT5
        For now, we'll return mock data until you set up the bridge
        """
        logger.warning("⚠️ REST API mode: Returning mock data")
        logger.info("To use real MT5 data, you need to:")
        logger.info("1. Install MT5 on Windows machine")
        logger.info("2. Set up MT5 REST API bridge (ZeroMQ/REST)")
        logger.info("3. Configure API endpoint in environment")
        
        # For now, simulate connection with your real account details
        self.connected = True
        self.balance = 2000.0  # Your actual balance from MT5
        self.equity = 2000.0
        self.margin = 0.0
        self.free_margin = 2000.0
        
        logger.info(f"✅ Simulated MT5 connection: {self.server}")
        logger.info(f"Account: {self.login}, Balance: {self.balance:.2f} EUR")
        
        return True
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get current account information"""
        if not self.connected:
            await self.connect()
        
        if not self.connected:
            return None
        
        try:
            if self.mt5_available and self.mt5:
                account = self.mt5.account_info()
                if account:
                    return {
                        "balance": account.balance,
                        "equity": account.equity,
                        "margin": account.margin,
                        "free_margin": account.margin_free,
                        "profit": account.profit,
                        "currency": account.currency,
                        "leverage": account.leverage,
                        "login": account.login,
                        "server": account.server,
                        "trade_mode": "REAL" if "Demo" not in account.server else "DEMO"
                    }
            else:
                # REST API or mock mode
                return {
                    "balance": self.balance,
                    "equity": self.equity,
                    "margin": self.margin,
                    "free_margin": self.free_margin,
                    "profit": self.equity - self.balance,
                    "currency": "EUR",
                    "leverage": 500,
                    "login": self.login,
                    "server": self.server,
                    "trade_mode": "REAL" if "Demo" not in self.server else "DEMO"
                }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        if not self.connected:
            await self.connect()
        
        if not self.connected:
            return []
        
        try:
            if self.mt5_available and self.mt5:
                positions = self.mt5.positions_get()
                if positions:
                    return [
                        {
                            "ticket": pos.ticket,
                            "symbol": pos.symbol,
                            "type": "BUY" if pos.type == 0 else "SELL",
                            "volume": pos.volume,
                            "price_open": pos.price_open,
                            "price_current": pos.price_current,
                            "profit": pos.profit,
                            "swap": pos.swap,
                            "time": datetime.fromtimestamp(pos.time)
                        }
                        for pos in positions
                    ]
            else:
                # REST API or mock mode
                return []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def place_order(self, symbol: str, order_type: str, volume: float, 
                         price: Optional[float] = None,
                         sl: Optional[float] = None, 
                         tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a trading order"""
        if not self.connected:
            await self.connect()
        
        if not self.connected:
            logger.error("Cannot place order: Not connected to MT5")
            return None
        
        try:
            if self.mt5_available and self.mt5:
                # Prepare order request
                request = {
                    "action": self.mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": self.mt5.ORDER_TYPE_BUY if order_type == "BUY" else self.mt5.ORDER_TYPE_SELL,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "WTI Smart Trader",
                    "type_time": self.mt5.ORDER_TIME_GTC,
                    "type_filling": self.mt5.ORDER_FILLING_IOC,
                }
                
                if sl:
                    request["sl"] = sl
                if tp:
                    request["tp"] = tp
                if price:
                    request["price"] = price
                
                # Send order
                result = self.mt5.order_send(request)
                
                if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                    logger.info(f"✅ Order placed: {order_type} {volume} {symbol} at {result.price}")
                    return {
                        "success": True,
                        "ticket": result.order,
                        "volume": volume,
                        "price": result.price,
                        "type": order_type
                    }
                else:
                    logger.error(f"Order failed: {result.retcode} - {result.comment}")
                    return None
            else:
                # REST API or mock mode
                logger.warning(f"⚠️ MOCK ORDER: {order_type} {volume} {symbol}")
                logger.warning("Order not sent to real MT5 - REST API not configured")
                return {
                    "success": True,
                    "ticket": 123456789,
                    "volume": volume,
                    "price": price or 0.0,
                    "type": order_type,
                    "mock": True
                }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def close_position(self, ticket: int) -> bool:
        """Close an open position"""
        if not self.connected:
            await self.connect()
        
        if not self.connected:
            return False
        
        try:
            if self.mt5_available and self.mt5:
                position = self.mt5.positions_get(ticket=ticket)
                if not position:
                    logger.error(f"Position {ticket} not found")
                    return False
                
                position = position[0]
                
                # Prepare close request
                request = {
                    "action": self.mt5.TRADE_ACTION_DEAL,
                    "symbol": position.symbol,
                    "volume": position.volume,
                    "type": self.mt5.ORDER_TYPE_SELL if position.type == 0 else self.mt5.ORDER_TYPE_BUY,
                    "position": ticket,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Close by WTI Smart Trader",
                    "type_time": self.mt5.ORDER_TIME_GTC,
                    "type_filling": self.mt5.ORDER_FILLING_IOC,
                }
                
                result = self.mt5.order_send(request)
                
                if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                    logger.info(f"✅ Position {ticket} closed")
                    return True
                else:
                    logger.error(f"Close failed: {result.retcode} - {result.comment}")
                    return False
            else:
                # REST API or mock mode
                logger.warning(f"⚠️ MOCK CLOSE: Position {ticket}")
                return True
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        try:
            if self.mt5_available and self.mt5:
                self.mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")


# Global MT5 connector instance
_mt5_connector: Optional[MT5Connector] = None

async def get_mt5_connector(login: str, password: str, server: str) -> MT5Connector:
    """Get or create MT5 connector instance"""
    global _mt5_connector
    
    if _mt5_connector is None:
        _mt5_connector = MT5Connector(login, password, server)
        await _mt5_connector.connect()
    
    return _mt5_connector
