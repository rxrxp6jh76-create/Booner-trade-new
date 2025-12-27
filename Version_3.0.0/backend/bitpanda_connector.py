"""
Bitpanda Public API Connector (Offizielle API)
Basierend auf: https://developers.bitpanda.com/#bitpanda-public-api

Base URL: https://api.bitpanda.com/v1
Authentication: X-Api-Key Header
"""

import logging
import os
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BitpandaConnector:
    """Bitpanda Public API connection handler"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bitpanda.com/v1"
        self.connected = False
        self.balance = 0.0
        self.balances = {}
        
        logger.info(f"Bitpanda Public API Connector initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Bitpanda Public API"""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def connect(self) -> bool:
        """Connect to Bitpanda and verify credentials"""
        try:
            account_info = await self.get_account_info()
            if account_info:
                self.connected = True
                logger.info(f"✅ Connected to Bitpanda Public API")
                return True
            else:
                logger.error("Failed to connect to Bitpanda")
                return False
        except Exception as e:
            logger.error(f"Bitpanda connection error: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information from Bitpanda
        
        Ruft Fiat Wallets und Asset Wallets ab und kombiniert sie.
        """
        try:
            # Fiat Wallets abrufen
            fiat_url = f"{self.base_url}/fiatwallets"
            
            async with aiohttp.ClientSession() as session:
                # 1. Fiat Wallets
                async with session.get(fiat_url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        fiat_data = await response.json()
                        
                        total_balance_eur = 0
                        
                        # Parse Fiat Wallets
                        for wallet in fiat_data.get('data', []):
                            attrs = wallet.get('attributes', {})
                            fiat_symbol = attrs.get('fiat_symbol', '')
                            balance = float(attrs.get('balance', 0))
                            
                            self.balances[fiat_symbol] = {
                                'available': balance,
                                'locked': 0,
                                'total': balance,
                                'type': 'fiat'
                            }
                            
                            # EUR-Balance für Gesamt-Balance
                            if fiat_symbol == 'EUR':
                                total_balance_eur += balance
                        
                        # 2. Asset Wallets (Crypto + Commodities)
                        asset_url = f"{self.base_url}/asset-wallets"
                        async with session.get(asset_url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as asset_response:
                            if asset_response.status == 200:
                                asset_data = await asset_response.json()
                                
                                # Parse Asset Wallets (verschachtelte Struktur)
                                data_attrs = asset_data.get('data', {}).get('attributes', {})
                                
                                # Cryptocoin Wallets
                                crypto_wallets = data_attrs.get('cryptocoin', {}).get('attributes', {}).get('wallets', [])
                                for wallet in crypto_wallets:
                                    attrs = wallet.get('attributes', {})
                                    symbol = attrs.get('cryptocoin_symbol', '')
                                    balance = float(attrs.get('balance', 0))
                                    
                                    if balance > 0:
                                        self.balances[symbol] = {
                                            'available': balance,
                                            'locked': 0,
                                            'total': balance,
                                            'type': 'crypto'
                                        }
                                
                                # Commodity Wallets (Gold, Silver, etc.)
                                commodity_data = data_attrs.get('commodity', {})
                                if isinstance(commodity_data, dict):
                                    for category, category_data in commodity_data.items():
                                        if isinstance(category_data, dict):
                                            wallets = category_data.get('attributes', {}).get('wallets', [])
                                            for wallet in wallets:
                                                attrs = wallet.get('attributes', {})
                                                symbol = attrs.get('cryptocoin_symbol', '')
                                                balance = float(attrs.get('balance', 0))
                                                
                                                if balance > 0:
                                                    self.balances[symbol] = {
                                                        'available': balance,
                                                        'locked': 0,
                                                        'total': balance,
                                                        'type': 'commodity'
                                                    }
                        
                        self.balance = total_balance_eur
                        
                        logger.info(f"Bitpanda Account Info: EUR Balance={self.balance:.2f}, Total Wallets={len(self.balances)}")
                        
                        return {
                            "balance": self.balance,
                            "equity": self.balance,
                            "margin": 0.0,
                            "free_margin": self.balance,
                            "profit": 0.0,
                            "currency": "EUR",
                            "leverage": 1,
                            "login": "Bitpanda Account",
                            "server": "Bitpanda",
                            "trade_mode": "LIVE",
                            "name": "Bitpanda Trading Account",
                            "broker": "Bitpanda",
                            "balances": self.balances
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Bitpanda error {response.status}: {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error getting Bitpanda account info: {e}")
            return None
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get holdings (wallet balances) from Bitpanda
        
        Bitpanda ist ein Broker, keine Exchange. "Positionen" sind hier
        die Wallet-Guthaben (Holdings).
        """
        try:
            # Asset Wallets abrufen
            url = f"{self.base_url}/asset-wallets"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result = []
                        data_attrs = data.get('data', {}).get('attributes', {})
                        
                        # Cryptocoin Wallets
                        crypto_wallets = data_attrs.get('cryptocoin', {}).get('attributes', {}).get('wallets', [])
                        for wallet in crypto_wallets:
                            attrs = wallet.get('attributes', {})
                            balance = float(attrs.get('balance', 0))
                            
                            if balance > 0:
                                result.append({
                                    "ticket": wallet.get('id', ''),
                                    "symbol": attrs.get('cryptocoin_symbol', ''),
                                    "type": "HOLD",
                                    "volume": balance,
                                    "price_open": 0,
                                    "price_current": 0,
                                    "profit": 0.0,
                                    "swap": 0.0,
                                    "time": "",
                                    "sl": None,
                                    "tp": None
                                })
                        
                        # Commodity Wallets
                        commodity_data = data_attrs.get('commodity', {})
                        if isinstance(commodity_data, dict):
                            for category, category_data in commodity_data.items():
                                if isinstance(category_data, dict):
                                    wallets = category_data.get('attributes', {}).get('wallets', [])
                                    for wallet in wallets:
                                        attrs = wallet.get('attributes', {})
                                        balance = float(attrs.get('balance', 0))
                                        
                                        if balance > 0:
                                            result.append({
                                                "ticket": wallet.get('id', ''),
                                                "symbol": attrs.get('cryptocoin_symbol', ''),
                                                "type": "HOLD",
                                                "volume": balance,
                                                "price_open": 0,
                                                "price_current": 0,
                                                "profit": 0.0,
                                                "swap": 0.0,
                                                "time": "",
                                                "sl": None,
                                                "tp": None
                                            })
                        
                        logger.info(f"Bitpanda Holdings: {len(result)} assets with balance")
                        return result
                    else:
                        logger.error(f"Failed to get Bitpanda holdings")
                        return []
        except Exception as e:
            logger.error(f"Error getting Bitpanda holdings: {e}")
            return []
    
    async def get_trades(self, trade_type: Optional[str] = None, page_size: int = 50) -> List[Dict[str, Any]]:
        """Get trade history from Bitpanda
        
        Args:
            trade_type: Optional filter for "buy" or "sell"
            page_size: Number of trades to return
        
        Returns:
            List of trades
        """
        try:
            url = f"{self.base_url}/trades"
            params = {"page_size": page_size}
            if trade_type:
                params["type"] = trade_type
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._get_headers(), params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        trades = []
                        for trade_item in data.get('data', []):
                            attrs = trade_item.get('attributes', {})
                            
                            trades.append({
                                "id": trade_item.get('id', ''),
                                "type": attrs.get('type', ''),
                                "status": attrs.get('status', ''),
                                "cryptocoin_id": attrs.get('cryptocoin_id', ''),
                                "amount_fiat": float(attrs.get('amount_fiat', 0)),
                                "amount_cryptocoin": float(attrs.get('amount_cryptocoin', 0)),
                                "price": float(attrs.get('price', 0)),
                                "time": attrs.get('time', {}).get('date_iso8601', ''),
                                "is_swap": attrs.get('is_swap', False)
                            })
                        
                        logger.info(f"Bitpanda Trades: {len(trades)} retrieved")
                        return trades
                    else:
                        logger.error(f"Failed to get Bitpanda trades")
                        return []
        except Exception as e:
            logger.error(f"Error getting Bitpanda trades: {e}")
            return []
    
    async def place_order(self, symbol: str, order_type: str, volume: float, 
                         price: Optional[float] = None,
                         sl: Optional[float] = None, 
                         tp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a trading order via Bitpanda
        
        HINWEIS: Die Public API bietet KEIN direktes Trading-Endpoint.
        Trading muss über die Bitpanda Webseite oder Mobile App erfolgen.
        """
        logger.warning(f"Bitpanda Public API: Automatisches Trading nicht unterstützt")
        logger.warning(f"Bitte handeln Sie manuell auf bitpanda.com oder in der App")
        
        return {
            "success": False,
            "message": "Bitpanda Public API unterstützt kein automatisches Trading. Bitte manuell auf bitpanda.com handeln.",
            "ticket": "N/A",
            "volume": volume,
            "price": price or 0.0,
            "type": order_type
        }
    
    async def close_position(self, position_id: str) -> bool:
        """Close a position (sell asset) via Bitpanda
        
        HINWEIS: Die Public API bietet KEIN direktes Verkaufs-Endpoint.
        Verkäufe müssen über die Bitpanda Webseite oder Mobile App erfolgen.
        """
        logger.warning(f"Bitpanda Public API: Automatisches Verkaufen nicht unterstützt")
        logger.warning(f"Bitte verkaufen Sie Assets manuell auf bitpanda.com oder in der App")
        
        return False
    
    def disconnect(self):
        """Disconnect from Bitpanda"""
        self.connected = False
        logger.info("Disconnected from Bitpanda Public API")


# Global Bitpanda connector instance
_bitpanda_connector: Optional[BitpandaConnector] = None

async def get_bitpanda_connector(api_key: str = None) -> BitpandaConnector:
    """Get or create Bitpanda connector instance"""
    global _bitpanda_connector
    
    # Use environment variable if not provided
    if api_key is None:
        api_key = os.environ.get('BITPANDA_API_KEY')
    
    if not api_key:
        raise ValueError("Bitpanda API key not provided")
    
    if _bitpanda_connector is None:
        _bitpanda_connector = BitpandaConnector(api_key)
        await _bitpanda_connector.connect()
    
    return _bitpanda_connector
