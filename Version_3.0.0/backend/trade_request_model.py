"""
Trade Request Models für API
"""
from pydantic import BaseModel
from typing import Optional

class TradeExecuteRequest(BaseModel):
    """Request Model für /trades/execute"""
    trade_type: str  # "BUY" or "SELL"
    price: float
    quantity: Optional[float] = None
    commodity: str = "WTI_CRUDE"
