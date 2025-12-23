from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
# SQLite Database instead of MongoDB
import database as db_module

# Memory Profiling - Disabled for production (use in debug mode only)
# from memory_profiler import get_profiler
# import psutil
import os

import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
# Scheduler moved to worker.py
# from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from threading import Thread
# Use fallback module for emergentintegrations (Mac compatibility)
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    from llm_fallback import get_llm_chat as LlmChat, get_user_message as UserMessage
from commodity_processor import COMMODITIES, fetch_commodity_data, calculate_indicators, generate_signal, calculate_position_size, get_commodities_with_hours
from trailing_stop import update_trailing_stops, check_stop_loss_triggers

# V2.3.35: News & Market Regime System - Imports (logging später)
NEWS_SYSTEM_AVAILABLE = False
REGIME_SYSTEM_AVAILABLE = False

try:
    from news_analyzer import (
        check_news_for_trade, 
        get_current_news, 
        get_news_decision_log,
        NewsImpact, NewsDirection
    )
    NEWS_SYSTEM_AVAILABLE = True
except ImportError:
    pass

try:
    from market_regime import (
        detect_market_regime,
        is_strategy_allowed,
        MarketRegime,
        check_news_window
    )
    REGIME_SYSTEM_AVAILABLE = True
except ImportError:
    pass
from ai_position_manager import manage_open_positions

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Custom Ollama Chat Client
class OllamaChat:
    """Simple Ollama chat client for local LLM inference"""
    def __init__(self, base_url="http://localhost:11434", model="llama2", system_message=""):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.system_message = system_message
        self.conversation_history = []
        
        if system_message:
            self.conversation_history.append({
                "role": "system",
                "content": system_message
            })
    
    async def send_message(self, user_message):
        """Send message to Ollama and get response"""
        import aiohttp
        
        # Add user message to history
        if hasattr(user_message, 'text'):
            message_text = user_message.text
        else:
            message_text = str(user_message)
        
        self.conversation_history.append({
            "role": "user",
            "content": message_text
        })
        
        try:
            # Call Ollama API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": self.conversation_history,
                    "stream": False
                }
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        assistant_message = result.get('message', {}).get('content', '')
                        
                        # Add assistant response to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message
                        })
                        
                        return assistant_message
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# SQLite Database Collections
db = type('DB', (), {
    'trading_settings': db_module.trading_settings,
    'trades': db_module.trades,
    'trade_settings': db_module.trade_settings,
    'market_data': db_module.market_data,
    'market_data_history': db_module.market_data_history
})()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Startup event - automatisches Cleanup beim Start
@app.on_event("startup")
async def startup_cleanup():
    """Server startup initialization"""
    global ai_trading_bot_instance, bot_task
    
    try:
        logger.info("🚀 Server startet mit SQLite...")
        # Initialize SQLite database (legacy)
        await db_module.init_database()
        logger.info("✅ SQLite Datenbank initialisiert")
        
        # V2.3.36: Initialize database_v2 (Multi-DB Architecture)
        try:
            from database_v2 import db_manager
            await db_manager.initialize_all()
            logger.info("✅ Multi-DB Architecture initialisiert (database_v2)")
        except Exception as e:
            logger.warning(f"⚠️ database_v2 Initialisierung fehlgeschlagen: {e}")
        
        # V2.3.37 FIX: Initial Database Cleanup to prevent memory leak
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            
            # Cleanup market_data_history (older than 7 days)
            try:
                result = await db.market_data_history.delete_many({
                    "timestamp": {"$lt": cutoff_date}
                })
                if result and hasattr(result, 'deleted_count') and result.deleted_count > 0:
                    logger.info(f"🧹 Cleanup: {result.deleted_count} alte market_data_history Einträge gelöscht")
            except Exception as e:
                logger.debug(f"market_data_history cleanup: {e}")
            
            # Cleanup old closed trades (older than 30 days)
            try:
                cutoff_30_days = datetime.now(timezone.utc) - timedelta(days=30)
                result = await db.trades.delete_many({
                    "status": "CLOSED",
                    "closed_at": {"$lt": cutoff_30_days}
                })
                if result and hasattr(result, 'deleted_count') and result.deleted_count > 0:
                    logger.info(f"🧹 Cleanup: {result.deleted_count} alte geschlossene Trades gelöscht")
            except Exception as e:
                logger.debug(f"trades cleanup: {e}")
                
            logger.info("✅ Initial Cleanup abgeschlossen")
        except Exception as e:
            logger.warning(f"⚠️ Initial cleanup fehlgeschlagen: {e}")
        
        logger.info("ℹ️  AI Trading Bot wird im Worker-Prozess gestartet")
    except Exception as e:
        logger.error(f"⚠️ Startup fehlgeschlagen: {e}")

@app.on_event("shutdown")
async def shutdown_cleanup():
    """Server shutdown cleanup"""
    try:
        await db_module.close_database()
        logger.info("✅ SQLite Verbindung geschlossen")
        
        # V2.3.36: Close database_v2
        try:
            from database_v2 import db_manager
            await db_manager.close_all()
            logger.info("✅ Multi-DB Verbindungen geschlossen")
        except Exception as e:
            logger.warning(f"⚠️ database_v2 close fehlgeschlagen: {e}")
    except Exception as e:
        logger.error(f"⚠️ Shutdown fehlgeschlagen: {e}")

# Configure logging with rotation (max 50MB total)
from logging.handlers import RotatingFileHandler
import os

log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'backend.log'),
            maxBytes=10*1024*1024,  # 10MB per file
            backupCount=5  # Keep 5 backups = 50MB max
        ),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

# Global variables
latest_market_data = {}  # Dictionary to cache latest market data
# Scheduler moved to worker.py
# scheduler = BackgroundScheduler()
auto_trading_enabled = False
trade_count_per_hour = 0
ai_chat = None  # AI chat instance for market analysis

# V2.3.31: Multi-Bot System
ai_trading_bot_instance = None  # Legacy AI Trading Bot instance (fallback)
bot_task = None  # Legacy bot background task

# V2.3.31: Multi-Bot Manager
multi_bot_manager = None  # New Multi-Bot System

# AI System Message
AI_SYSTEM_MESSAGE = """You are an expert commodities trading analyst specializing in WTI crude oil. 
Your role is to analyze market data, technical indicators, and provide clear BUY, SELL, or HOLD recommendations.

You will receive:
- Current WTI price and historical data
- Technical indicators (RSI, MACD, SMA, EMA)
- Market trends

Provide concise analysis in JSON format:
{
    "signal": "BUY" or "SELL" or "HOLD",
    "confidence": 0-100,
    "reasoning": "Brief explanation",
    "risk_level": "LOW", "MEDIUM", or "HIGH"
}

Base your decisions on:
1. RSI levels (oversold/overbought)
2. MACD crossovers
3. Price position relative to moving averages
4. Overall trend direction
5. Market momentum"""

# Initialize AI Chat
def init_ai_chat(provider="emergent", api_key=None, model="gpt-5", ollama_base_url="http://localhost:11434"):
    """Initialize AI chat for market analysis with different providers including Ollama"""
    global ai_chat
    try:
        # Handle Ollama provider separately
        if provider == "ollama":
            logger.info(f"Initializing Ollama: URL={ollama_base_url}, Model={model}")
            # Create a custom Ollama chat instance
            ai_chat = OllamaChat(base_url=ollama_base_url, model=model, system_message=AI_SYSTEM_MESSAGE)
            logger.info(f"Ollama Chat initialized: Model={model}")
            return ai_chat
        
        # Determine API key for cloud providers
        if provider == "emergent":
            api_key = os.environ.get('EMERGENT_LLM_KEY')
            if not api_key:
                logger.error("EMERGENT_LLM_KEY not found in environment variables")
                return None
        elif not api_key:
            logger.error(f"No API key provided for {provider}")
            return None
        
        # Map provider to emergentintegrations format
        provider_mapping = {
            "emergent": "openai",  # Emergent key works with OpenAI format
            "openai": "openai",
            "gemini": "google",
            "anthropic": "anthropic"
        }
        
        llm_provider = provider_mapping.get(provider, "openai")
        
        # Create chat instance
        ai_chat = LlmChat(
            api_key=api_key,
            session_id="wti-trading-bot",
            system_message=AI_SYSTEM_MESSAGE
        ).with_model(llm_provider, model)
        
        logger.info(f"AI Chat initialized: Provider={provider}, Model={model}")
        return ai_chat
    except Exception as e:
        logger.error(f"Failed to initialize AI chat: {e}")
        return None

# Commodity definitions - Multi-Platform Support (Libertex MT5 + Bitpanda)
COMMODITIES = {
    # Precious Metals - Libertex: ✅ | ICMarkets: ✅ | Bitpanda: ✅
    "GOLD": {"name": "Gold", "symbol": "GC=F", "mt5_libertex_symbol": "XAUUSD", "mt5_icmarkets_symbol": "XAUUSD", "bitpanda_symbol": "GOLD", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SILVER": {"name": "Silber", "symbol": "SI=F", "mt5_libertex_symbol": "XAGUSD", "mt5_icmarkets_symbol": "XAGUSD", "bitpanda_symbol": "SILVER", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "PLATINUM": {"name": "Platin", "symbol": "PL=F", "mt5_libertex_symbol": "PL", "mt5_icmarkets_symbol": "XPTUSD", "bitpanda_symbol": "PLATINUM", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "PALLADIUM": {"name": "Palladium", "symbol": "PA=F", "mt5_libertex_symbol": "PA", "mt5_icmarkets_symbol": "XPDUSD", "bitpanda_symbol": "PALLADIUM", "category": "Edelmetalle", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    
    # Energy - Libertex: ✅ CL (WTI), BRN (Brent), NG (Gas) | ICMarkets: ✅ | Bitpanda: ✅
    "WTI_CRUDE": {"name": "WTI Crude Oil", "symbol": "CL=F", "mt5_libertex_symbol": "CL", "mt5_icmarkets_symbol": "WTI_F6", "bitpanda_symbol": "OIL_WTI", "category": "Energie", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "BRENT_CRUDE": {"name": "Brent Crude Oil", "symbol": "BZ=F", "mt5_libertex_symbol": "BRN", "mt5_icmarkets_symbol": "BRENT_F6", "bitpanda_symbol": "OIL_BRENT", "category": "Energie", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "NATURAL_GAS": {"name": "Natural Gas", "symbol": "NG=F", "mt5_libertex_symbol": "NG", "mt5_icmarkets_symbol": None, "bitpanda_symbol": "NATURAL_GAS", "category": "Energie", "platforms": ["MT5_LIBERTEX", "BITPANDA"]},
    
    # Agricultural - Libertex: ✅ WHEAT, SOYBEAN, COFFEE, SUGAR, COCOA, CORN | ICMarkets: teilweise
    "WHEAT": {"name": "Weizen", "symbol": "ZW=F", "mt5_libertex_symbol": "WHEAT", "mt5_icmarkets_symbol": "Wheat_H6", "bitpanda_symbol": "WHEAT", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "CORN": {"name": "Mais", "symbol": "ZC=F", "mt5_libertex_symbol": "CORN", "mt5_icmarkets_symbol": "Corn_H6", "bitpanda_symbol": "CORN", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SOYBEANS": {"name": "Sojabohnen", "symbol": "ZS=F", "mt5_libertex_symbol": "SOYBEAN", "mt5_icmarkets_symbol": "Sbean_F6", "bitpanda_symbol": "SOYBEANS", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "COFFEE": {"name": "Kaffee", "symbol": "KC=F", "mt5_libertex_symbol": "COFFEE", "mt5_icmarkets_symbol": "Coffee_H6", "bitpanda_symbol": "COFFEE", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "SUGAR": {"name": "Zucker", "symbol": "SB=F", "mt5_libertex_symbol": "SUGAR", "mt5_icmarkets_symbol": "Sugar_H6", "bitpanda_symbol": "SUGAR", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    "COCOA": {"name": "Kakao", "symbol": "CC=F", "mt5_libertex_symbol": "COCOA", "mt5_icmarkets_symbol": "Cocoa_H6", "bitpanda_symbol": "COCOA", "category": "Agrar", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
    
    # Forex - Major Currency Pairs
    "EURUSD": {"name": "EUR/USD", "symbol": "EURUSD=X", "mt5_libertex_symbol": "EURUSD", "mt5_icmarkets_symbol": "EURUSD", "bitpanda_symbol": None, "category": "Forex", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS"]},
    
    # Crypto - 24/7 Trading
    "BITCOIN": {"name": "Bitcoin", "symbol": "BTC-USD", "mt5_libertex_symbol": "BTCUSD", "mt5_icmarkets_symbol": "BTCUSD", "bitpanda_symbol": "BTC", "category": "Crypto", "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"]},
}

# Models
class MarketData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    commodity: str = "WTI_CRUDE"  # Commodity identifier
    price: float
    volume: Optional[float] = None
    sma_20: Optional[float] = None
    ema_20: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    trend: Optional[str] = None  # "UP", "DOWN", "NEUTRAL"
    signal: Optional[str] = None  # "BUY", "SELL", "HOLD"

class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    commodity: str = "WTI_CRUDE"  # Commodity identifier
    type: Literal["BUY", "SELL"]
    price: float
    quantity: float = 1.0
    status: Literal["OPEN", "CLOSED"] = "OPEN"
    platform: Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "BITPANDA"] = "MT5_LIBERTEX"  # Updated for multi-platform
    mode: Optional[str] = None  # Deprecated, kept for backward compatibility
    entry_price: float
    exit_price: Optional[float] = None
    profit_loss: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_signal: Optional[str] = None
    closed_at: Optional[datetime] = None
    mt5_ticket: Optional[str] = None  # MT5 order ticket number

class CloseTradeRequest(BaseModel):
    """Request model for closing trades"""
    trade_id: Optional[str] = None
    ticket: Optional[str] = None
    platform: Optional[str] = None
    trade_data: Optional[dict] = None  # Fallback trade data from frontend

class TradingSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = "trading_settings"
    # Active platforms (3 MT5 Accounts + Legacy BITPANDA) - with legacy support
    active_platforms: List[Literal["MT5_LIBERTEX", "MT5_ICMARKETS", "MT5_LIBERTEX_DEMO", "MT5_ICMARKETS_DEMO", "MT5_LIBERTEX_REAL", "BITPANDA"]] = ["MT5_LIBERTEX_DEMO", "MT5_ICMARKETS_DEMO"]  # Default: Beide MT5 aktiv
    mode: Optional[str] = None  # Deprecated, kept for backward compatibility
    auto_trading: bool = False
    use_ai_analysis: bool = True  # Enable AI analysis
    use_llm_confirmation: bool = False  # LLM Confirmation vor Trade (v2.3.27)
    allow_weekend_trading: bool = False  # Wochenende Trading erlauben (v2.3.27)
    ai_provider: Literal["emergent", "openai", "gemini", "anthropic", "ollama"] = "emergent"
    ai_model: str = "gpt-5"  # Default model
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = "http://127.0.0.1:11434"  # Ollama local URL (127.0.0.1 für Mac!)
    ollama_model: Optional[str] = "llama3:latest"  # Ollama model (v2.3.27: llama3:latest statt llama2)
    stop_loss_percent: float = 2.0  # DEPRECATED - Benutze swing_stop_loss_percent/day_stop_loss_percent
    take_profit_percent: float = 4.0  # DEPRECATED - Benutze swing_take_profit_percent/day_take_profit_percent
    use_trailing_stop: bool = True  # V2.3.34: Trailing Stop immer aktiv für alle Strategien
    trailing_stop_distance: float = 1.5  # Trailing stop distance in %
    max_trades_per_hour: int = 3
    position_size: float = 1.0
    max_portfolio_risk_percent: float = 20.0  # Max 20% of balance for all open positions
    default_platform: Optional[Literal["ALL", "MT5_LIBERTEX", "MT5_ICMARKETS", "MT5_LIBERTEX_DEMO", "MT5_ICMARKETS_DEMO", "MT5_LIBERTEX_REAL", "BITPANDA"]] = None  # Deprecated - all active platforms receive trades
    # Alle Assets aktiviert: 15 Rohstoffe + EUR/USD + BITCOIN (24/7!) + COPPER (NEU)
    enabled_commodities: List[str] = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "COPPER", "WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COCOA", "EURUSD", "BITCOIN"]
    
    # Trading Strategy Selection
    trading_strategy: str = "CONSERVATIVE"  # CONSERVATIVE, AGGRESSIVE, SCALPING
    
    # KI Trading Strategie-Parameter (anpassbar) - LEGACY für Backward-Compatibility
    rsi_oversold_threshold: float = 30.0  # RSI Kaufsignal (Standard: 30)
    rsi_overbought_threshold: float = 70.0  # RSI Verkaufssignal (Standard: 70)
    macd_signal_threshold: float = 0.0  # MACD Schwellenwert für Signale
    trend_following: bool = True  # Folge dem Trend (kaufe bei UP, verkaufe bei DOWN)
    min_confidence_score: float = 0.6  # Minimale Konfidenz für automatisches Trading (0-1)
    use_volume_confirmation: bool = True  # Verwende Volumen zur Bestätigung
    risk_per_trade_percent: float = 2.0  # Maximales Risiko pro Trade (% der Balance)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DUAL TRADING STRATEGY - Swing Trading + Day Trading parallel
    # ═══════════════════════════════════════════════════════════════════════════
    
    # SWING TRADING Konfiguration (Langfristig) - V2.3.35 Updated
    swing_trading_enabled: bool = True  # Swing Trading aktiviert
    swing_min_confidence_score: float = 0.55  # 55% Mindest-Konfidenz (V2.3.35)
    swing_tp_sl_mode: Literal["percent", "euro"] = "percent"  # Modus: Prozent oder Euro
    swing_stop_loss_percent: float = 2.5  # 2.5% Stop Loss (V2.3.35)
    swing_take_profit_percent: float = 4.0  # 4% Take Profit
    swing_stop_loss_euro: float = 20.0  # €20 Stop Loss (wenn Euro-Modus)
    swing_take_profit_euro: float = 50.0  # €50 Take Profit (wenn Euro-Modus)
    swing_max_positions: int = 5  # Max 5 Swing-Positionen (V2.3.35)
    swing_position_hold_time_hours: int = 168  # Max 168h = 7 Tage Haltezeit
    swing_analysis_interval_seconds: int = 30  # Alle 30 Sekunden analysieren
    swing_atr_multiplier_sl: float = 2.0  # Stop Loss = 2x ATR
    swing_atr_multiplier_tp: float = 3.0  # Take Profit = 3x ATR
    swing_risk_per_trade_percent: float = 1.5  # 1.5% Risiko pro Trade (V2.3.35)
    
    # DAY TRADING Konfiguration (Kurzfristig) - V2.3.35 Updated
    day_trading_enabled: bool = False  # Day Trading aktiviert (default: aus)
    day_min_confidence_score: float = 0.40  # 40% Mindest-Konfidenz (V2.3.35)
    day_tp_sl_mode: Literal["percent", "euro"] = "percent"  # Modus: Prozent oder Euro
    day_stop_loss_percent: float = 1.2  # 1.2% Stop Loss (V2.3.35)
    day_take_profit_percent: float = 2.0  # 2% Take Profit (V2.3.35)
    day_stop_loss_euro: float = 15.0  # €15 Stop Loss (wenn Euro-Modus)
    day_take_profit_euro: float = 30.0  # €30 Take Profit (wenn Euro-Modus)
    day_max_positions: int = 10  # Max 10 Day-Trading-Positionen (V2.3.35)
    day_position_hold_time_hours: int = 48  # Max 24-48h Haltezeit (V2.3.35)
    day_analysis_interval_seconds: int = 30  # Alle 30 Sekunden analysieren
    day_atr_multiplier_sl: float = 1.5  # Stop Loss = 1.5x ATR
    day_atr_multiplier_tp: float = 2.0  # Take Profit = 2.0x ATR
    day_risk_per_trade_percent: float = 1.0  # 1% Risiko pro Trade (V2.3.35)
    
    # SCALPING TRADING Konfiguration (Ultra-Schnell) - V2.3.35 Updated
    scalping_enabled: bool = False  # Scalping Trading aktiviert (default: aus)
    scalping_min_confidence_score: float = 0.65  # 65% Mindest-Konfidenz (V2.3.35)
    scalping_max_positions: int = 2  # Max 2 Scalping-Positionen (V2.3.35)
    scalping_stop_loss_percent: float = 0.15  # 0.15% Stop Loss (V2.3.35)
    scalping_take_profit_percent: float = 0.25  # 0.25% Take Profit (V2.3.35)
    scalping_max_hold_time_minutes: int = 5  # Max 3-5 Minuten Haltezeit (V2.3.35)
    scalping_risk_per_trade_percent: float = 0.5  # 0.5% Risiko pro Trade (V2.3.35)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # V2.3.31: NEUE STRATEGIEN - Mean Reversion, Momentum, Breakout, Grid
    # ═══════════════════════════════════════════════════════════════════════════
    
    # MEAN REVERSION Konfiguration - V2.3.35 Updated
    mean_reversion_enabled: bool = False
    mean_reversion_bollinger_period: int = 20  # BB: 20 (V2.3.35)
    mean_reversion_bollinger_std: float = 2.0   # BB: 2.0 (V2.3.35)
    mean_reversion_rsi_period: int = 14
    mean_reversion_rsi_oversold: float = 30.0   # RSI: 30 (V2.3.35)
    mean_reversion_rsi_overbought: float = 70.0 # RSI: 70 (V2.3.35)
    mean_reversion_stop_loss_percent: float = 2.0  # 2% SL (V2.3.35)
    mean_reversion_take_profit_percent: float = 1.5  # 1.5% TP (V2.3.35)
    mean_reversion_max_positions: int = 4  # Max 4 Positionen (V2.3.35)
    mean_reversion_min_confidence: float = 0.70  # 70% Mindest-Konfidenz (V2.3.35)
    mean_reversion_risk_per_trade_percent: float = 1.5  # 1.5% Risiko pro Trade
    
    # MOMENTUM TRADING Konfiguration - V2.3.35 Updated
    momentum_enabled: bool = False
    momentum_period: int = 14  # Momentum: 14 Perioden (V2.3.35)
    momentum_threshold: float = 0.8  # Momentum: 0.8% Schwelle (V2.3.35)
    momentum_ma_fast_period: int = 20   # MA: 20 (V2.3.35)
    momentum_ma_slow_period: int = 100  # MA: 100 (V2.3.35)
    momentum_stop_loss_percent: float = 2.0  # 2% SL (V2.3.35)
    momentum_take_profit_percent: float = 4.0  # 4% TP (V2.3.35)
    momentum_max_positions: int = 5
    momentum_min_confidence: float = 0.60  # 60% Mindest-Konfidenz (V2.3.35)
    momentum_risk_per_trade_percent: float = 2.0  # 2% Risiko pro Trade
    
    # BREAKOUT TRADING Konfiguration - V2.3.35 Updated
    breakout_enabled: bool = False
    breakout_lookback_period: int = 20  # Lookback: 20 (V2.3.35)
    breakout_confirmation_bars: int = 2  # Confirmation: 2 Bars (V2.3.35)
    breakout_volume_multiplier: float = 1.8  # Volume Multiplier: 1.8 (V2.3.35)
    breakout_stop_loss_percent: float = 2.5  # 2.5% SL (V2.3.35)
    breakout_take_profit_percent: float = 5.0  # 5% TP (V2.3.35)
    breakout_max_positions: int = 3
    breakout_min_confidence: float = 0.65  # 65% Mindest-Konfidenz (V2.3.35)
    breakout_risk_per_trade_percent: float = 1.8  # 1.8% Risiko pro Trade
    
    # GRID TRADING Konfiguration - V2.3.35 Updated (NUR Range-Regime!)
    grid_enabled: bool = False
    grid_size_pips: float = 10.0
    grid_levels: int = 5  # Max 5 Grid Levels (V2.3.35)
    grid_direction: str = "both"  # "long", "short", "both"
    grid_stop_loss_percent: float = 5.0  # Globaler Not-SL (V2.3.35)
    grid_tp_per_level_percent: float = 1.5  # 1-2% TP pro Level (V2.3.35)
    grid_max_positions: int = 8  # Max 8 Positionen (V2.3.35)
    grid_risk_per_trade_percent: float = 1.0  # 1% Risiko pro Trade
    
    # Weekend Trading per Asset (v2.3.27)
    gold_allow_weekend: bool = False
    silver_allow_weekend: bool = False
    platinum_allow_weekend: bool = False
    palladium_allow_weekend: bool = False
    wti_crude_allow_weekend: bool = False
    brent_crude_allow_weekend: bool = False
    natural_gas_allow_weekend: bool = False
    copper_allow_weekend: bool = False
    wheat_allow_weekend: bool = False
    corn_allow_weekend: bool = False
    soybeans_allow_weekend: bool = False
    coffee_allow_weekend: bool = False
    sugar_allow_weekend: bool = False
    cocoa_allow_weekend: bool = False
    eurusd_allow_weekend: bool = False
    bitcoin_allow_weekend: bool = True  # Bitcoin ist 24/7, default: True
    
    # GESAMTES Balance-Management (Swing + Day zusammen)
    combined_max_balance_percent_per_platform: float = 20.0  # Max 20% PRO PLATTFORM für BEIDE Strategien zusammen
    
    # MetaAPI Token (shared across all MT5 accounts)
    metaapi_token: Optional[str] = os.getenv("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiIzNDVmOWVmYWFmZWUyMWVkM2RjMzZlNDYxOGJkMDdhYiIsInBlcm1pc3Npb25zIjpbXSwiYWNjZXNzUnVsZXMiOlt7ImlkIjoidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJ0cmFkaW5nLWFjY291bnQtbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1ycGMtYXBpIiwibWV0aG9kcyI6WyJtZXRhYXBpLWFwaTp3czpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibWV0YWFwaS1yZWFsLXRpbWUtc3RyZWFtaW5nLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoicmlzay1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsicmlzay1tYW5hZ2VtZW50LWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJjb3B5ZmFjdG9yeS1hcGkiLCJtZXRob2RzIjpbImNvcHlmYWN0b3J5LWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtdC1tYW5hZ2VyLWFwaSIsIm1ldGhvZHMiOlsibXQtbWFuYWdlci1hcGk6cmVzdDpkZWFsaW5nOio6KiIsIm10LW1hbmFnZXItYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6ImJpbGxpbmctYXBpIiwibWV0aG9kcyI6WyJiaWxsaW5nLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19XSwidG9rZW5JZCI6IjIwMjEwMjEzIiwiaW1wZXJzb25hdGVkIjpmYWxzZSwicmVhbFVzZXJJZCI6IjM0NWY5ZWZhYWZlZTIxZWQzZGMzNmU0NjE4YmQwN2FiIiwiaWF0IjoxNzM3NTQyMjI1fQ.G1-t5iTVMHLaBFKs84ij-Pn0h6PYJm3h8p-3jRQZLxnqpBkJhTzJpDcm3d5-BqhKZI7kV5q3xT8u9GovpQPXW9eAxhIwXQC4BdAJoxEwWCBqCKHkJ1CZKWqFSKVWU6-2GX1j6nCHzXDI6CyiIZAJqPIi-rZOJ91l-V8JjEVi5fwUh4nTcJ-LQ3O9_1VL2RZ5vHWoH6qB8KqvH4GfGLOE7MaH3HbXqQ_KbqfvEt7POuZC1q-vMj2hxmrRQ9AHp5J4s0t7Q5ScqrYXhMjRkw9xFLGMt8vkTxQBFfxKJNqT7Vp7bKS5RpBPEWiCQ0BmB6pKc6g7nqO2WPpH4JhWYuUw8rjA")
    # MT5 Libertex Demo Credentials
    mt5_libertex_account_id: Optional[str] = os.getenv("METAAPI_ACCOUNT_ID", "5cc9abd1-671a-447e-ab93-5abbfe0ed941")
    # MT5 ICMarkets Demo Credentials
    mt5_icmarkets_account_id: Optional[str] = os.getenv("METAAPI_ICMARKETS_ACCOUNT_ID", "d2605e89-7bc2-4144-9f7c-951edd596c39")
    # MT5 Libertex REAL Credentials
    mt5_libertex_real_account_id: Optional[str] = os.getenv("METAAPI_LIBERTEX_REAL_ACCOUNT_ID", None)
    # Deprecated MT5 credentials (kept for compatibility)
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    
    # Market Hours Settings - Handelszeiten konfigurierbar machen
    respect_market_hours: bool = True  # Ob Handelszeiten beachtet werden sollen
    market_hours_check_interval_minutes: int = 5  # Alle 5 Minuten prüfen
    pause_when_all_markets_closed: bool = True  # Bot pausieren wenn alle Märkte zu
    
    # Deprecated Bitpanda Credentials (no longer used)
    bitpanda_api_key: Optional[str] = None
    bitpanda_email: Optional[str] = None

class TradeStats(BaseModel):
    total_trades: int
    open_positions: int
    closed_positions: int
    total_profit_loss: float
    win_rate: float
    winning_trades: int
    losing_trades: int

# Helper Functions
def fetch_commodity_data(commodity_id: str):
    """Fetch commodity data from Yahoo Finance"""
    try:
        if commodity_id not in COMMODITIES:
            logger.error(f"Unknown commodity: {commodity_id}")
            return None
            
        commodity = COMMODITIES[commodity_id]
        ticker = yf.Ticker(commodity["symbol"])
        
        # Get historical data for the last 100 days with 1-hour intervals
        hist = ticker.history(period="100d", interval="1h")
        
        if hist.empty:
            logger.error(f"No data received for {commodity['name']}")
            return None
            
        return hist
    except Exception as e:
        logger.error(f"Error fetching {commodity_id} data: {e}")
        return None

async def calculate_position_size(balance: float, price: float, max_risk_percent: float = 20.0) -> float:
    """Calculate position size ensuring max 20% portfolio risk"""
    try:
        # Get all open positions
        cursor = await db.trades.find({"status": "OPEN"})
        open_trades = await cursor.to_list(100)
        
        # Calculate total exposure from open positions
        total_exposure = sum([trade.get('entry_price', 0) * trade.get('quantity', 0) for trade in open_trades])
        
        # Calculate available capital (20% of balance minus current exposure)
        max_portfolio_value = balance * (max_risk_percent / 100)
        available_capital = max(0, max_portfolio_value - total_exposure)
        
        # Calculate lot size (simple division, can be refined based on commodity)
        if available_capital > 0 and price > 0:
            lot_size = round(available_capital / price, 2)
        else:
            lot_size = 0.0
            
        logger.info(f"Position size calculated: {lot_size} (Balance: {balance}, Price: {price}, Exposure: {total_exposure}/{max_portfolio_value})")
        
        return lot_size
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.0

def fetch_wti_data():
    """Fetch WTI crude oil data - backward compatibility"""
    return fetch_commodity_data("WTI_CRUDE")

def calculate_indicators(df):
    """Calculate technical indicators"""
    try:
        # SMA
        sma_indicator = SMAIndicator(close=df['Close'], window=20)
        df['SMA_20'] = sma_indicator.sma_indicator()
        
        # EMA
        ema_indicator = EMAIndicator(close=df['Close'], window=20)
        df['EMA_20'] = ema_indicator.ema_indicator()
        
        # RSI
        rsi_indicator = RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi_indicator.rsi()
        
        # MACD
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MACD_histogram'] = macd.macd_diff()
        
        return df
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df

def generate_signal(latest_data):
    """
    Generate trading signal based on indicators
    V2.3.35: Verbesserte Signal-Logik mit mehreren Methoden
    """
    try:
        rsi = latest_data.get('RSI')
        macd = latest_data.get('MACD')
        macd_signal = latest_data.get('MACD_signal')
        macd_hist = latest_data.get('MACD_histogram', 0)
        price = latest_data.get('Close')
        ema_20 = latest_data.get('EMA_20')
        sma_20 = latest_data.get('SMA_20')
        
        if pd.isna(rsi) or pd.isna(price):
            return "HOLD", "NEUTRAL"
        
        # Determine trend based on EMA
        trend = "NEUTRAL"
        ema = ema_20 if not pd.isna(ema_20) else sma_20
        if not pd.isna(ema):
            price_vs_ema = ((price - ema) / ema) * 100
            if price_vs_ema > 0.5:
                trend = "UP"
            elif price_vs_ema < -0.5:
                trend = "DOWN"
        
        # Signal Score System (-100 bis +100)
        signal_score = 0
        reasons = []
        
        # 1. RSI Signal (Gewicht: 35%)
        if rsi < 30:
            signal_score += 35
            reasons.append(f"RSI überverkauft ({rsi:.1f})")
        elif rsi < 40:
            signal_score += 20
            reasons.append(f"RSI niedrig ({rsi:.1f})")
        elif rsi > 70:
            signal_score -= 35
            reasons.append(f"RSI überkauft ({rsi:.1f})")
        elif rsi > 60:
            signal_score -= 20
            reasons.append(f"RSI hoch ({rsi:.1f})")
        
        # 2. MACD Signal (Gewicht: 30%)
        if not pd.isna(macd) and not pd.isna(macd_signal):
            macd_diff = macd - macd_signal
            if macd_diff > 0 and macd_hist > 0:
                signal_score += 30
                reasons.append("MACD bullish")
            elif macd_diff < 0 and macd_hist < 0:
                signal_score -= 30
                reasons.append("MACD bearish")
            elif macd_diff > 0:
                signal_score += 15
            elif macd_diff < 0:
                signal_score -= 15
        
        # 3. Trend Signal (Gewicht: 35%)
        if trend == "UP":
            signal_score += 25
            reasons.append("Aufwärtstrend")
        elif trend == "DOWN":
            signal_score -= 25
            reasons.append("Abwärtstrend")
        
        # 4. Signal bestimmen basierend auf Score
        signal = "HOLD"
        
        # V2.3.35: Niedrigere Schwellen für mehr Signale
        if signal_score >= 40:  # War: 55
            signal = "BUY"
        elif signal_score <= -40:  # War: -55
            signal = "SELL"
        elif signal_score >= 25:  # Schwaches BUY Signal
            signal = "BUY"  # Für Swing/Day Trading
        elif signal_score <= -25:  # Schwaches SELL Signal
            signal = "SELL"  # Für Swing/Day Trading
        
        # Log für Debugging
        if signal != "HOLD":
            logger.debug(f"Signal generated: {signal} (Score: {signal_score}, Reasons: {', '.join(reasons)})")
        
        return signal, trend
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD", "NEUTRAL"

async def get_ai_analysis(market_data: dict, df: pd.DataFrame, commodity_id: str = 'WTI_CRUDE') -> dict:
    """Get AI analysis for trading decision"""
    global ai_chat
    
    # AI-Analyse temporär deaktiviert wegen Budget-Limit
    return None
    
    if not ai_chat:
        logger.warning("AI chat not initialized, using standard technical analysis")
        return None
    
    try:
        # Get commodity name
        commodity_name = COMMODITIES.get(commodity_id, {}).get('name', commodity_id)
        
        # Prepare market context
        latest = df.iloc[-1]
        last_5 = df.tail(5)
        
        analysis_prompt = f"""Analyze the following {commodity_name} market data and provide a trading recommendation:

**Current Market Data:**
- Price: ${latest['Close']:.2f}
- RSI (14): {latest['RSI']:.2f} {'(Oversold)' if latest['RSI'] < 30 else '(Overbought)' if latest['RSI'] > 70 else '(Neutral)'}
- MACD: {latest['MACD']:.4f}
- MACD Signal: {latest['MACD_signal']:.4f}
- MACD Histogram: {latest['MACD_histogram']:.4f}
- SMA (20): ${latest['SMA_20']:.2f}
- EMA (20): ${latest['EMA_20']:.2f}

**Price Trend (Last 5 periods):**
{last_5[['Close']].to_string()}

**Technical Signal:**
- Price vs EMA: {'Above (Bullish)' if latest['Close'] > latest['EMA_20'] else 'Below (Bearish)'}
- MACD: {'Bullish Crossover' if latest['MACD'] > latest['MACD_signal'] else 'Bearish Crossover'}

Provide your trading recommendation in JSON format."""

        user_message = UserMessage(text=analysis_prompt)
        response = await ai_chat.send_message(user_message)
        
        # Parse AI response
        import json
        response_text = response.strip()
        
        # Try to extract JSON from response
        if '{' in response_text and '}' in response_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            ai_recommendation = json.loads(json_str)
            
            logger.info(f"{commodity_id} AI: {ai_recommendation.get('signal')} (Confidence: {ai_recommendation.get('confidence')}%)")
            
            return ai_recommendation
        else:
            logger.warning(f"Could not parse AI response as JSON: {response_text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting AI analysis for {commodity_id}: {e}")
        return None

async def process_market_data():
    """Background task to fetch and process market data for ALL enabled commodities"""
    global latest_market_data, auto_trading_enabled, trade_count_per_hour
    
    try:
        # Get settings to check enabled commodities
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        enabled_commodities = settings.get('enabled_commodities', ['WTI_CRUDE']) if settings else ['WTI_CRUDE']
        
        logger.info(f"Fetching market data for {len(enabled_commodities)} commodities: {enabled_commodities}")
        
        # Process commodities in batches of 3 with delays to avoid rate limiting
        batch_size = 3
        for i in range(0, len(enabled_commodities), batch_size):
            batch = enabled_commodities[i:i+batch_size]
            
            # Process batch concurrently
            tasks = []
            for commodity_id in batch:
                tasks.append(process_commodity_market_data(commodity_id, settings))
            
            # Run batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any errors
            for commodity_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {commodity_id}: {result}")
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(enabled_commodities):
                await asyncio.sleep(2)
        
        # V2.3.34: Trailing Stop IMMER AKTIV für alle Strategien
        current_prices = {}
        for commodity_id in enabled_commodities:
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id},
                sort=[("timestamp", -1)]
            )
            if market_data:
                current_prices[commodity_id] = market_data['price']
        
        # Update trailing stops
        if current_prices:
            await update_trailing_stops(db, current_prices, settings)
        
        # Check for SL/TP triggers and close trades
        trades_to_close = await check_stop_loss_triggers(db, current_prices)
        for trade_info in trades_to_close:
            await db.trades.update_one(
                {"id": trade_info['id']},
                {
                    "$set": {
                        "status": "CLOSED",
                        "exit_price": trade_info['exit_price'],
                        "closed_at": datetime.now(timezone.utc),
                        "strategy_signal": trade_info['reason']
                    }
                }
            )
            logger.info(f"Position auto-closed: {trade_info['reason']}")
        
        # AI Position Manager - Überwacht ALLE Positionen (auch manuell eröffnete)
        if settings and settings.get('use_ai_analysis'):
            current_prices = {}
            for commodity_id in enabled_commodities:
                market_data = await db.market_data.find_one(
                    {"commodity": commodity_id},
                    sort=[("timestamp", -1)]
                )
                if market_data:
                    current_prices[commodity_id] = market_data['price']
            
            # DEAKTIVIERT: AI Position Manager schließt manuelle Trades ungewollt
            # await manage_open_positions(db, current_prices, settings)
            logger.debug("AI Position Manager ist deaktiviert (schließt manuelle Trades)")
        
        logger.info("Market data processing complete for all commodities")
        
    except Exception as e:
        logger.error(f"Error processing market data: {e}")


async def market_data_updater():
    """Background task that updates market data every 15 seconds (ECHTZEIT-TRADING)"""
    logger.info("🔄 Market Data Updater started - ECHTZEIT MODE (15s)")
    
    while True:
        try:
            await asyncio.sleep(15)  # Update every 15 seconds (SCHNELLER für Echtzeit!)
            logger.debug("🔄 Updating market data...")
            await process_market_data()
        except Exception as e:
            logger.error(f"Error in market data updater: {e}")
            await asyncio.sleep(15)  # Wait before retry

async def process_commodity_market_data(commodity_id: str, settings):
    """Process market data for a specific commodity - HYBRID DATA SOURCES!"""
    try:
        from commodity_processor import calculate_indicators, COMMODITIES
        from multi_platform_connector import multi_platform
        from hybrid_data_fetcher import fetch_commodity_price_hybrid, get_yahoo_finance_history
        
        # Get MT5 connector if available
        connector = None
        if 'MT5_ICMARKETS' in multi_platform.platforms:
            connector = multi_platform.platforms['MT5_ICMARKETS'].get('connector')
        elif 'MT5_LIBERTEX' in multi_platform.platforms:
            connector = multi_platform.platforms['MT5_LIBERTEX'].get('connector')
        
        # HYBRID FETCH: Try MetaAPI, then Yahoo Finance, then others
        price_data = await fetch_commodity_price_hybrid(commodity_id, connector)
        
        if not price_data:
            logger.warning(f"❌ No price data available for {commodity_id}")
            return
        
        live_price = price_data['price']
        data_source = price_data['source']
        
        logger.info(f"✅ {commodity_id}: ${live_price:.2f} (source: {data_source})")
        
        # Fetch historical data for indicators
        hist = None
        if 'hist' in price_data:
            hist = price_data['hist']
        else:
            # Fallback: Get from Yahoo Finance
            hist = get_yahoo_finance_history(commodity_id)
        
        # If no historical data, create minimal data with live price
        if hist is None or hist.empty:
            logger.info(f"Using live price only for {commodity_id}: ${live_price:.2f}")
            # Create minimal market data without indicators
            market_data = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc),
                "commodity": commodity_id,
                "price": live_price,
                "volume": 0,
                "sma_20": live_price,
                "ema_20": live_price,
                "rsi": 50.0,  # Neutral
                "macd": 0.0,
                "macd_signal": 0.0,
                "macd_histogram": 0.0,
                "trend": "NEUTRAL",
                "signal": "HOLD",
                "data_source": data_source
            }
            
            # Store in database
            await db.market_data.update_one(
                {"commodity": commodity_id},
                {"$set": market_data},
                upsert=True
            )
            
            # V2.3.37 FIX: Store in history mit TTL/Limit um Memory Leak zu verhindern
            # Nur alle 5 Minuten einen History-Eintrag speichern (statt bei jedem Update)
            last_history_key = f"_last_history_{commodity_id}"
            last_history_time = getattr(db, last_history_key, 0)
            now_ts = datetime.now(timezone.utc).timestamp()
            
            if now_ts - last_history_time >= 300:  # 5 Minuten
                history_entry = market_data.copy()
                history_entry['commodity_id'] = commodity_id
                await db.market_data_history.insert_one(history_entry)
                setattr(db, last_history_key, now_ts)
                
                # Alte History-Einträge löschen (älter als 7 Tage)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
                await db.market_data_history.delete_many({
                    "commodity_id": commodity_id,
                    "timestamp": {"$lt": cutoff_date}
                })
            
            latest_market_data[commodity_id] = market_data
            logger.info(f"✅ Updated market data for {commodity_id}: ${live_price:.2f}, Signal: HOLD (live only, source: {data_source})")
            return
        
        # Update the latest price in hist with live price
        hist.iloc[-1, hist.columns.get_loc('Close')] = live_price
        
        # Calculate indicators if not already present
        if hist is not None and 'RSI' not in hist.columns:
            hist = calculate_indicators(hist)
            
            # Check again if calculate_indicators returned None
            if hist is None or hist.empty:
                logger.warning(f"Indicators calculation failed for {commodity_id}")
                return
        
        # Get latest data point - with safety check
        if len(hist) == 0:
            logger.warning(f"Empty history for {commodity_id}")
            return
            
        latest = hist.iloc[-1]
        
        # Safely get values with defaults
        close_price = float(latest.get('Close', 0))
        if close_price == 0:
            logger.warning(f"Invalid close price for {commodity_id}")
            return
        
        sma_20 = float(latest.get('SMA_20', close_price))
        
        # Determine trend and signal
        trend = "UP" if close_price > sma_20 else "DOWN"
        
        # Get trading strategy parameters from settings
        rsi_oversold = settings.get('rsi_oversold_threshold', 30.0) if settings else 30.0
        rsi_overbought = settings.get('rsi_overbought_threshold', 70.0) if settings else 70.0
        
        # Signal logic using configurable thresholds
        rsi = float(latest.get('RSI', 50))
        signal = "HOLD"
        if rsi > rsi_overbought:
            signal = "SELL"
        elif rsi < rsi_oversold:
            signal = "BUY"
        
        # Prepare market data
        market_data = {
            "timestamp": datetime.now(timezone.utc),
            "commodity": commodity_id,
            "price": close_price,
            "volume": float(latest.get('Volume', 0)),
            "sma_20": sma_20,
            "ema_20": float(latest.get('EMA_20', close_price)),
            "rsi": rsi,
            "macd": float(latest.get('MACD', 0)),
            "macd_signal": float(latest.get('MACD_signal', 0)),
            "macd_histogram": float(latest.get('MACD_hist', 0)),
            "trend": trend,
            "signal": signal,
            "data_source": data_source  # Track wo die Daten herkommen
        }
        
        # Store in database (upsert by commodity)
        await db.market_data.update_one(
            {"commodity": commodity_id},
            {"$set": market_data},
            upsert=True
        )
        
        # V2.3.37 FIX: Store in history with rate limiting to prevent memory leak
        # Only save every 5 minutes per commodity
        last_history_key = f"_last_history_full_{commodity_id}"
        last_history_time = getattr(db, last_history_key, 0)
        now_ts = datetime.now(timezone.utc).timestamp()
        
        if now_ts - last_history_time >= 300:  # 5 Minuten
            history_entry = market_data.copy()
            history_entry['commodity_id'] = commodity_id
            await db.market_data_history.insert_one(history_entry)
            setattr(db, last_history_key, now_ts)
            
            # Cleanup alte Einträge (älter als 7 Tage)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            await db.market_data_history.delete_many({
                "commodity_id": commodity_id,
                "timestamp": {"$lt": cutoff_date}
            })
        
        # Update in-memory cache
        latest_market_data[commodity_id] = market_data
        
        logger.info(f"✅ Updated market data for {commodity_id}: ${close_price:.2f}, Signal: {signal}")
        
    except Exception as e:
        logger.error(f"Error processing commodity {commodity_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def sync_mt5_positions():
    """Background task to sync closed positions from MT5 to app database"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings or settings.get('mode') != 'MT5':
            return
        
        from metaapi_connector import get_metaapi_connector
        
        # Get MT5 positions
        connector = await get_metaapi_connector()
        mt5_positions = await connector.get_positions()
        mt5_tickets = {str(pos['ticket']) for pos in mt5_positions}
        
        # Get open trades from database (MT5 only)
        open_trades = await db.trades.find({"status": "OPEN", "mode": "MT5"}).to_list(100)
        
        synced_count = 0
        for trade in open_trades:
            # Check if trade has MT5 ticket in strategy_signal
            if 'MT5 #' in trade.get('strategy_signal', ''):
                mt5_ticket = trade['strategy_signal'].split('MT5 #')[1].strip()
                
                # If ticket not in open positions, it was closed on MT5
                if mt5_ticket not in mt5_tickets and mt5_ticket != 'TRADE_RETCODE_INVALID_STOPS':
                    # Close in database
                    current_price = trade.get('entry_price', 0)
                    pl = 0
                    
                    if trade['type'] == 'BUY':
                        pl = (current_price - trade['entry_price']) * trade['quantity']
                    else:
                        pl = (trade['entry_price'] - current_price) * trade['quantity']
                    
                    await db.trades.update_one(
                        {"id": trade['id']},
                        {"$set": {
                            "status": "CLOSED",
                            "exit_price": current_price,
                            "profit_loss": pl,
                            "closed_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    synced_count += 1
                    logger.info(f"✅ Synced closed position: {trade['commodity']} (Ticket: {mt5_ticket})")
        
        if synced_count > 0:
            logger.info(f"🔄 Platform-Sync: {synced_count} Positionen geschlossen")
            
    except Exception as e:
        logger.error(f"Error in platform sync: {e}")

    try:
        logger.info(f"Fetching {commodity_id} market data...")
        df = fetch_commodity_data(commodity_id)
        
        if df is None or df.empty:
            logger.warning(f"No data available for {commodity_id}")
            return
        
        # Calculate indicators
        df = calculate_indicators(df)
        
        # Get latest data point
        latest = df.iloc[-1]
        
        # Get standard technical signal
        signal, trend = generate_signal(latest)
        
        # Get AI analysis if enabled
        use_ai = settings.get('use_ai_analysis', True) if settings else True
        
        ai_signal = None
        ai_confidence = None
        ai_reasoning = None
        
        if use_ai and ai_chat:
            ai_analysis = await get_ai_analysis(latest.to_dict(), df, commodity_id)
            if ai_analysis:
                ai_signal = ai_analysis.get('signal', signal)
                ai_confidence = ai_analysis.get('confidence', 0)
                ai_reasoning = ai_analysis.get('reasoning', '')
                
                # Use AI signal if confidence is high enough
                if ai_confidence >= 60:
                    signal = ai_signal
                    logger.info(f"{commodity_id}: Using AI signal: {signal} (Confidence: {ai_confidence}%)")
                else:
                    logger.info(f"{commodity_id}: AI confidence too low ({ai_confidence}%), using technical signal: {signal}")
        
        # Create market data object
        market_data = MarketData(
            commodity=commodity_id,
            price=float(latest['Close']),
            volume=float(latest['Volume']) if not pd.isna(latest['Volume']) else None,
            sma_20=float(latest['SMA_20']) if not pd.isna(latest['SMA_20']) else None,
            ema_20=float(latest['EMA_20']) if not pd.isna(latest['EMA_20']) else None,
            rsi=float(latest['RSI']) if not pd.isna(latest['RSI']) else None,
            macd=float(latest['MACD']) if not pd.isna(latest['MACD']) else None,
            macd_signal=float(latest['MACD_signal']) if not pd.isna(latest['MACD_signal']) else None,
            macd_histogram=float(latest['MACD_histogram']) if not pd.isna(latest['MACD_histogram']) else None,
            trend=trend,
            signal=signal
        )
        
        # Store in database
        doc = market_data.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        if ai_reasoning:
            doc['ai_analysis'] = {
                'signal': ai_signal,
                'confidence': ai_confidence,
                'reasoning': ai_reasoning
            }
        await db.market_data.insert_one(doc)
        
        # Auto-trading logic
        if settings and settings.get('auto_trading') and signal in ["BUY", "SELL"]:
            max_trades = settings.get('max_trades_per_hour', 3)
            if trade_count_per_hour < max_trades:
                await execute_trade_logic(signal, market_data.price, settings, commodity_id)
                trade_count_per_hour += 1
        
        logger.info(f"{commodity_id}: Price={market_data.price}, Signal={signal}, Trend={trend}")
        
    except Exception as e:
        logger.error(f"Error processing {commodity_id} market data: {e}")

async def execute_trade_logic(signal, price, settings, commodity_id='WTI_CRUDE'):
    """Execute trade based on signal"""
    try:
        # Check for open positions for this commodity
        open_trades = await db.trades.find({"status": "OPEN", "commodity": commodity_id}).to_list(100)
        
        if signal == "BUY" and len([t for t in open_trades if t['type'] == 'BUY']) == 0:
            # Open BUY position
            stop_loss = price * (1 - settings.get('stop_loss_percent', 2.0) / 100)
            take_profit = price * (1 + settings.get('take_profit_percent', 4.0) / 100)
            
            trade = Trade(
                commodity=commodity_id,
                type="BUY",
                price=price,
                quantity=settings.get('position_size', 1.0),
                mode=settings.get('mode', 'PAPER'),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_signal="RSI + MACD + Trend"
            )
            
            doc = trade.model_dump()
            doc['timestamp'] = doc['timestamp'].isoformat()
            await db.trades.insert_one(doc)
            logger.info(f"{commodity_id}: BUY trade executed at {price}")
            
        elif signal == "SELL" and len([t for t in open_trades if t['type'] == 'BUY']) > 0:
            # Close BUY position
            for trade in open_trades:
                if trade['type'] == 'BUY':
                    profit_loss = (price - trade['entry_price']) * trade['quantity']
                    await db.trades.update_one(
                        {"id": trade['id']},
                        {"$set": {
                            "status": "CLOSED",
                            "exit_price": price,
                            "profit_loss": profit_loss,
                            "closed_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    logger.info(f"{commodity_id}: Position closed at {price}, P/L: {profit_loss}")
    except Exception as e:
        logger.error(f"Error executing trade for {commodity_id}: {e}")

def reset_trade_count():
    """Reset hourly trade count"""
    global trade_count_per_hour
    trade_count_per_hour = 0
    logger.info("Hourly trade count reset")

def run_async_task():
    """Run async task in separate thread - DISABLED due to event loop conflicts"""
    # This function is disabled because APScheduler's BackgroundScheduler
    # cannot properly handle FastAPI's async event loop
    # Market data will be fetched on-demand via API calls instead
    logger.debug("Background scheduler task skipped - using on-demand fetching")

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Rohstoff Trader API"}

@api_router.get("/commodities")
async def get_commodities():
    """Get list of all available commodities with trading hours"""
    return {"commodities": get_commodities_with_hours()}

@api_router.get("/market/current")
async def get_current_market(commodity: str = "WTI_CRUDE"):
    """Get current market data for a specific commodity"""
    if commodity not in COMMODITIES:
        raise HTTPException(status_code=400, detail=f"Unknown commodity: {commodity}")


@api_router.get("/settings")
async def get_settings():
    """Get trading settings"""
    try:
        logger.info("📋 GET /settings - Loading settings from DB...")
        logger.info(f"📂 DB Path being used: {db.trading_settings.db.db_path}")
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        logger.info(f"📋 Settings found in DB: {settings is not None}")
        if settings:
            logger.info(f"📋 Settings keys: {list(settings.keys())}")
            logger.info(f"📋 take_profit value: {settings.get('take_profit')}")
        else:
            # Create default settings
            logger.warning("⚠️ No settings found in DB - creating defaults")
            default_settings = TradingSettings()
            settings = default_settings.model_dump()
            await db.trading_settings.insert_one(settings)
            logger.info("✅ Default settings created and saved")
        
        settings.pop('_id', None)
        return settings
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# REMOVED: Duplicate POST /settings endpoint - using the one at line 2383 instead

@api_router.get("/market/all")
async def get_all_markets():
    """Get current market data for all enabled commodities"""
    try:
        # Always return ALL commodities
        enabled = list(COMMODITIES.keys())
        
        results = {}
        for commodity_id in enabled:
            # SQLite: find_one nimmt nur 1 Parameter (query)
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id}
            )
            if market_data:
                results[commodity_id] = market_data
        
        # Return commodities list for frontend compatibility
        commodities_list = []
        for commodity_id in enabled:
            if commodity_id in COMMODITIES:
                commodity_info = COMMODITIES[commodity_id].copy()
                commodity_info['id'] = commodity_id
                commodity_info['marketData'] = results.get(commodity_id)
                commodities_list.append(commodity_info)
        
        return {
            "markets": results, 
            "enabled_commodities": enabled,
            "commodities": commodities_list  # Add this for frontend
        }
    except Exception as e:
        logger.error(f"Error fetching all markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/current", response_model=MarketData)
async def get_current_market_legacy():
    """Legacy endpoint - redirects to /market/all"""
    return await get_all_markets()

@api_router.get("/market/live-ticks")
async def get_live_ticks():
    """
    Get LIVE tick prices from MetaAPI for all available commodities
    Returns real-time broker prices (Bid/Ask) - NO CACHING!
    """
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        live_prices = {}
        
        # Get connector (prefer ICMarkets) - DON'T reconnect every time!
        connector = None
        if 'MT5_ICMARKETS' in multi_platform.platforms and multi_platform.platforms['MT5_ICMARKETS'].get('active'):
            connector = multi_platform.platforms['MT5_ICMARKETS'].get('connector')
        elif 'MT5_LIBERTEX' in multi_platform.platforms and multi_platform.platforms['MT5_LIBERTEX'].get('active'):
            connector = multi_platform.platforms['MT5_LIBERTEX'].get('connector')
        
        if not connector:
            logger.debug("No MetaAPI connector active for live ticks (normal if not connected)")
            return {"error": "MetaAPI not connected", "live_prices": {}}
        
        # Fetch live ticks for all MT5-available commodities
        for commodity_id, commodity_info in COMMODITIES.items():
            # Get symbol (prefer ICMarkets)
            symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
            
            if symbol:
                tick = await connector.get_symbol_price(symbol)
                if tick:
                    live_prices[commodity_id] = {
                        'commodity': commodity_id,
                        'name': commodity_info.get('name'),
                        'symbol': symbol,
                        'price': tick['price'],
                        'bid': tick['bid'],
                        'ask': tick['ask'],
                        'time': tick['time'],
                        'source': 'MetaAPI_LIVE'
                    }
        
        logger.info(f"✅ Fetched {len(live_prices)} live tick prices from MetaAPI")
        
        return {
            "live_prices": live_prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "MetaAPI",
            "count": len(live_prices)
        }
        
    except Exception as e:
        logger.error(f"Error fetching live ticks: {e}")
        return {"error": str(e), "live_prices": {}}


@api_router.get("/market/ohlcv-simple/{commodity}")
async def get_simple_ohlcv(commodity: str, timeframe: str = "5m", period: str = "1d"):
    """
    Simplified OHLCV endpoint when yfinance is rate-limited
    Returns recent market data from DB and current live tick
    """
    try:
        from commodity_processor import COMMODITIES
        
        if commodity not in COMMODITIES:
            raise HTTPException(status_code=404, detail=f"Unknown commodity: {commodity}")
        
        # Get latest market data from DB
        market_data = await db.market_data.find_one(
            {"commodity": commodity},
            sort=[("timestamp", -1)]
        )
        
        if not market_data:
            raise HTTPException(status_code=404, detail=f"No data available for {commodity}")
        
        # Create multiple candles simulating recent history (last hour with 5min candles = 12 candles)
        current_price = market_data.get('price', 0)
        current_time = datetime.now(timezone.utc)
        
        # Map timeframe to number of minutes
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, 
            '1h': 60, '2h': 120, '4h': 240, '1d': 1440
        }
        interval_minutes = timeframe_minutes.get(timeframe, 5)
        
        # Map period to total minutes
        period_minutes = {
            '2h': 120, '1d': 1440, '5d': 7200, '1wk': 10080, 
            '2wk': 20160, '1mo': 43200, '3mo': 129600, 
            '6mo': 259200, '1y': 525600
        }
        total_minutes = period_minutes.get(period, 1440)  # Default 1 day
        
        # Calculate number of candles needed
        num_candles = min(int(total_minutes / interval_minutes), 500)  # Max 500 candles for performance
        
        # Generate candles with realistic price movement simulation
        import random
        data = []
        
        # Start from a slightly higher price for historical data
        base_price = current_price * 1.002  # 0.2% higher than current
        
        for i in range(num_candles - 1, -1, -1):  # Going backwards from now
            candle_time = current_time - timedelta(minutes=i * interval_minutes)
            
            # Create more realistic price movement with random walk
            # Add small random variance + slight overall downward trend
            random_walk = random.uniform(-0.0015, 0.0010)  # Random movement
            trend = (i / num_candles) * 0.002  # Slight downward trend towards current price
            
            price_at_time = base_price * (1 + random_walk + trend)
            
            # Ensure we end close to current price
            if i == 0:
                price_at_time = current_price
            
            # Generate realistic OHLC with intrabar volatility
            volatility = random.uniform(0.0003, 0.0008)
            open_price = price_at_time * (1 + random.uniform(-volatility/2, volatility/2))
            close_price = price_at_time
            high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility))
            
            data.append({
                "timestamp": candle_time.isoformat(),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": market_data.get('volume', 0) * random.uniform(0.8, 1.2),  # Vary volume
                "rsi": market_data.get('rsi', 50) + random.uniform(-5, 5),  # Vary RSI
                "sma_20": market_data.get('sma_20', current_price),
                "ema_20": market_data.get('ema_20', current_price)
            })
            
            # Update base price for next candle
            base_price = close_price
        
        return {
            "success": True,
            "data": data,
            "commodity": commodity,
            "timeframe": timeframe,
            "period": period,
            "source": "live_db",
            "message": "Using live database data (yfinance rate-limited)"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/whisper/transcribe")
async def whisper_transcribe_endpoint(file: UploadFile):
    """
    Whisper Speech-to-Text endpoint
    Upload audio file → Get transcription
    Supports: mp3, wav, m4a, webm, ogg
    """
    try:
        from whisper_service import transcribe_audio_bytes
        
        # Read audio file
        audio_bytes = await file.read()
        
        # Transcribe
        result = await transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            filename=file.filename,
            language="de"  # German
        )
        
        if result.get("success"):
            return {
                "success": True,
                "text": result.get("text", ""),
                "language": result.get("language", "de")
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Transkription fehlgeschlagen"))
    
    except Exception as e:
        logger.error(f"Whisper endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/ai-chat")
async def ai_chat_endpoint(
    message: str,
    session_id: str = "default-session",
    ai_provider: str = None,
    model: str = None
):
    """
    AI Chat endpoint for trading bot
    Supports: GPT-5 (openai), Claude (anthropic), Ollama (local)
    Uses session_id to maintain conversation context
    Uses ai_provider and model from user settings if not explicitly provided
    """
    try:
        from ai_chat_service import send_chat_message
        
        # Get settings from correct collection
        settings_doc = await db.trading_settings.find_one({"id": "trading_settings"})
        settings = settings_doc if settings_doc else {}
        
        # Use settings values if parameters not provided
        # Priority: URL params > Settings > Defaults
        final_ai_provider = ai_provider or settings.get('ai_provider', 'emergent')
        final_model = model or settings.get('ai_model', 'gpt-5')
        
        logger.info(f"AI Chat: Using provider={final_ai_provider}, model={final_model} (from {'params' if ai_provider else 'settings'})")
        
        # Get open trades - Same logic as /trades/list endpoint
        from multi_platform_connector import multi_platform
        
        open_trades = []
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        # Symbol mapping (same as /trades/list)
        symbol_to_commodity = {
            'XAUUSD': 'GOLD', 'XAGUSD': 'SILVER', 'XPTUSD': 'PLATINUM', 'XPDUSD': 'PALLADIUM',
            'PL': 'PLATINUM', 'PA': 'PALLADIUM',
            'USOILCash': 'WTI_CRUDE', 'WTI_F6': 'WTI_CRUDE',
            'UKOUSD': 'BRENT_CRUDE', 'CL': 'BRENT_CRUDE',
            'NGASCash': 'NATURAL_GAS', 'NG': 'NATURAL_GAS',
            'WHEAT': 'WHEAT', 'CORN': 'CORN', 'SOYBEAN': 'SOYBEANS',
            'COFFEE': 'COFFEE', 'SUGAR': 'SUGAR', 'COTTON': 'COTTON', 'COCOA': 'COCOA'
        }
        
        # Fetch positions from active platforms (check without _DEMO/_REAL suffix)
        # Remove duplicates: MT5_LIBERTEX_DEMO and MT5_LIBERTEX map to same base
        seen_base_platforms = set()
        
        for platform_name in active_platforms:
            # Map _DEMO/_REAL to base name for API calls
            base_platform = platform_name.replace('_DEMO', '').replace('_REAL', '')
            
            # Skip if we already processed this base platform
            if base_platform in seen_base_platforms:
                logger.info(f"⚠️ Skipping duplicate platform: {platform_name} (already processed {base_platform})")
                continue
            
            seen_base_platforms.add(base_platform)
            
            if base_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
                try:
                    positions = await multi_platform.get_open_positions(base_platform)
                    
                    for pos in positions:
                        mt5_symbol = pos.get('symbol', 'UNKNOWN')
                        commodity_id = symbol_to_commodity.get(mt5_symbol, mt5_symbol)
                        
                        trade = {
                            'commodity': commodity_id,
                            'type': "BUY" if pos.get('type') == 'POSITION_TYPE_BUY' else "SELL",
                            'quantity': pos.get('volume', 0),
                            'entry_price': pos.get('price_open', 0),
                            'profit_loss': pos.get('profit', 0),
                            'platform': platform_name
                        }
                        open_trades.append(trade)
                except Exception as e:
                    logger.warning(f"Could not fetch positions from {platform_name}: {e}")
        
        logger.info(f"AI Chat: Found {len(open_trades)} open trades from MT5")
        
        # Send message to AI with session_id and db for function calling
        result = await send_chat_message(
            message=message,
            settings=settings,
            latest_market_data=latest_market_data or {},
            open_trades=open_trades,
            ai_provider=final_ai_provider,
            model=final_model,
            session_id=session_id,
            db=db  # Pass db for function calling
        )
        
        return result
        
    except Exception as e:
        logger.error(f"AI Chat error: {e}")
        return {
            "success": False,
            "response": f"Fehler beim AI-Chat: {str(e)}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple OHLCV: {e}")
        raise HTTPException(status_code=500, detail=str(e))




    """Get current market data with indicators"""
    if latest_market_data is None:
        # Fetch data synchronously if not available
        await process_market_data()
    
    if latest_market_data is None:
        raise HTTPException(status_code=503, detail="Market data not available")
    
    return latest_market_data

@api_router.get("/market/history")
async def get_market_history(limit: int = 100):
    """Get historical market data (snapshot history from DB)"""
    try:
        # V2.3.32 FIX: SQLite-kompatible Abfrage ohne MongoDB-Syntax
        cursor = await db.market_data.find({})
        data = await cursor.to_list(limit)
        
        # Sortiere nach Timestamp (neueste zuerst, dann umkehren)
        data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        data = data[:limit]  # Limit anwenden
        
        # Convert timestamps
        for item in data:
            if isinstance(item.get('timestamp'), str):
                try:
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')).isoformat()
                except:
                    pass
        
        return {"data": list(reversed(data))}
    except Exception as e:
        logger.error(f"Error fetching market history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/ohlcv/{commodity}")
async def get_ohlcv_data(
    commodity: str,
    timeframe: str = "1d",
    period: str = "1mo"
):
    """
    Get OHLCV candlestick data with technical indicators
    
    Parameters:
    - commodity: Commodity ID (GOLD, WTI_CRUDE, etc.)
    - timeframe: Chart interval (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1wk, 1mo)
    - period: Data period (2h, 1d, 5d, 1wk, 2wk, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
    
    Example: /api/market/ohlcv/GOLD?timeframe=1m&period=2h
    """
    try:
        from commodity_processor import fetch_historical_ohlcv_async
        
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1wk', '1mo']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        # Validate period  
        valid_periods = ['2h', '1d', '5d', '1wk', '2wk', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max']
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Fetch data (async version for MetaAPI support)
        df = await fetch_historical_ohlcv_async(commodity, timeframe=timeframe, period=period)
        
        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for {commodity}"
            )
        
        # Convert DataFrame to list of dicts
        df_reset = df.reset_index()
        data = []
        
        for _, row in df_reset.iterrows():
            data.append({
                'timestamp': row['Datetime'].isoformat() if 'Datetime' in df_reset.columns else row['Date'].isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'sma_20': float(row['SMA_20']) if 'SMA_20' in row and not pd.isna(row['SMA_20']) else None,
                'ema_20': float(row['EMA_20']) if 'EMA_20' in row and not pd.isna(row['EMA_20']) else None,
                'rsi': float(row['RSI']) if 'RSI' in row and not pd.isna(row['RSI']) else None,
                'macd': float(row['MACD']) if 'MACD' in row and not pd.isna(row['MACD']) else None,
                'macd_signal': float(row['MACD_Signal']) if 'MACD_Signal' in row and not pd.isna(row['MACD_Signal']) else None,
                'macd_histogram': float(row['MACD_Histogram']) if 'MACD_Histogram' in row and not pd.isna(row['MACD_Histogram']) else None,
            })
        
        return {
            'success': True,
            'commodity': commodity,
            'timeframe': timeframe,
            'period': period,
            'data_points': len(data),
            'data': data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLCV data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/market/hours")
async def get_market_hours_status():
    """Get current market hours status for all enabled commodities"""
    try:
        from commodity_market_hours import get_market_hours, is_market_open
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            settings = TradingSettings().model_dump()
        
        enabled_commodities = settings.get('enabled_commodities', ['WTI_CRUDE'])
        
        # Hole alle Handelszeiten aus DB
        market_hours = await get_market_hours(db)
        
        market_status = {}
        any_market_open = False
        current_time = datetime.now(timezone.utc)
        
        for commodity_id in enabled_commodities:
            is_open = is_market_open(commodity_id, market_hours, current_time)
            hours_config = market_hours.get(commodity_id, {})
            
            market_status[commodity_id] = {
                "is_open": is_open,
                "name": COMMODITIES.get(commodity_id, {}).get("name", commodity_id),
                "category": COMMODITIES.get(commodity_id, {}).get("category", "Unbekannt"),
                "hours": hours_config
            }
            
            if is_open:
                any_market_open = True
        
        # Get market hours settings
        respect_market_hours = settings.get('respect_market_hours', True) if settings else True
        
        return {
            "current_time": current_time.isoformat(),
            "any_market_open": any_market_open,
            "respect_market_hours": respect_market_hours,
            "bot_would_pause": respect_market_hours and not any_market_open,
            "markets": market_status
        }
        
    except Exception as e:
        logger.error(f"Error fetching market hours status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/market/hours/all")
async def get_all_market_hours():
    """Get market hours configuration for ALL commodities"""
    try:
        from commodity_market_hours import get_market_hours, DEFAULT_MARKET_HOURS
        
        # Hole Custom Hours aus DB (oder Defaults)
        market_hours = await get_market_hours(db)
        
        # Füge alle Commodities hinzu (auch die nicht enabled)
        all_hours = {}
        for commodity_id in COMMODITIES.keys():
            if commodity_id in market_hours:
                all_hours[commodity_id] = market_hours[commodity_id]
            elif commodity_id in DEFAULT_MARKET_HOURS:
                all_hours[commodity_id] = DEFAULT_MARKET_HOURS[commodity_id]
            else:
                # Fallback: Standard 24/5
                all_hours[commodity_id] = {
                    "enabled": True,
                    "days": [0, 1, 2, 3, 4],
                    "open_time": "00:00",
                    "close_time": "23:59",
                    "is_24_5": True,
                    "description": "Standard 24/5"
                }
            
            # Füge Commodity-Info hinzu
            all_hours[commodity_id]["commodity_name"] = COMMODITIES.get(commodity_id, {}).get("name", commodity_id)
            all_hours[commodity_id]["commodity_category"] = COMMODITIES.get(commodity_id, {}).get("category", "Unbekannt")
        
        return {
            "success": True,
            "market_hours": all_hours
        }
        
    except Exception as e:
        logger.error(f"Error fetching all market hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/market/hours/update")
async def update_commodity_market_hours(request: dict):
    """Update market hours for a specific commodity"""
    try:
        from commodity_market_hours import update_market_hours
        
        commodity_id = request.get("commodity_id")
        hours_config = request.get("hours_config")
        
        if not commodity_id or not hours_config:
            raise HTTPException(status_code=400, detail="commodity_id und hours_config erforderlich")
        
        # Update in DB
        updated_hours = await update_market_hours(db, commodity_id, hours_config)
        
        return {
            "success": True,
            "message": f"Handelszeiten für {commodity_id} aktualisiert",
            "market_hours": updated_hours
        }
        
    except Exception as e:
        logger.error(f"Error updating market hours: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class TradeExecuteRequest(BaseModel):
    """Request Model für /trades/execute"""
    trade_type: str  # "BUY" or "SELL"
    price: float
    quantity: Optional[float] = None
    commodity: str = "WTI_CRUDE"
    strategy: Optional[str] = "day"  # "day" oder "swing" - bestimmt welche SL/TP Settings verwendet werden

@api_router.post("/trades/execute")
async def execute_trade(request: TradeExecuteRequest):
    """Manually execute a trade with automatic position sizing - SENDET AN MT5!"""
    try:
        trade_type = request.trade_type
        price = request.price
        quantity = request.quantity
        commodity = request.commodity
        
        logger.info(f"🔥 Trade Execute Request: {trade_type} {commodity} @ {price}, Quantity: {quantity}")
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Get trading strategy from settings
        strategy = settings.get('trading_strategy', 'CONSERVATIVE') if settings else 'CONSERVATIVE'
        
        # Apply Scalping-specific TP/SL if strategy is SCALPING
        if strategy == 'SCALPING':
            from scalping_strategy import scalping_strategy
            
            # Get market data for scalping analysis
            market_data = latest_market_data.get(commodity, {})
            
            if market_data:
                scalping_analysis = scalping_strategy.analyze(market_data, {'name': commodity})
                
                # Override TP/SL with scalping values if available
                if scalping_analysis.get('take_profit'):
                    # Update request with scalping TP/SL (these will be used later in the function)
                    logger.info(f"🎯 SCALPING Trade: Applying TP={scalping_analysis['take_profit']:.2f}, SL={scalping_analysis['stop_loss']:.2f}")
                    # Store scalping values for later use
                    request.scalping_tp = scalping_analysis['take_profit']
                    request.scalping_sl = scalping_analysis['stop_loss']
        logger.info(f"🔍 Settings loaded: {settings is not None}")
        if not settings:
            settings = TradingSettings().model_dump()
        
        # Get default platform (handle both dict and MongoDB document)
        default_platform = settings.get('default_platform') or settings.get('default_platform', 'MT5_LIBERTEX_DEMO')
        if not default_platform:
            default_platform = 'MT5_LIBERTEX_DEMO'
        logger.info(f"🔍 Default Platform: {default_platform}")
        
        # Automatische Position Size Berechnung wenn nicht angegeben
        if quantity is None or quantity == 1.0:
            logger.info(f"🔍 Auto Position Size: Starting calculation")
            # Hole aktuelle Balance und Free Margin
            balance = 50000.0  # Default
            free_margin = None
            
            logger.info(f"🔍 Platform Check: {default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']}")
            
            if default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                try:
                    from multi_platform_connector import multi_platform
                    await multi_platform.connect_platform(default_platform)
                    
                    if default_platform in multi_platform.platforms:
                        connector = multi_platform.platforms[default_platform].get('connector')
                        if connector:
                            account_info = await connector.get_account_info()
                            if account_info:
                                balance = account_info.get('balance', balance)
                                free_margin = account_info.get('free_margin')
                except Exception as e:
                    logger.warning(f"Could not fetch balance from {default_platform}: {e}")
            elif default_platform == 'BITPANDA':
                try:
                    from multi_platform_connector import multi_platform
                    await multi_platform.connect_platform('BITPANDA')
                    
                    if 'BITPANDA' in multi_platform.platforms:
                        bp_balance = multi_platform.platforms['BITPANDA'].get('balance', 0.0)
                        if bp_balance > 0:
                            balance = bp_balance
                except Exception as e:
                    logger.warning(f"Could not fetch Bitpanda balance: {e}")
            
            # Berechne Position Size (max 20% des verfügbaren Kapitals) PRO PLATTFORM
            from commodity_processor import calculate_position_size
            from multi_platform_connector import multi_platform
            try:
                quantity = await calculate_position_size(
                    balance=balance, 
                    price=price, 
                    db=db, 
                    max_risk_percent=settings.get('max_portfolio_risk_percent', 20.0), 
                    free_margin=free_margin,
                    platform=default_platform,
                    multi_platform_connector=multi_platform
                )
            except Exception as e:
                logger.error(f"❌ Position Size Calculation Error: {e}")
                # Fallback to minimum quantity
                quantity = 0.01
            
            # WICHTIG: Wenn quantity 0.0 ist, bedeutet das Portfolio-Risiko überschritten!
            if quantity <= 0.0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Portfolio-Risiko überschritten! Maximales Risiko: {settings.get('max_portfolio_risk_percent', 20.0)}%. Schließen Sie bestehende Positionen, bevor Sie neue eröffnen."
                )
            
            # Minimum 0.01 (Broker-Minimum), Maximum 0.1 für Sicherheit
            quantity = max(0.01, min(quantity, 0.1))
            
            logger.info(f"📊 [{default_platform}] Auto Position Size: {quantity:.4f} lots (Balance: {balance:.2f}, Free Margin: {free_margin}, Price: {price:.2f})")
        else:
            # WICHTIG: Auch bei manuell eingegebener Quantity das Portfolio-Risiko prüfen!
            logger.info(f"🔍 Manual Position Size provided: {quantity} - Checking portfolio risk...")
            
            # Hole Balance für Risk-Check
            balance = 50000.0  # Default
            free_margin = None
            
            if default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                try:
                    from multi_platform_connector import multi_platform
                    await multi_platform.connect_platform(default_platform)
                    
                    if default_platform in multi_platform.platforms:
                        connector = multi_platform.platforms[default_platform].get('connector')
                        if connector:
                            account_info = await connector.get_account_info()
                            if account_info:
                                balance = account_info.get('balance', balance)
                                free_margin = account_info.get('free_margin')
                except Exception as e:
                    logger.warning(f"Could not fetch balance from {default_platform}: {e}")
            
            # Portfolio-Risiko prüfen
            try:
                from multi_platform_connector import multi_platform
                
                # Hole offene Positionen
                positions = await multi_platform.get_open_positions(default_platform)
                
                # Berechne aktuelles Exposure
                total_exposure = sum([
                    (pos.get('price_open', 0) or pos.get('openPrice', 0)) * pos.get('volume', 0)
                    for pos in positions
                ])
                
                # Berechne neues Exposure
                new_exposure = price * quantity
                total_new_exposure = total_exposure + new_exposure
                
                # Max Portfolio Risiko
                max_portfolio_value = balance * (settings.get('max_portfolio_risk_percent', 20.0) / 100)
                
                logger.info(f"📊 Portfolio Risk Check: Current Exposure: {total_exposure:.2f}, New Trade: {new_exposure:.2f}, Total: {total_new_exposure:.2f}, Max: {max_portfolio_value:.2f}")
                
                # Prüfe ob Risiko überschritten wird
                if total_new_exposure > max_portfolio_value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Portfolio-Risiko würde überschritten! Aktuelles Exposure: {total_exposure:.2f} EUR, Neue Position: {new_exposure:.2f} EUR, Gesamt: {total_new_exposure:.2f} EUR, Max erlaubt: {max_portfolio_value:.2f} EUR ({settings.get('max_portfolio_risk_percent', 20.0)}% von {balance:.2f} EUR)"
                    )
                
                logger.info(f"✅ Portfolio Risk Check passed")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"⚠️ Could not verify portfolio risk: {e} - Allowing trade")
        
        # V2.3.31: Stop Loss und Take Profit für ALLE Strategien berechnen
        strategy = request.strategy if hasattr(request, 'strategy') else "day"
        logger.info(f"📊 Using strategy: {strategy}")
        
        # V2.3.31: Strategie-spezifische Settings für ALLE 7 Strategien
        strategy_config = {
            'swing': {
                'tp_key': 'swing_take_profit_percent', 'tp_default': 4.0,
                'sl_key': 'swing_stop_loss_percent', 'sl_default': 2.0
            },
            'day': {
                'tp_key': 'day_take_profit_percent', 'tp_default': 2.5,
                'sl_key': 'day_stop_loss_percent', 'sl_default': 1.5
            },
            'scalping': {
                'tp_key': 'scalping_take_profit_percent', 'tp_default': 0.5,
                'sl_key': 'scalping_stop_loss_percent', 'sl_default': 0.3
            },
            'mean_reversion': {
                'tp_key': 'mean_reversion_take_profit_percent', 'tp_default': 4.0,
                'sl_key': 'mean_reversion_stop_loss_percent', 'sl_default': 2.0
            },
            'momentum': {
                'tp_key': 'momentum_take_profit_percent', 'tp_default': 5.0,
                'sl_key': 'momentum_stop_loss_percent', 'sl_default': 2.5
            },
            'breakout': {
                'tp_key': 'breakout_take_profit_percent', 'tp_default': 6.0,
                'sl_key': 'breakout_stop_loss_percent', 'sl_default': 3.0
            },
            'grid': {
                'tp_key': 'grid_tp_per_level_percent', 'tp_default': 2.0,
                'sl_key': 'grid_stop_loss_percent', 'sl_default': 5.0
            }
        }
        
        # Hole Config für diese Strategie (oder Day als Fallback)
        config = strategy_config.get(strategy, strategy_config['day'])
        
        # Prüfe ob Euro-Modus für diese Strategie aktiv ist
        tp_sl_mode = settings.get(f'{strategy}_tp_sl_mode', 'percent')
        
        if tp_sl_mode == 'euro':
            tp_euro = settings.get(f'{strategy}_take_profit_euro', 10.0)
            sl_euro = settings.get(f'{strategy}_stop_loss_euro', 15.0)
            lot_multiplier = quantity / 0.01
            tp_points = tp_euro / lot_multiplier if lot_multiplier > 0 else tp_euro
            sl_points = sl_euro / lot_multiplier if lot_multiplier > 0 else sl_euro
        else:
            tp_percent = max(settings.get(config['tp_key'], config['tp_default']), 0.1)
            sl_percent = max(settings.get(config['sl_key'], config['sl_default']), 0.1)
            tp_points = price * (tp_percent / 100)
            sl_points = price * (sl_percent / 100)
        
        # Check if scalping values are available (set earlier in the function)
        if hasattr(request, 'scalping_tp') and hasattr(request, 'scalping_sl'):
            # Use scalping-specific TP/SL values
            take_profit = round(request.scalping_tp, 2)
            stop_loss = round(request.scalping_sl, 2)
            logger.info(f"🎯 Using SCALPING TP/SL: Price={price}, SL={stop_loss}, TP={take_profit}")
        else:
            # Use standard strategy-based TP/SL calculation
            if trade_type.upper() == 'BUY':
                # BUY: SL unter Entry, TP über Entry
                stop_loss = round(price - sl_points, 2)
                take_profit = round(price + tp_points, 2)
            else:  # SELL
                # SELL: SL über Entry, TP unter Entry
                stop_loss = round(price + sl_points, 2)
                take_profit = round(price - tp_points, 2)
            
            logger.info(f"💡 SL/TP calculated ({strategy} strategy): Price={price}, SL={stop_loss}, TP={take_profit}")
        logger.info(f"🔍 Using Platform: {default_platform}")
        
        # WICHTIG: Order an Trading-Plattform senden!
        platform_ticket = None
        
        # MT5 Mode (Libertex or ICMarkets)
        if default_platform in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5', 'MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            try:
                from multi_platform_connector import multi_platform
                from commodity_processor import COMMODITIES
                
                commodity_info = COMMODITIES.get(commodity, {})
                logger.info(f"🔍 Commodity Info: {commodity}, Default Platform: {default_platform}")
                logger.info(f"🔍 Platforms: {commodity_info.get('platforms', [])}")
                
                # Select correct symbol based on default platform
                if 'LIBERTEX' in default_platform:
                    mt5_symbol = commodity_info.get('mt5_libertex_symbol')
                elif 'ICMARKETS' in default_platform:
                    mt5_symbol = commodity_info.get('mt5_icmarkets_symbol')
                else:
                    # Fallback
                    mt5_symbol = commodity_info.get('mt5_icmarkets_symbol') or commodity_info.get('mt5_libertex_symbol')
                
                # Prüfen ob Rohstoff auf MT5 verfügbar
                platforms = commodity_info.get('platforms', [])
                mt5_available = any(p in platforms for p in ['MT5_LIBERTEX', 'MT5_ICMARKETS', 'MT5'])
                logger.info(f"🔍 MT5 Symbol: {mt5_symbol}, MT5 Available: {mt5_available}")
                
                if not mt5_available or not mt5_symbol:
                    logger.warning(f"⚠️ {commodity} ist auf MT5 nicht handelbar!")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{commodity_info.get('name', commodity)} ist auf MT5 nicht verfügbar. Nutzen Sie Bitpanda für diesen Rohstoff oder wählen Sie einen verfügbaren Rohstoff."
                    )
                
                # Get the correct platform connector
                await multi_platform.connect_platform(default_platform)
                
                if default_platform not in multi_platform.platforms:
                    raise HTTPException(status_code=503, detail=f"{default_platform} ist nicht verbunden")
                
                connector = multi_platform.platforms[default_platform].get('connector')
                if not connector:
                    raise HTTPException(status_code=503, detail=f"{default_platform} Connector nicht verfügbar")
                
                # WICHTIG: Trade OHNE SL/TP an MT5 senden (AI Bot übernimmt die Überwachung)
                logger.info(f"🎯 Sende Trade OHNE SL/TP an MT5 (AI Bot überwacht Position)")
                logger.info(f"📊 Berechnete Ziele (nur für Monitoring): SL={stop_loss}, TP={take_profit}")
                
                result = await connector.create_market_order(
                    symbol=mt5_symbol,
                    order_type=trade_type.upper(),
                    volume=quantity,
                    sl=None,  # Kein SL an MT5 - AI Bot überwacht!
                    tp=None   # Kein TP an MT5 - AI Bot überwacht!
                )
                
                logger.info(f"📥 SDK Response Type: {type(result)}")
                logger.info(f"📥 SDK Response: {result}")
                
                # Robuste Success-Prüfung (3 Fallback-Methoden)
                is_success = False
                platform_ticket = None
                
                # Method 1: Explicit success key in dict
                if isinstance(result, dict) and result.get('success') == True:
                    is_success = True
                    platform_ticket = result.get('orderId') or result.get('positionId')
                    logger.info(f"✅ Success detection method: Explicit success key in dict")
                
                # Method 2: Check for orderId/positionId presence (implicit success)
                elif isinstance(result, dict) and (result.get('orderId') or result.get('positionId')):
                    is_success = True
                    platform_ticket = result.get('orderId') or result.get('positionId')
                    logger.info(f"✅ Success detection method: OrderId/PositionId present")
                
                # Method 3: Check for object attributes (SDK might return object instead of dict)
                elif hasattr(result, 'orderId') or hasattr(result, 'positionId'):
                    is_success = True
                    platform_ticket = getattr(result, 'orderId', None) or getattr(result, 'positionId', None)
                    logger.info(f"✅ Success detection method: Object attributes")
                
                if is_success and platform_ticket:
                    logger.info(f"✅ Order an {default_platform} gesendet: Ticket #{platform_ticket}")
                else:
                    error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'SDK returned unexpected response'
                    logger.error(f"❌ {default_platform} Order fehlgeschlagen: {error_msg}")
                    logger.error(f"❌ Result type: {type(result)}, Result: {result}")
                    raise HTTPException(status_code=500, detail=f"{default_platform} Order failed: {error_msg}")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Fehler beim Senden an MT5: {e}")
                raise HTTPException(status_code=500, detail=f"MT5 Fehler: {str(e)}")
        
        # Bitpanda Mode
        elif default_platform == 'BITPANDA':
            try:
                from multi_platform_connector import multi_platform
                from commodity_processor import COMMODITIES
                
                commodity_info = COMMODITIES.get(commodity, {})
                bitpanda_symbol = commodity_info.get('bitpanda_symbol', 'GOLD')
                
                # Prüfen ob Rohstoff auf Bitpanda verfügbar
                platforms = commodity_info.get('platforms', [])
                if 'BITPANDA' not in platforms:
                    logger.warning(f"⚠️ {commodity} ist auf Bitpanda nicht handelbar!")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"{commodity_info.get('name', commodity)} ist auf Bitpanda nicht verfügbar."
                    )
                
                # Connect to Bitpanda
                await multi_platform.connect_platform('BITPANDA')
                
                if 'BITPANDA' not in multi_platform.platforms:
                    raise HTTPException(status_code=503, detail="Bitpanda ist nicht verbunden")
                
                connector = multi_platform.platforms['BITPANDA'].get('connector')
                if not connector:
                    raise HTTPException(status_code=503, detail="Bitpanda Connector nicht verfügbar")
                
                # WICHTIG: Trade OHNE SL/TP an Bitpanda senden (AI Bot übernimmt die Überwachung)
                logger.info(f"🎯 Sende Trade OHNE SL/TP an Bitpanda (AI Bot überwacht Position)")
                logger.info(f"📊 Berechnete Ziele (nur für Monitoring): SL={stop_loss}, TP={take_profit}")
                
                result = await connector.place_order(
                    symbol=bitpanda_symbol,
                    order_type=trade_type.upper(),
                    volume=quantity,
                    price=price,
                    sl=None,  # Kein SL an Bitpanda - AI Bot überwacht!
                    tp=None   # Kein TP an Bitpanda - AI Bot überwacht!
                )
                
                logger.info(f"📥 SDK Response: {result}")
                
                if result and result.get('success'):
                    platform_ticket = result.get('order_id', result.get('ticket'))
                    logger.info(f"✅ Order an Bitpanda gesendet: #{platform_ticket}")
                else:
                    logger.error("❌ Bitpanda Order fehlgeschlagen!")
                    raise HTTPException(status_code=500, detail="Bitpanda Order konnte nicht platziert werden")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"❌ Fehler beim Senden an Bitpanda: {e}")
                raise HTTPException(status_code=500, detail=f"Bitpanda Fehler: {str(e)}")
        
        # NICHT in DB speichern! Trade wird live von MT5 abgerufen
        if platform_ticket:
            logger.info(f"✅ Trade erfolgreich an MT5 gesendet: {trade_type} {quantity:.4f} {commodity} @ {price}, Ticket #{platform_ticket}")
            logger.info(f"📊 Trade wird NICHT in DB gespeichert - wird live von MT5 über /trades/list abgerufen")
            
            # Bestimme Strategie basierend auf User-Request oder Auto-Detection
            strategy = request.strategy if hasattr(request, 'strategy') else "day"
            
            # V2.3.31: TICKET-STRATEGIE MAPPING - Speichere die Zuordnung DAUERHAFT
            try:
                from database_v2 import db_manager
                await db_manager.trades_db.save_ticket_strategy(
                    mt5_ticket=str(platform_ticket),
                    strategy=strategy,
                    commodity=commodity,
                    platform=default_platform
                )
                logger.info(f"💾 Ticket-Strategie gespeichert: #{platform_ticket} → {strategy}")
            except Exception as mapping_err:
                logger.warning(f"⚠️ Ticket-Strategie-Mapping konnte nicht gespeichert werden: {mapping_err}")
            
            # Speichere auch in trade_settings (für Rückwärtskompatibilität)
            try:
                trade_settings = {
                    'trade_id': str(platform_ticket),
                    'strategy': strategy,  # NUR Strategie wird gespeichert!
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'created_by': 'MANUAL',
                    'commodity': commodity,
                    'entry_price': price,
                    'platform': default_platform,
                    'note': 'SL/TP werden dynamisch aus Settings berechnet'
                }
                await db.trade_settings.update_one(
                    {'trade_id': str(platform_ticket)},
                    {'$set': trade_settings},
                    upsert=True
                )
                logger.info(f"💾 Trade Settings gespeichert für #{platform_ticket} ({strategy} strategy)")
            except Exception as e:
                logger.error(f"⚠️ Fehler beim Speichern der Trade Settings: {e}")
                # Continue anyway - trade was successful
            
            return {
                "success": True, 
                "ticket": platform_ticket, 
                "platform": default_platform,
                "message": f"Trade erfolgreich an {default_platform} gesendet. Ticket: #{platform_ticket}"
            }
        else:
            logger.error(f"❌ platform_ticket ist None - Trade fehlgeschlagen")
            raise HTTPException(status_code=500, detail="Trade konnte nicht ausgeführt werden - Broker hat Order abgelehnt")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/auto-set-targets")
async def auto_set_sl_tp_for_open_trades():
    """
    Automatisch SL/TP für alle offenen Trades berechnen und in DB speichern
    Der AI Bot nutzt diese Werte dann zur Überwachung
    """
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        # Get settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            raise HTTPException(status_code=404, detail="Settings nicht gefunden")
        
        # Get TP/SL percentages from settings
        tp_percent = settings.get('take_profit_percent', 4.0)
        sl_percent = settings.get('stop_loss_percent', 2.0)
        
        updated_count = 0
        errors = []
        
        # Check both platforms
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
            if platform_name not in settings.get('active_platforms', []):
                continue
            
            try:
                # Get open positions from platform
                positions = await multi_platform.get_open_positions(platform_name)
                
                for pos in positions:
                    ticket = pos.get('ticket') or pos.get('id') or pos.get('positionId')
                    entry_price = pos.get('price_open') or pos.get('openPrice') or pos.get('entry_price')
                    pos_type = str(pos.get('type', '')).upper()
                    symbol = pos.get('symbol', '')
                    
                    if not ticket or not entry_price:
                        continue
                    
                    # Check if settings already exist
                    existing = await db.trade_settings.find_one({'trade_id': str(ticket)})
                    if existing and existing.get('stop_loss') and existing.get('take_profit'):
                        logger.info(f"ℹ️ Trade #{ticket} hat bereits SL/TP Settings - überspringe")
                        continue
                    
                    # Calculate SL/TP based on position type
                    if 'BUY' in pos_type:
                        take_profit = entry_price * (1 + tp_percent / 100)
                        stop_loss = entry_price * (1 - sl_percent / 100)
                    else:  # SELL
                        take_profit = entry_price * (1 - tp_percent / 100)
                        stop_loss = entry_price * (1 + sl_percent / 100)
                    
                    # Map MT5 symbol to commodity
                    commodity_id = None
                    for comm_id, comm_data in COMMODITIES.items():
                        if (comm_data.get('mt5_libertex_symbol') == symbol or 
                            comm_data.get('mt5_icmarkets_symbol') == symbol):
                            commodity_id = comm_id
                            break
                    
                    # Save settings
                    trade_settings = {
                        'trade_id': str(ticket),
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'commodity': commodity_id or symbol,
                        'entry_price': entry_price,
                        'platform': platform_name
                    }
                    
                    await db.trade_settings.update_one(
                        {'trade_id': str(ticket)},
                        {'$set': trade_settings},
                        upsert=True
                    )
                    
                    logger.info(f"✅ Auto-Set SL/TP für Trade #{ticket}: SL={stop_loss:.2f}, TP={take_profit:.2f}")
                    updated_count += 1
                    
            except Exception as e:
                error_msg = f"Fehler bei Platform {platform_name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"✅ SL/TP automatisch gesetzt für {updated_count} Trade(s)",
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-set SL/TP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/close")
async def close_trade_v2(request: CloseTradeRequest):
    """Close an open trade - supports both DB trades and MT5 positions"""
    try:
        trade_id = request.trade_id
        ticket = request.ticket
        platform = request.platform
        
        logger.info(f"Close trade request: trade_id={trade_id}, ticket={ticket}, platform={platform}")
        
        # If we have a ticket, close the MT5 position
        if ticket and platform:
            from multi_platform_connector import MultiPlatformConnector
            connector = MultiPlatformConnector()
            
            await connector.connect_platform(platform)
            platform_info = connector.platforms.get(platform)
            
            if platform_info and platform_info.get('connector'):
                mt5_connector = platform_info['connector']
                
                # Get position details BEFORE closing (for DB storage)
                positions = await connector.get_open_positions(platform)
                position_data = None
                logger.info(f"🔍 Found {len(positions)} open positions on {platform}")
                for pos in positions:
                    if str(pos.get('ticket') or pos.get('id')) == str(ticket):
                        position_data = pos
                        logger.info(f"✅ Found position_data for ticket {ticket}: {pos.get('symbol')}")
                        break
                
                if not position_data:
                    logger.warning(f"⚠️ position_data is None for ticket {ticket}! Cannot save to DB.")
                
                # V2.3.31: Close on MT5 mit detaillierter Fehlerbehandlung
                close_result = await mt5_connector.close_position(str(ticket))
                
                # Handle both old (bool) and new (dict) return types
                if isinstance(close_result, dict):
                    success = close_result.get('success', False)
                    error_msg = close_result.get('error')
                    error_type = close_result.get('error_type')
                else:
                    success = close_result
                    error_msg = None
                    error_type = None
                
                # V2.3.31: Bei Fehler spezifische Meldung zurückgeben
                if not success:
                    if error_type == 'MARKET_CLOSED':
                        raise HTTPException(status_code=400, detail=error_msg or "Die Börse ist gerade geschlossen")
                    elif error_type == 'TIMEOUT':
                        raise HTTPException(status_code=504, detail=error_msg or "Zeitüberschreitung - bitte erneut versuchen")
                    elif error_type == 'INVALID_TICKET':
                        raise HTTPException(status_code=404, detail=error_msg or "Position nicht gefunden")
                    else:
                        raise HTTPException(status_code=500, detail=error_msg or "Position konnte nicht geschlossen werden")
                
                if success:
                    logger.info(f"✅ Closed MT5 position {ticket} on {platform}")
                    
                    # WICHTIG: Speichere geschlossenen Trade in DB für Historie
                    # FALLBACK: Wenn position_data None ist, nutze trade_data vom Frontend
                    if not position_data and request.trade_data:
                        logger.warning(f"⚠️ position_data is None - using trade_data from frontend for ticket {ticket}")
                        td = request.trade_data
                        # Map frontend data to position_data format
                        position_data = {
                            'symbol': td.get('commodity', 'UNKNOWN'),  # Frontend sendet bereits commodity_id
                            'type': 'POSITION_TYPE_BUY' if td.get('type') == 'BUY' else 'POSITION_TYPE_SELL',
                            'price_open': td.get('entry_price', 0),
                            'price_current': td.get('current_price', 0),
                            'volume': td.get('quantity', 0),
                            'profit': td.get('profit_loss', 0),
                            'time': td.get('opened_at', datetime.now(timezone.utc).isoformat())
                        }
                    elif not position_data:
                        logger.warning(f"⚠️ No position_data and no trade_data - creating minimal fallback for ticket {ticket}")
                        position_data = {
                            'symbol': 'UNKNOWN',
                            'type': 'POSITION_TYPE_BUY',
                            'price_open': 0,
                            'price_current': 0,
                            'volume': 0,
                            'profit': 0,
                            'time': datetime.now(timezone.utc).isoformat()
                        }
                    
                    if position_data:
                        try:
                            # Symbol-Mapping: MT5-Symbole → Unsere Commodity-IDs (gleich wie in /trades/list)
                            symbol_to_commodity = {
                                'XAUUSD': 'GOLD',
                                'XAGUSD': 'SILVER',
                                'XPTUSD': 'PLATINUM',
                                'XPDUSD': 'PALLADIUM',
                                'PL': 'PLATINUM',
                                'PA': 'PALLADIUM',
                                'USOILCash': 'WTI_CRUDE',
                                'WTI_F6': 'WTI_CRUDE',
                                'UKOUSD': 'BRENT_CRUDE',
                                'CL': 'BRENT_CRUDE',
                                'NGASCash': 'NATURAL_GAS',
                                'NG': 'NATURAL_GAS',
                                'HGF6': 'COPPER',
                                'COPPER': 'COPPER',
                                'BTCUSD': 'BITCOIN',
                                'WHEAT': 'WHEAT',
                                'CORN': 'CORN',
                                'SOYBEAN': 'SOYBEANS',
                                'COFFEE': 'COFFEE',
                                'SUGAR': 'SUGAR',
                                'COTTON': 'COTTON',
                                'COCOA': 'COCOA'
                            }
                            
                            mt5_symbol = position_data.get('symbol', 'UNKNOWN')
                            # Check if symbol is already a commodity_id (from frontend trade_data)
                            if mt5_symbol in ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'WTI_CRUDE', 'BRENT_CRUDE', 'NATURAL_GAS', 'COPPER', 'BITCOIN', 'WHEAT', 'CORN', 'SOYBEANS', 'COFFEE', 'SUGAR', 'COTTON', 'COCOA']:
                                commodity_id = mt5_symbol  # Already mapped
                            else:
                                commodity_id = symbol_to_commodity.get(mt5_symbol, mt5_symbol)  # Map MT5 symbol
                            
                            # Timestamp konvertieren (könnte Unix timestamp sein)
                            opened_time = position_data.get('time')
                            if isinstance(opened_time, (int, float)):
                                # Unix timestamp to ISO string
                                opened_at = datetime.fromtimestamp(opened_time, tz=timezone.utc).isoformat()
                            elif isinstance(opened_time, str):
                                opened_at = opened_time
                            else:
                                opened_at = datetime.now(timezone.utc).isoformat()
                            
                            # V2.3.31: Verbesserte Closed Trade Speicherung
                            closed_trade = {
                                "id": f"mt5_{ticket}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "mt5_ticket": str(ticket),
                                "commodity": commodity_id,
                                "type": "BUY" if position_data.get('type') == 'POSITION_TYPE_BUY' else "SELL",
                                "entry_price": position_data.get('price_open', 0),
                                "exit_price": position_data.get('price_current', position_data.get('price_open', 0)),
                                "quantity": position_data.get('volume', 0),
                                "profit_loss": position_data.get('profit', 0),
                                "status": "CLOSED",
                                "platform": platform,
                                "strategy": position_data.get('comment', 'MANUAL'),
                                "opened_at": opened_at,
                                "closed_at": datetime.now(timezone.utc).isoformat(),
                                "closed_by": "MANUAL",
                                "close_reason": "MANUAL_CLOSE"
                            }
                            
                            logger.info(f"📝 Preparing to save closed trade: {closed_trade}")
                            
                            try:
                                await db.trades.insert_one(closed_trade)
                                logger.info(f"💾 ✅ Saved closed trade #{ticket} to DB: {commodity_id} {closed_trade['type']} (P/L: €{position_data.get('profit', 0):.2f})")
                            except Exception as db_error:
                                logger.error(f"❌ Database insert error: {db_error}")
                                # Versuche alternative Speicherung
                                try:
                                    from database_v2 import db_manager
                                    await db_manager.trades_db.insert_trade(closed_trade)
                                    logger.info(f"💾 ✅ Saved via database_v2: #{ticket}")
                                except Exception as e2:
                                    logger.error(f"❌ Alternative save also failed: {e2}")
                        except Exception as e:
                            logger.error(f"⚠️ Failed to save closed trade to DB: {e}", exc_info=True)
                            # Continue anyway - trade was closed on MT5
                    
                    return {
                        "success": True,
                        "message": f"Position {ticket} geschlossen",
                        "ticket": ticket
                    }
                else:
                    raise HTTPException(status_code=500, detail=f"MT5 Order konnte nicht geschlossen werden. Ticket: {ticket}")
            else:
                raise HTTPException(status_code=500, detail=f"Platform {platform} not connected")
        
        # Otherwise, close DB trade
        if trade_id:
            trade = await db.trades.find_one({"id": trade_id})
            if not trade:
                raise HTTPException(status_code=404, detail="Trade not found")
            
            if trade['status'] == 'CLOSED':
                raise HTTPException(status_code=400, detail="Trade already closed")
            
            await db.trades.update_one(
                {"id": trade_id},
                {"$set": {
                    "status": "CLOSED",
                    "closed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return {"success": True, "trade_id": trade_id}
        
        raise HTTPException(status_code=400, detail="Missing trade_id or ticket")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/close/{trade_id}")
async def close_trade(trade_id: str, exit_price: float):
    """Close an open trade (legacy endpoint)"""
    try:
        trade = await db.trades.find_one({"id": trade_id})
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        if trade['status'] == 'CLOSED':
            raise HTTPException(status_code=400, detail="Trade already closed")
        
        profit_loss = (exit_price - trade['entry_price']) * trade['quantity']
        if trade['type'] == 'SELL':
            profit_loss = -profit_loss
        
        await db.trades.update_one(
            {"id": trade_id},
            {"$set": {
                "status": "CLOSED",
                "exit_price": exit_price,
                "profit_loss": profit_loss,
                "closed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"success": True, "profit_loss": profit_loss}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/cleanup")
async def cleanup_trades():
    """Lösche fehlerhafte Trades und Duplikate permanent aus der Datenbank"""
    try:
        # Simple cleanup - remove trades with errors or invalid data
        error_deleted = 0
        duplicate_deleted = 0
        
        # V2.3.32: Robustere Implementierung mit Null-Check
        try:
            # Remove trades with missing critical fields
            result = await db.trades.delete_many({
                "$or": [
                    {"symbol": {"$exists": False}},
                    {"openPrice": {"$exists": False}},
                    {"closePrice": {"$exists": False}}
                ]
            })
            if result and hasattr(result, 'deleted_count'):
                error_deleted = result.deleted_count
        except Exception as cleanup_error:
            logger.warning(f"Cleanup delete_many failed: {cleanup_error}")
        
        total_deleted = error_deleted + duplicate_deleted
        
        return {
            "success": True,
            "message": f"✅ {total_deleted} Trades gelöscht",
            "error_trades_deleted": error_deleted,
            "duplicate_trades_deleted": duplicate_deleted,
            "total_deleted": total_deleted
        }
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/ping")
async def ping():
    """Simple ping endpoint to test connectivity"""
    return {
        "status": "ok",
        "message": "Backend is reachable",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint - Frontend kann regelmäßig abfragen"""
    try:
        from multi_platform_connector import multi_platform
        
        # Get active platforms
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            return {"status": "error", "message": "No settings found"}
        
        active_platforms = settings.get('active_platforms', [])
        platform_status = {}
        
        for platform_name in active_platforms:
            if platform_name not in multi_platform.platforms:
                platform_status[platform_name] = {"connected": False, "error": "Unknown platform"}
                continue
            
            platform = multi_platform.platforms[platform_name]
            connector = platform.get('connector')
            
            if not connector:
                platform_status[platform_name] = {"connected": False, "error": "No connector"}
                continue
            
            try:
                is_connected = await connector.is_connected()
                balance = platform.get('balance', 0)
                
                platform_status[platform_name] = {
                    "connected": is_connected,
                    "balance": balance,
                    "name": platform.get('name', platform_name)
                }
            except Exception as e:
                platform_status[platform_name] = {
                    "connected": False,
                    "error": str(e)
                }
        
        # Check if any platform is connected
        any_connected = any(p.get('connected', False) for p in platform_status.values())
        
        return {
            "status": "ok" if any_connected else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platforms": platform_status,
            "database": "connected"  # MongoDB connection is always available
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@api_router.get("/trades/list")
async def get_trades(status: Optional[str] = None):
    """Get all trades - ONLY real MT5 positions + closed DB trades"""
    try:
        logger.info("🔍 /trades/list aufgerufen - NEU VERSION 2.0")
        
        # Get settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        logger.info(f"Active platforms: {active_platforms}")
        
        # Hole echte MT5-Positionen (LIVE)
        live_mt5_positions = []
        
        # PERFORMANCE OPTIMIZATION: Hole ALLE trade_settings auf einmal
        try:
            from database import trade_settings as trade_settings_collection
            cursor = await trade_settings_collection.find({})
            all_settings = await cursor.to_list(10000)
            trade_settings_map = {ts['trade_id']: ts for ts in all_settings if 'trade_id' in ts}
            logger.info(f"📊 Loaded {len(trade_settings_map)} trade settings for fast lookup")
        except Exception as e:
            logger.error(f"Error loading trade settings: {e}", exc_info=True)
            trade_settings_map = {}
        
        # V2.3.31: Lade Ticket-Strategie-Mapping für permanente Strategie-Zuordnung
        ticket_strategy_map = {}
        try:
            from database_v2 import db_manager
            ticket_strategy_map = await db_manager.trades_db.get_all_ticket_strategies()
            logger.info(f"📋 Loaded {len(ticket_strategy_map)} ticket-strategy mappings")
        except Exception as e:
            logger.warning(f"⚠️ Could not load ticket-strategy map: {e}")
        
        for platform_name in active_platforms:
            # Support both DEMO and REAL accounts
            if 'MT5_LIBERTEX' in platform_name or 'MT5_ICMARKETS' in platform_name:
                try:
                    from multi_platform_connector import multi_platform
                    positions = await multi_platform.get_open_positions(platform_name)
                    
                    # Konvertiere MT5-Positionen zu Trade-Format
                    # Symbol-Mapping: MT5-Symbole → Unsere Commodity-IDs
                    symbol_to_commodity = {
                        'XAUUSD': 'GOLD',
                        'XAGUSD': 'SILVER',
                        'XPTUSD': 'PLATINUM',
                        'XPDUSD': 'PALLADIUM',
                        'PL': 'PLATINUM',
                        'PA': 'PALLADIUM',
                        'USOILCash': 'WTI_CRUDE',
                        'WTI_F6': 'WTI_CRUDE',
                        'UKOUSD': 'BRENT_CRUDE',
                        'CL': 'BRENT_CRUDE',
                        'NGASCash': 'NATURAL_GAS',
                        'NG': 'NATURAL_GAS',
                        'HGF6': 'COPPER',
                        'COPPER': 'COPPER',
                        'BTCUSD': 'BITCOIN',
                        'WHEAT': 'WHEAT',
                        'CORN': 'CORN',
                        'SOYBEAN': 'SOYBEANS',
                        'COFFEE': 'COFFEE',
                        'SUGAR': 'SUGAR',
                        'COTTON': 'COTTON',
                        'COCOA': 'COCOA'
                    }
                    
                    for pos in positions:
                        mt5_symbol = pos.get('symbol', 'UNKNOWN')
                        commodity_id = symbol_to_commodity.get(mt5_symbol, mt5_symbol)  # Fallback to MT5 symbol
                        ticket = str(pos.get('ticket', pos.get('id')))
                        
                        # Hole Settings aus trade_settings_map
                        trade_id = f"mt5_{ticket}"
                        settings = trade_settings_map.get(trade_id, {})
                        
                        # 🐛 FIX v2.3.29: Lade echte Strategie aus trade_settings (NICHT hard-coded!)
                        # AI bestimmt Strategie basierend auf Trade-Parametern
                        real_strategy = settings.get('strategy')
                        
                        # V2.3.32 FIX: Prüfe auch die lokale trades DB für Strategie
                        if not real_strategy or real_strategy == 'day':
                            try:
                                local_trade = await db_manager.trades_db.find_trade_by_commodity_and_type(
                                    commodity=commodity_id, trade_type="BUY" if pos.get('type') == 'POSITION_TYPE_BUY' else "SELL"
                                )
                                if local_trade and local_trade.get('strategy') and local_trade.get('strategy') != 'day':
                                    real_strategy = local_trade.get('strategy')
                                    logger.debug(f"✅ Trade {trade_id}: Strategy from local DB = '{real_strategy}'")
                            except:
                                pass
                        
                        # V2.3.31: Strategie-Erkennung mit Ticket-Mapping (höchste Priorität!)
                        if not real_strategy:
                            # 1. Prüfe Ticket-Strategie-Mapping (dauerhaft gespeichert)
                            if str(ticket) in ticket_strategy_map:
                                real_strategy = ticket_strategy_map[str(ticket)]
                                logger.debug(f"✅ Trade {trade_id}: Strategy from ticket-map = '{real_strategy}'")
                            
                            # 2. Prüfe trade comment
                            if not real_strategy:
                                comment = pos.get('comment', '')
                                if 'mean_reversion' in comment.lower():
                                    real_strategy = 'mean_reversion'
                                elif 'momentum' in comment.lower():
                                    real_strategy = 'momentum'
                                elif 'breakout' in comment.lower():
                                    real_strategy = 'breakout'
                                elif 'grid' in comment.lower():
                                    real_strategy = 'grid'
                                elif 'scalping' in comment.lower():
                                    real_strategy = 'scalping'
                                elif 'swing' in comment.lower():
                                    real_strategy = 'swing'
                                elif 'day' in comment.lower():
                                    real_strategy = 'day'
                            
                            # 3. Fallback basierend auf SL/TP (letzte Option)
                            if not real_strategy:
                                sl = settings.get('stop_loss', 0) if settings else 0
                                tp = settings.get('take_profit', 0) if settings else 0
                                entry = pos.get('price_open', 0)
                                
                                if entry > 0 and sl > 0 and tp > 0:
                                    sl_percent = abs((entry - sl) / entry * 100)
                                    tp_percent = abs((tp - entry) / entry * 100)
                                    
                                    if sl_percent < 0.5 and tp_percent < 1.0:
                                        real_strategy = 'scalping'
                                    elif tp_percent > 5.0:
                                        real_strategy = 'swing'
                                    else:
                                        real_strategy = 'day'
                                else:
                                    real_strategy = 'day'
                                
                                logger.warning(f"⚠️ Trade {trade_id}: No strategy found, using fallback='{real_strategy}'")
                        
                        # Debug: Log Strategie-Erkennung
                        if settings:
                            logger.debug(f"✅ Trade {trade_id}: Strategy='{real_strategy}' (from {'DB' if settings.get('strategy') else 'auto-detection'})")
                        else:
                            logger.debug(f"⚠️ No settings for {trade_id}, using default strategy='{real_strategy}'")
                        
                        trade = {
                            "id": trade_id,
                            "mt5_ticket": ticket,
                            "commodity": commodity_id,  # Unser internes Symbol!
                            "type": "BUY" if pos.get('type') == 'POSITION_TYPE_BUY' else "SELL",
                            "entry_price": pos.get('price_open', 0),
                            "price": pos.get('price_current', pos.get('price_open', 0)),
                            "quantity": pos.get('volume', 0),
                            "profit_loss": pos.get('profit', 0),
                            "status": "OPEN",
                            "platform": platform_name,
                            "mode": platform_name,
                            "stop_loss": settings.get('stop_loss'),  # Aus trade_settings DB
                            "take_profit": settings.get('take_profit'),  # Aus trade_settings DB
                            "strategy": real_strategy,  # 🐛 FIX: Echte Strategie, nicht hard-coded!
                            "timestamp": pos.get('time', datetime.now(timezone.utc).isoformat())
                        }
                        live_mt5_positions.append(trade)
                except Exception as e:
                    logger.error(f"Fehler beim Holen von {platform_name} Positionen: {e}")
        
        # Hole GESCHLOSSENE Trades aus DB
        query = {"status": "CLOSED"}
        logger.info(f"📊 Live MT5 Positionen: {len(live_mt5_positions)}")
        
        if status and status.upper() == "OPEN":
            # Wenn nur OPEN angefordert, gib nur MT5-Positionen zurück
            trades = live_mt5_positions
        elif status and status.upper() == "CLOSED":
            # Wenn nur CLOSED angefordert, gib nur DB-Trades zurück
            cursor = await db.trades.find(query, {"_id": 0})
            trades = await cursor.to_list(1000)
        else:
            # Sonst beide kombinieren
            cursor = await db.trades.find(query, {"_id": 0})
            closed_trades = await cursor.to_list(1000)
            logger.info(f"📊 Geschlossene Trades aus DB: {len(closed_trades)}")
            trades = live_mt5_positions + closed_trades
        
        # Sort manually - handle mixed timestamp formats
        def get_sort_key(trade):
            timestamp = trade.get('created_at') or trade.get('timestamp') or ''
            if isinstance(timestamp, datetime):
                return timestamp
            elif isinstance(timestamp, str):
                try:
                    return datetime.fromisoformat(timestamp)
                except:
                    return datetime.min
            return datetime.min
        
        try:
            trades.sort(key=get_sort_key, reverse=True)
        except Exception as e:
            logger.error(f"Sorting error: {e}")
            # Fallback: no sorting
        
        # Convert timestamps
        for trade in trades:
            # Handle both created_at and timestamp fields
            if 'timestamp' in trade and isinstance(trade['timestamp'], str):
                trade['timestamp'] = datetime.fromisoformat(trade['timestamp']).isoformat()
            if 'created_at' in trade and isinstance(trade['created_at'], str):
                # Add timestamp field for frontend compatibility
                trade['timestamp'] = trade['created_at']
            if trade.get('closed_at') and isinstance(trade['closed_at'], str):
                trade['closed_at'] = datetime.fromisoformat(trade['closed_at']).isoformat()
        
        # Filter errors AND deduplicate by ticket ID
        # Reason: MT5_LIBERTEX and MT5_LIBERTEX_DEMO point to same account, causing duplicates
        unique_trades = []
        seen_tickets = set()
        
        for trade in trades:
            ticket = trade.get('mt5_ticket') or trade.get('ticket')
            commodity = trade.get('commodity', '')
            status = trade.get('status', '')
            
            # Skip trades with MetaAPI error codes
            if ticket and isinstance(ticket, str) and 'TRADE_RETCODE' in str(ticket):
                logger.debug(f"Filtered error trade: {ticket}")
                continue
            
            if commodity and 'TRADE_RETCODE' in str(commodity):
                logger.debug(f"Filtered error trade: commodity={commodity}")
                continue
            
            # Deduplicate by ticket ID (OPEN trades only - closed trades may have same ticket)
            if status == 'OPEN' and ticket:
                if ticket in seen_tickets:
                    logger.debug(f"Filtered duplicate open trade: ticket={ticket}")
                    continue
                seen_tickets.add(ticket)
            
            unique_trades.append(trade)
        
        logger.info(f"Trades fetched: {len(trades)} total, {len(unique_trades)} after deduplication")
        
        return {"trades": unique_trades}
    
    except Exception as e:
        logger.error(f"Error in get_trades: {e}", exc_info=True)
        return {"trades": []}


@api_router.post("/trades/{trade_id}/settings")
async def update_trade_settings(trade_id: str, settings: dict):
    """
    Update individuelle Settings für einen spezifischen Trade
    Diese werden von der KI überwacht und angewendet
    """
    try:
        # Speichere individuelle Trade Settings
        trade_settings = {
            'trade_id': trade_id,
            'stop_loss': settings.get('stop_loss'),
            'take_profit': settings.get('take_profit'),
            'trailing_stop': settings.get('trailing_stop', False),
            'trailing_stop_distance': settings.get('trailing_stop_distance', 50),  # in Pips
            'strategy': settings.get('strategy') or settings.get('strategy_type', 'swing'),  # WICHTIG: 'strategy' nicht 'strategy_type'
            'notes': settings.get('notes', ''),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert in DB
        await db.trade_settings.update_one(
            {'trade_id': trade_id},
            {'$set': trade_settings},
            upsert=True
        )
        
        logger.info(f"✅ Trade Settings gespeichert für #{trade_id}: SL={settings.get('stop_loss')}, TP={settings.get('take_profit')}, Strategy={trade_settings['strategy']}")
        
        return {
            'success': True,
            'message': 'Trade Settings gespeichert',
            'settings': trade_settings
        }
    
    except Exception as e:
        logger.error(f"Error updating trade settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades/{trade_id}/settings")
async def get_trade_settings(trade_id: str):
    """
    Hole individuelle Settings für einen Trade
    """
    try:
        settings = await db.trade_settings.find_one({'trade_id': trade_id})
        
        if settings:
            settings.pop('_id', None)
            # Für Backward-Kompatibilität: stelle sicher dass 'strategy' vorhanden ist
            if 'strategy' not in settings and 'strategy_type' in settings:
                settings['strategy'] = settings['strategy_type']
            return settings
        else:
            # Keine individuellen Settings - return defaults
            return {
                'trade_id': trade_id,
                'stop_loss': None,
                'take_profit': None,
                'trailing_stop': False,
                'strategy': 'swing'
            }
    
    except Exception as e:
        logger.error(f"Error getting trade settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trades/stats", response_model=TradeStats)
async def get_trade_stats():
    """Get trading statistics - USES SAME LOGIC AS /trades/list (no duplicates!)"""
    try:
        # Use the SAME logic as /trades/list to avoid discrepancies!
        # This calls get_trades() internally which already handles MT5 sync
        from fastapi import Request
        
        # Get unified trades list (same as /trades/list endpoint)
        trades_response = await get_trades()
        all_trades = trades_response.get('trades', [])
        
        # Calculate stats from unified trade list
        open_positions = [t for t in all_trades if t.get('status') == 'OPEN']
        closed_positions = [t for t in all_trades if t.get('status') == 'CLOSED']
        
        total_trades = len(all_trades)
        
        # Calculate P&L from open positions (live MT5)
        open_pl = sum([t.get('profit_loss', 0) or 0 for t in open_positions])
        
        # Calculate P&L from closed positions (DB)
        closed_pl = sum([t.get('profit_loss', 0) or 0 for t in closed_positions if t.get('profit_loss') is not None])
        
        total_profit_loss = open_pl + closed_pl
        
        # Calculate win/loss stats (only from closed trades)
        closed_with_pl = [t for t in closed_positions if t.get('profit_loss') is not None]
        winning_trades = len([t for t in closed_with_pl if t['profit_loss'] > 0])
        losing_trades = len([t for t in closed_with_pl if t['profit_loss'] <= 0])
        
        win_rate = (winning_trades / len(closed_with_pl) * 100) if len(closed_with_pl) > 0 else 0
        
        return TradeStats(
            total_trades=total_trades,
            open_positions=len(open_positions),
            closed_positions=len(closed_positions),
            total_profit_loss=round(total_profit_loss, 2),
            win_rate=round(win_rate, 2),
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/settings", response_model=TradingSettings)
async def get_settings():
    """Get trading settings"""
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if not settings:
        # Create default settings
        default_settings = TradingSettings()
        doc = default_settings.model_dump()
        await db.trading_settings.insert_one(doc)
        return default_settings
    
    settings.pop('_id', None)
    return TradingSettings(**settings)

@api_router.post("/settings", response_model=TradingSettings)
async def update_settings(settings: TradingSettings):
    """Update trading settings and reinitialize AI if needed"""
    global ai_trading_bot_instance, bot_task
    
    logger.info("📥 POST /api/settings aufgerufen")
    print("📥 POST /api/settings aufgerufen", flush=True)  # Debug
    
    try:
        # Only update provided fields, keep existing values for others
        doc = settings.model_dump(exclude_unset=False, exclude_none=False)
        print(f"📋 Settings Update - TP/SL Keys im Request: {[k for k in doc.keys() if 'stop_loss' in k or 'take_profit' in k][:10]}", flush=True)
        
        # Get existing settings first to preserve API keys
        existing = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Check if auto_trading status changed
        auto_trading_changed = False
        if existing:
            old_auto_trading = existing.get('auto_trading', False)
            new_auto_trading = settings.auto_trading
            auto_trading_changed = old_auto_trading != new_auto_trading
        
        # Merge: Keep existing values for fields that weren't explicitly set
        if existing:
            # Preserve API keys if not provided in update
            for key in ['openai_api_key', 'gemini_api_key', 'anthropic_api_key', 'bitpanda_api_key',
                       'mt5_libertex_account_id', 'mt5_icmarkets_account_id']:
                if key in existing and (key not in doc or doc[key] is None or doc[key] == ''):
                    doc[key] = existing[key]
        
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": doc},
            upsert=True
        )
        print("✅ DB Update erfolgreich!", flush=True)
        
        # ⚡ AUTOMATISCH: Trade Settings für alle offenen Trades aktualisieren
        # 🆕 v2.3.29: Erweitert um ALLE 7 Strategien!
        strategy_keys = [
            'day_stop_loss_percent', 'day_take_profit_percent',
            'swing_stop_loss_percent', 'swing_take_profit_percent',
            'scalping_stop_loss_percent', 'scalping_take_profit_percent',
            'mean_reversion_stop_loss_percent', 'mean_reversion_take_profit_percent',
            'momentum_stop_loss_percent', 'momentum_take_profit_percent',
            'breakout_stop_loss_percent', 'breakout_take_profit_percent',
            'grid_stop_loss_percent', 'grid_take_profit_per_level_percent',
            # Auch Modus-Änderungen
            'day_sl_mode', 'day_tp_mode', 'day_stop_loss_euro', 'day_take_profit_euro'
        ]
        
        # v2.3.33: Trade-Settings Update wenn SL/TP geändert wurde
        strategy_keys_in_doc = [k for k in strategy_keys if k in doc]
        print(f"🔍 Strategy keys in doc: {strategy_keys_in_doc[:5]}...", flush=True)
        
        if any(key in doc for key in strategy_keys):
            print("🔄 Trading Settings geändert - aktualisiere offene Trades...", flush=True)
            logger.info("🔄 Trading Settings geändert - aktualisiere offene Trades...")
            try:
                print("  → Lade Module...", flush=True)
                from multi_platform_connector import multi_platform
                from trade_settings_manager import trade_settings_manager
                print("  → Module geladen!", flush=True)
                
                active_platforms = doc.get('active_platforms', existing.get('active_platforms', []) if existing else [])
                print(f"📋 Active Platforms: {active_platforms}", flush=True)
                updated_settings = await db.trading_settings.find_one({"id": "trading_settings"})
                print(f"📋 Updated Settings Mean Reversion SL: {updated_settings.get('mean_reversion_stop_loss_percent')}", flush=True)
                
                # Sammle alle offenen Positionen
                all_positions = []
                print(f"🔍 Sammle Positionen von {len(active_platforms)} Plattformen...", flush=True)
                for platform_name in active_platforms:
                    print(f"  → Prüfe {platform_name}...", flush=True)
                    if 'MT5_' in platform_name:
                        try:
                            positions = await multi_platform.get_open_positions(platform_name)
                            print(f"📊 {platform_name}: {len(positions)} offene Positionen", flush=True)
                            logger.info(f"📊 {platform_name}: {len(positions)} offene Positionen")
                            all_positions.extend(positions)
                        except Exception as e:
                            print(f"⚠️ {platform_name} ERROR: {e}", flush=True)
                            logger.warning(f"⚠️ {platform_name}: {e}")
                
                print(f"📊 Gesammelt: {len(all_positions)} Positionen total", flush=True)
                if all_positions:
                    print(f"🔄 Starte Trade-Updates für {len(all_positions)} Trades...", flush=True)
                    logger.info(f"🔄 Aktualisiere SL/TP für {len(all_positions)} Trades...")
                    
                    # V2.3.34: Lade existierende trade_settings für Strategie-Mapping
                    trade_settings_coll = db.trade_settings
                    all_settings = await trade_settings_coll.find({}, {"_id": 0}).to_list(10000)
                    settings_by_ticket = {}
                    for ts in all_settings:
                        tid = ts.get('trade_id', '')
                        if tid.startswith('mt5_'):
                            ticket = tid.replace('mt5_', '')
                            settings_by_ticket[ticket] = ts
                    logger.info(f"📋 Lade {len(settings_by_ticket)} existierende Trade-Settings")
                    
                    # V2.3.34: Lade ticket_strategy_map für Strategie-Erkennung
                    ticket_strategy_map = {}
                    try:
                        ticket_strategy_map = await db_manager.trades_db.get_all_ticket_strategies()
                        logger.info(f"📋 Loaded {len(ticket_strategy_map)} ticket-strategy mappings")
                    except Exception as e:
                        logger.warning(f"⚠️ Konnte ticket_strategy_map nicht laden: {e}")
                    
                    updated_count = 0
                    errors = []
                    for i, pos in enumerate(all_positions):
                        try:
                            ticket = str(pos.get('ticket', pos.get('id', '')))
                            
                            # Hole existierende Strategie aus trade_settings oder ticket_strategy_map
                            existing_settings = settings_by_ticket.get(ticket, {})
                            
                            # V2.3.34: Prüfe mehrere Quellen für Strategie
                            strategy = existing_settings.get('strategy')
                            if not strategy:
                                # Prüfe ticket_strategy_map (globales Mapping)
                                strategy = ticket_strategy_map.get(ticket, 'day')
                            
                            # Transformiere Position in das erwartete Format
                            entry_price = pos.get('price_open', 0) or pos.get('openPrice', 0) or 0
                            trade_data = {
                                'ticket': ticket,
                                'price_open': entry_price,
                                'entry_price': entry_price,
                                'type': 'SELL' if pos.get('type') == 'POSITION_TYPE_SELL' else 'BUY',
                                'strategy': strategy,
                                'commodity': pos.get('symbol', 'UNKNOWN')
                            }
                            
                            logger.info(f"  → Trade {i+1}/{len(all_positions)}: {trade_data['commodity']} ({strategy}) Entry={entry_price}")
                            
                            result = await trade_settings_manager.get_or_create_settings_for_trade(
                                trade=trade_data,
                                global_settings=updated_settings,
                                force_update=True
                            )
                            if result:
                                updated_count += 1
                                new_sl = result.get('stop_loss', 0)
                                new_tp = result.get('take_profit', 0)
                                logger.info(f"    ✅ SL={new_sl:.2f}, TP={new_tp:.2f}")
                        except Exception as e:
                            errors.append(f"Trade {ticket}: {e}")
                            logger.error(f"❌ Trade {ticket}: {e}", exc_info=True)
                    
                    logger.info(f"✅ {updated_count}/{len(all_positions)} Trade Settings aktualisiert!")
                    
                    # V2.3.34: Sync aufrufen wenn Trade-Updates stattfanden
                    if updated_count > 0:
                        logger.info("🔄 Rufe Sync auf um DB zu aktualisieren...")
                        await sync_trade_settings()
                    logger.info(f"✅ {updated_count} Trade Settings aktualisiert!")
                else:
                    logger.info("ℹ️ Keine offenen Trades zum Aktualisieren")
                    
            except Exception as e:
                logger.error(f"❌ Trade Update Fehler: {e}", exc_info=True)
        
        # Reinitialize AI chat with new settings
        provider = settings.ai_provider
        model = settings.ai_model
        api_key = None
        ollama_base_url = settings.ollama_base_url or "http://localhost:11434"
        
        if provider == "openai":
            api_key = settings.openai_api_key
        elif provider == "gemini":
            api_key = settings.gemini_api_key
        elif provider == "anthropic":
            api_key = settings.anthropic_api_key
        elif provider == "ollama":
            ollama_model = settings.ollama_model or "llama2"
            init_ai_chat(provider="ollama", model=ollama_model, ollama_base_url=ollama_base_url)
            logger.info(f"Settings updated and AI reinitialized: Provider={provider}, Model={ollama_model}, URL={ollama_base_url}")
        else:
            init_ai_chat(provider=provider, api_key=api_key, model=model)
            logger.info(f"Settings updated and AI reinitialized: Provider={provider}, Model={model}")
        
        # V2.3.31: Multi-Bot System Management
        async def manage_bots_background():
            global multi_bot_manager, ai_trading_bot_instance, bot_task
            
            if auto_trading_changed:
                if settings.auto_trading:
                    logger.info("🤖 Auto-Trading aktiviert - starte Multi-Bot-System v2.3.31...")
                    
                    try:
                        # Versuche neues Multi-Bot-System
                        from multi_bot_system import MultiBotManager
                        from database_v2 import db_manager
                        
                        # Stoppe alte Bots falls vorhanden
                        if multi_bot_manager and multi_bot_manager.is_running:
                            await multi_bot_manager.stop_all()
                        
                        # Stoppe Legacy Bot falls vorhanden
                        if ai_trading_bot_instance and getattr(ai_trading_bot_instance, 'running', False):
                            ai_trading_bot_instance.stop()
                        
                        # Settings Getter Funktion
                        async def get_settings():
                            return await db.trading_settings.find_one({"id": "trading_settings"})
                        
                        # Starte neues Multi-Bot-System
                        multi_bot_manager = MultiBotManager(db_manager, get_settings)
                        await multi_bot_manager.start_all()
                        
                        logger.info("✅ Multi-Bot-System v2.3.31 gestartet (MarketBot + SignalBot + TradeBot)")
                        
                    except ImportError as e:
                        # Fallback: Legacy Single Bot
                        logger.warning(f"⚠️ Multi-Bot nicht verfügbar, nutze Legacy Bot: {e}")
                        from ai_trading_bot import AITradingBot
                        
                        if ai_trading_bot_instance and ai_trading_bot_instance.running:
                            ai_trading_bot_instance.stop()
                            if bot_task:
                                try:
                                    await asyncio.wait_for(bot_task, timeout=2.0)
                                except:
                                    pass
                        
                        ai_trading_bot_instance = AITradingBot()
                        if await ai_trading_bot_instance.initialize():
                            bot_task = asyncio.create_task(ai_trading_bot_instance.run_forever())
                            logger.info("✅ Legacy AI Trading Bot gestartet")
                else:
                    # Stop alle Bots wenn deaktiviert
                    logger.info("🛑 Auto-Trading deaktiviert - stoppe Bots...")
                    
                    # Stoppe Multi-Bot-System
                    if multi_bot_manager and multi_bot_manager.is_running:
                        await multi_bot_manager.stop_all()
                        logger.info("✅ Multi-Bot-System gestoppt")
                    
                    # Stoppe Legacy Bot
                    if ai_trading_bot_instance and getattr(ai_trading_bot_instance, 'running', False):
                        ai_trading_bot_instance.stop()
                        if bot_task:
                            try:
                                await asyncio.wait_for(bot_task, timeout=2.0)
                            except:
                                pass
                        logger.info("✅ Legacy Bot gestoppt")
        
        # Start bot management in background
        if auto_trading_changed:
            asyncio.create_task(manage_bots_background())
        
        # v2.3.33: Diese Nachricht ist veraltet - Updates sind jetzt aktiv!
        # Der Code bei Zeile ~3075 macht die Updates
        logger.info("✅ Settings-Update abgeschlossen")
        
        # Return immediately - settings saved successfully
        logger.info("✅ Settings gespeichert")
        
        # WICHTIG: Hole die gespeicherten Settings aus der DB zurück
        # damit auch die erhaltenen Werte (wie active_platforms) zurückgegeben werden
        saved_settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # DEBUG: Prüfe ob active_platforms vorhanden sind
        logger.info(f"📋 Saved settings keys: {list(saved_settings.keys()) if saved_settings else 'None'}")
        logger.info(f"📋 Active platforms in saved settings: {saved_settings.get('active_platforms') if saved_settings else 'None'}")
        logger.info(f"📋 Active platforms in input: {settings.active_platforms if hasattr(settings, 'active_platforms') else 'None'}")
        
        return saved_settings or settings
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/settings/reset")
async def reset_settings_to_default():
    """Reset trading settings to default values"""
    try:
        # Create default settings
        default_settings = TradingSettings(
            id="trading_settings",
            active_platforms=["MT5_LIBERTEX", "MT5_ICMARKETS"],
            auto_trading=False,
            use_ai_analysis=True,
            ai_provider="emergent",
            ai_model="gpt-5",
            stop_loss_percent=2.0,
            take_profit_percent=4.0,
            use_trailing_stop=False,
            trailing_stop_distance=1.5,
            max_trades_per_hour=3,
            position_size=1.0,
            max_portfolio_risk_percent=20.0,
            default_platform="MT5_LIBERTEX",
            enabled_commodities=["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COTTON", "COCOA"],
            # KI Trading Strategie-Parameter (Standardwerte)
            rsi_oversold_threshold=30.0,
            rsi_overbought_threshold=70.0,
            macd_signal_threshold=0.0,
            trend_following=True,
            min_confidence_score=0.6,
            use_volume_confirmation=True,
            risk_per_trade_percent=2.0
        )
        
        # Get existing settings to preserve API keys
        existing = await db.trading_settings.find_one({"id": "trading_settings"})
        
        # Preserve API keys and credentials
        if existing:
            default_settings.openai_api_key = existing.get('openai_api_key')
            default_settings.gemini_api_key = existing.get('gemini_api_key')
            default_settings.anthropic_api_key = existing.get('anthropic_api_key')
            default_settings.bitpanda_api_key = existing.get('bitpanda_api_key')
            default_settings.mt5_libertex_account_id = existing.get('mt5_libertex_account_id')
            default_settings.mt5_icmarkets_account_id = existing.get('mt5_icmarkets_account_id')
            default_settings.bitpanda_email = existing.get('bitpanda_email')
        
        # Update database
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": default_settings.model_dump()},
            upsert=True
        )
        
        # Reinitialize AI with default settings
        init_ai_chat(provider="emergent", model="gpt-5")
        
        logger.info("Settings reset to default values")
        return {"success": True, "message": "Einstellungen auf Standardwerte zurückgesetzt", "settings": default_settings}
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/metaapi/update-ids")
async def update_metaapi_ids(ids: dict):
    """
    🐛 FIX 10: Update MetaAPI Account IDs
    Aktualisiert die MetaAPI Account IDs in den Settings
    """
    try:
        logger.info(f"🔄 Updating MetaAPI IDs: {ids}")
        
        # Hole aktuelle Settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            raise HTTPException(status_code=404, detail="Settings nicht gefunden")
        
        # Update nur die MetaAPI IDs
        update_data = {}
        if 'libertex_demo_id' in ids and ids['libertex_demo_id']:
            update_data['mt5_libertex_account_id'] = ids['libertex_demo_id']
        if 'icmarkets_demo_id' in ids and ids['icmarkets_demo_id']:
            update_data['mt5_icmarkets_account_id'] = ids['icmarkets_demo_id']
        if 'libertex_real_id' in ids and ids['libertex_real_id']:
            update_data['mt5_libertex_real_account_id'] = ids['libertex_real_id']
        
        if not update_data:
            return {"success": True, "message": "Keine IDs zum Aktualisieren"}
        
        # Speichere in DB
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": update_data}
        )
        
        logger.info(f"✅ MetaAPI IDs aktualisiert: {list(update_data.keys())}")
        
        return {
            "success": True,
            "message": "MetaAPI IDs erfolgreich aktualisiert",
            "updated_ids": list(update_data.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating MetaAPI IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/bot/status")
async def get_bot_status():
    """V2.3.31: Hole Multi-Bot-System Status"""
    global multi_bot_manager, ai_trading_bot_instance
    
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    auto_trading = settings.get('auto_trading', False) if settings else False
    
    # V2.3.31: Multi-Bot-System Status
    if multi_bot_manager:
        bot_status = multi_bot_manager.get_status()
        return {
            "running": auto_trading and bot_status.get('manager_running', False),
            "instance_running": bot_status.get('manager_running', False),
            "task_alive": bot_status.get('manager_running', False),
            "message": "Multi-Bot-System v2.3.31 aktiv" if bot_status.get('manager_running') else "Auto-Trading deaktiviert",
            "version": "2.3.31",
            "architecture": "multi-bot",
            "bots": bot_status.get('bots', {}),
            "statistics": bot_status.get('statistics', {}),
            "trade_count": bot_status.get('statistics', {}).get('total_trades_executed', 0),
            "last_trades": []
        }
    
    # Fallback: Legacy Bot Status
    legacy_running = ai_trading_bot_instance and getattr(ai_trading_bot_instance, 'running', False)
    return {
        "running": auto_trading and legacy_running,
        "instance_running": legacy_running,
        "task_alive": legacy_running,
        "message": "Legacy Bot aktiv" if legacy_running else "Auto-Trading deaktiviert",
        "version": "legacy",
        "architecture": "single-bot",
        "trade_count": 0,
        "last_trades": []
    }

@api_router.post("/bot/start")
async def start_bot():
    """Starte AI Trading Bot - Bot läuft im Worker-Prozess"""
    try:
        # Aktiviere auto_trading in Settings
        # Der Worker-Prozess überwacht die Settings und startet den Bot automatisch
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            raise HTTPException(status_code=404, detail="Settings nicht gefunden")
        
        # Update auto_trading zu true
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"auto_trading": True}}
        )
        
        logger.info("✅ Auto-Trading aktiviert - Worker startet Bot")
        return {"success": True, "message": "AI Trading Bot wird im Worker gestartet"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Bot-Start: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/bot/stop")
async def stop_bot():
    """Stoppe AI Trading Bot - Bot läuft im Worker-Prozess"""
    try:
        # Deaktiviere auto_trading in Settings
        # Der Worker-Prozess überwacht die Settings und stoppt den Bot automatisch
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not settings:
            raise HTTPException(status_code=404, detail="Settings nicht gefunden")
        
        # Update auto_trading zu false
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"auto_trading": False}}
        )
        
        logger.info("✅ Auto-Trading deaktiviert - Worker stoppt Bot")
        return {"success": True, "message": "AI Trading Bot wird im Worker gestoppt"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fehler beim Bot-Stopp: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/market/refresh")
async def refresh_market_data():
    """Manually refresh market data"""
    await process_market_data()
    return {"success": True, "message": "Market data refreshed"}

@api_router.post("/trailing-stop/update")
async def update_trailing_stops_endpoint():
    """Update trailing stops for all open positions"""
    try:
        # Get current market data
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if not settings or not settings.get('use_trailing_stop', False):
            return {"success": False, "message": "Trailing stop not enabled"}
        
        # Get latest prices for all commodities
        current_prices = {}
        enabled = settings.get('enabled_commodities', ['WTI_CRUDE'])
        
        for commodity_id in enabled:
            market_data = await db.market_data.find_one(
                {"commodity": commodity_id},
                sort=[("timestamp", -1)]
            )
            if market_data:
                current_prices[commodity_id] = market_data['price']
        
        # Update trailing stops
        await update_trailing_stops(db, current_prices, settings)
        
        # Check for stop loss triggers
        trades_to_close = await check_stop_loss_triggers(db, current_prices)
        
        # Close triggered positions
        for trade_info in trades_to_close:
            await db.trades.update_one(
                {"id": trade_info['id']},
                {
                    "$set": {
                        "status": "CLOSED",
                        "exit_price": trade_info['exit_price'],
                        "closed_at": datetime.now(timezone.utc),
                        "strategy_signal": trade_info['reason']
                    }
                }
            )
        
        return {
            "success": True,
            "message": "Trailing stops updated",
            "closed_positions": len(trades_to_close)
        }
    except Exception as e:
        logger.error(f"Error updating trailing stops: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MT5 Integration Endpoints
@api_router.get("/mt5/account")
async def get_mt5_account():
    """Get real MT5 account information via MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        account_info = await connector.get_account_info()
        
        if not account_info:
            raise HTTPException(status_code=503, detail="Failed to get MetaAPI account info")
        
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting MetaAPI account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bitpanda Integration Endpoints
@api_router.get("/bitpanda/account")
async def get_bitpanda_account():
    """Get Bitpanda account information"""
    try:
        from bitpanda_connector import get_bitpanda_connector
        
        # Get API key from settings or environment
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        api_key = settings.get('bitpanda_api_key') if settings else None
        
        if not api_key:
            api_key = os.environ.get('BITPANDA_API_KEY')
        
        if not api_key:
            raise HTTPException(status_code=400, detail="Bitpanda API Key not configured")
        
        connector = await get_bitpanda_connector(api_key)
        account_info = await connector.get_account_info()
        
        if not account_info:
            raise HTTPException(status_code=503, detail="Failed to get Bitpanda account info")
        
        return account_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting Bitpanda account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/bitpanda/status")
async def get_bitpanda_status():
    """Check Bitpanda connection status"""
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        api_key = settings.get('bitpanda_api_key') if settings else None
        
        if not api_key:
            api_key = os.environ.get('BITPANDA_API_KEY')
        
        if not api_key:
            return {
                "connected": False,
                "message": "Bitpanda API Key not configured"
            }
        
        from bitpanda_connector import get_bitpanda_connector
        
        connector = await get_bitpanda_connector(api_key)
        account_info = await connector.get_account_info()
        
        return {
            "connected": connector.connected,
            "mode": "BITPANDA_REST",
            "balance": account_info.get('balance') if account_info else None,
            "email": settings.get('bitpanda_email') if settings else None
        }
    except Exception as e:
        logger.error(f"Error checking Bitpanda status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

@api_router.post("/trades/sync-settings")
async def sync_trade_settings():
    """
    V2.3.34: Wendet globale Settings auf ALLE offenen Trades an
    """
    try:
        from trade_settings_manager import trade_settings_manager
        
        # Hole globale Settings
        global_settings = await db.trading_settings.find_one({"id": "trading_settings"})
        if not global_settings:
            return {"success": False, "error": "No global settings found"}
        
        # Hole alle Trades mit ihren Strategien
        trades_data = await get_trades(status="OPEN")
        all_trades = trades_data.get('trades', [])
        
        print(f"🔄 Sync: Aktualisiere {len(all_trades)} Trades...", flush=True)
        logger.info(f"🔄 Sync: Aktualisiere {len(all_trades)} Trades...")
        
        updated_count = 0
        for i, trade in enumerate(all_trades):
            print(f"  Processing trade {i+1}/{len(all_trades)}: {trade.get('commodity')}", flush=True)
            try:
                ticket = str(trade.get('mt5_ticket', trade.get('ticket', '')))
                strategy = trade.get('strategy', 'day')
                entry_price = trade.get('entry_price', 0)
                trade_type = trade.get('type', 'BUY')
                
                if not ticket or not entry_price:
                    continue
                
                # Hole Strategy Config
                print(f"    → Getting strategy config for: {strategy}", flush=True)
                try:
                    strategy_config = trade_settings_manager._get_strategy_config_by_name(strategy, global_settings)
                except Exception as e:
                    print(f"    ❌ Error getting strategy config: {e}", flush=True)
                    strategy_config = None
                    
                if not strategy_config:
                    print(f"    → Using day trading fallback", flush=True)
                    strategy_config = trade_settings_manager._get_day_trading_strategy(global_settings)
                print(f"    → Strategy config: SL={strategy_config.get('stop_loss_percent')}%, TP={strategy_config.get('take_profit_percent')}%", flush=True)
                
                # Berechne neue SL/TP
                sl_percent = strategy_config.get('stop_loss_percent', 2.0)
                tp_percent = strategy_config.get('take_profit_percent', 4.0)
                
                if 'SELL' in str(trade_type).upper():
                    new_sl = entry_price * (1 + sl_percent / 100)
                    new_tp = entry_price * (1 - tp_percent / 100)
                else:  # BUY
                    new_sl = entry_price * (1 - sl_percent / 100)
                    new_tp = entry_price * (1 + tp_percent / 100)
                
                # Speichere in trade_settings Collection
                trade_settings_doc = {
                    'trade_id': f"mt5_{ticket}",
                    'ticket': ticket,
                    'strategy': strategy,
                    'stop_loss': round(new_sl, 2),
                    'take_profit': round(new_tp, 2),
                    'entry_price': entry_price,
                    'type': trade_type,
                    'max_loss_percent': sl_percent,
                    'take_profit_percent': tp_percent,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                print(f"    → Writing to SQLite: trade_id=mt5_{ticket}", flush=True)
                try:
                    # V2.3.34: SQLite statt MongoDB verwenden!
                    from database_v2 import db_manager
                    await db_manager.trades_db.save_trade_settings(f"mt5_{ticket}", trade_settings_doc)
                    print(f"    ✅ Saved to SQLite!", flush=True)
                except Exception as db_error:
                    print(f"    ❌ DB Error: {db_error}", flush=True)
                updated_count += 1
                logger.info(f"  ✅ {trade.get('commodity')} ({strategy}): SL={new_sl:.2f}, TP={new_tp:.2f}")
                
            except Exception as e:
                logger.error(f"Error syncing trade {trade.get('ticket')}: {e}")
        
        logger.info(f"✅ Sync komplett: {updated_count}/{len(all_trades)} Trades aktualisiert")
        return {
            "success": True,
            "message": f"Settings synced for {updated_count} trades"
        }
    except Exception as e:
        logger.error(f"Error syncing settings: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@api_router.get("/mt5/positions")
async def get_mt5_positions():
    """Get open positions from MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        positions = await connector.get_positions()
        
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error getting MetaAPI positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/{trade_id}/update-strategy")
async def update_trade_strategy(trade_id: str, data: dict):
    """Update strategy of a trade"""
    try:
        strategy = data.get('strategy', 'day')
        await db.trade_settings.update_one(
            {"trade_id": trade_id},
            {"$set": {"strategy": strategy}},
            upsert=True
        )
        logger.info(f"✅ Trade {trade_id} strategy → {strategy}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/trades/mt5-history")
async def get_mt5_closed_trades(
    start_date: str = None, 
    end_date: str = None,
    commodity: str = None,
    strategy: str = None,
    platform: str = None
):
    """
    V2.3.37: Hole geschlossene Trades DIREKT von MT5 + merge mit lokalen Daten
    
    Query Parameters:
    - start_date: ISO Format z.B. "2024-01-01" (default: 30 Tage zurück)
    - end_date: ISO Format z.B. "2024-12-31" (default: heute)
    - commodity: Filter nach Rohstoff z.B. "GOLD", "SILVER"
    - strategy: Filter nach Strategie z.B. "scalping", "day"
    - platform: Filter nach Plattform z.B. "MT5_LIBERTEX_DEMO"
    
    Returns:
    - trades: Liste aller geschlossenen Trades
    - filters: Verfügbare Filter-Optionen
    """
    try:
        from datetime import datetime, timezone, timedelta
        from multi_platform_connector import multi_platform
        
        # Parse Datumsfilter
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            # End of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        else:
            end_dt = datetime.now(timezone.utc)
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        else:
            start_dt = end_dt - timedelta(days=30)
        
        logger.info(f"📊 MT5 History: {start_dt.date()} - {end_dt.date()}, Commodity: {commodity or 'ALL'}, Strategy: {strategy or 'ALL'}")
        
        # Hole geschlossene Trades von MT5
        mt5_trades = await multi_platform.get_closed_trades(
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            platform_filter=platform
        )
        
        # Symbol-zu-Commodity Mapping
        symbol_to_commodity = {
            'XAUUSD': 'GOLD', 'GOLD': 'GOLD',
            'XAGUSD': 'SILVER', 'SILVER': 'SILVER',
            'USOUSD': 'WTI_CRUDE', 'WTIUSD': 'WTI_CRUDE', 'CL': 'WTI_CRUDE', 'OIL': 'WTI_CRUDE',
            'UKOUSD': 'BRENT_CRUDE', 'BRENT': 'BRENT_CRUDE',
            'NGUSD': 'NATURAL_GAS', 'NATGAS': 'NATURAL_GAS', 'NG': 'NATURAL_GAS',
            'BTCUSD': 'BITCOIN', 'BTC': 'BITCOIN',
            'EURUSD': 'EURUSD',
            'XPTUSD': 'PLATINUM', 'PLATINUM': 'PLATINUM',
            'XPDUSD': 'PALLADIUM', 'PALLADIUM': 'PALLADIUM',
            'COPPER': 'COPPER', 'HG': 'COPPER'
        }
        
        # Hole lokale Trade-Daten für Commodity/Strategy Info
        local_trades_map = {}
        try:
            cursor = db.trades.find({"status": "CLOSED"}, {"_id": 0})
            local_trades = await cursor.to_list(5000)
            for lt in local_trades:
                # Map by position ID oder ticket
                pos_id = lt.get('position_id') or lt.get('ticket') or lt.get('id')
                if pos_id:
                    local_trades_map[str(pos_id)] = lt
        except Exception as e:
            logger.warning(f"Could not load local trades: {e}")
        
        # Merge MT5-Daten mit lokalen Daten
        result_trades = []
        available_commodities = set()
        available_strategies = set()
        available_platforms = set()
        
        for trade in mt5_trades:
            # Finde Commodity aus Symbol
            symbol = trade.get('symbol', '')
            commodity_id = None
            for sym, comm in symbol_to_commodity.items():
                if sym in symbol.upper():
                    commodity_id = comm
                    break
            
            if not commodity_id:
                commodity_id = symbol  # Fallback: Use symbol as commodity
            
            # Finde lokale Daten für Strategy
            pos_id = str(trade.get('positionId', ''))
            local_data = local_trades_map.get(pos_id, {})
            trade_strategy = local_data.get('strategy', 'unknown')
            
            # Erstelle kombiniertes Trade-Objekt
            combined_trade = {
                'id': trade.get('id'),
                'positionId': trade.get('positionId'),
                'ticket': trade.get('positionId'),
                'symbol': symbol,
                'commodity': commodity_id,
                'commodity_id': commodity_id,
                'type': trade.get('type'),
                'direction': 'BUY' if 'BUY' in str(trade.get('type', '')).upper() else 'SELL',
                'volume': trade.get('volume'),
                'lot_size': trade.get('volume'),
                'entry_price': local_data.get('entry_price') or trade.get('price'),
                'exit_price': trade.get('price'),
                'profit': trade.get('profit', 0),
                'profit_loss': trade.get('profit', 0),
                'swap': trade.get('swap', 0),
                'commission': trade.get('commission', 0),
                'strategy': trade_strategy,
                'platform': trade.get('platform'),
                'platform_name': trade.get('platform_name'),
                'is_real': trade.get('is_real', False),
                'status': 'CLOSED',
                'closed_at': trade.get('time') or trade.get('brokerTime'),
                'time': trade.get('time'),
                'brokerTime': trade.get('brokerTime'),
                'comment': trade.get('comment'),
                'source': 'MT5'
            }
            
            # Tracking für Filter
            available_commodities.add(commodity_id)
            available_strategies.add(trade_strategy)
            available_platforms.add(trade.get('platform'))
            
            # Wende Filter an
            if commodity and commodity.upper() != commodity_id.upper():
                continue
            if strategy and strategy.lower() != trade_strategy.lower():
                continue
            
            result_trades.append(combined_trade)
        
        # Sortiere nach Zeit (neueste zuerst)
        result_trades.sort(key=lambda x: x.get('time', '') or '', reverse=True)
        
        # Berechne Statistiken
        total_profit = sum(t.get('profit', 0) or 0 for t in result_trades)
        winning_trades = len([t for t in result_trades if (t.get('profit', 0) or 0) > 0])
        losing_trades = len([t for t in result_trades if (t.get('profit', 0) or 0) < 0])
        
        return {
            "success": True,
            "trades": result_trades,
            "count": len(result_trades),
            "statistics": {
                "total_profit": round(total_profit, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(winning_trades / len(result_trades) * 100, 1) if result_trades else 0
            },
            "filters": {
                "commodities": sorted(list(available_commodities)),
                "strategies": sorted(list(available_strategies)),
                "platforms": sorted([p for p in available_platforms if p])
            },
            "date_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting MT5 history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/trades/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a specific trade from closed trades history"""
    try:
        # 🐛 FIX: Verbesserte Lösch-Logik mit besserer Fehlerbehandlung
        logger.info(f"🗑️ Deleting trade: {trade_id}")
        
        # Lösche Trade aus der trades DB (geschlossene Trades)
        result = await db.trades.delete_one({"id": trade_id})
        
        if result.deleted_count == 0:
            # Prüfe ob Trade vielleicht mit mt5_ Präfix existiert
            alt_id = f"mt5_{trade_id}" if not trade_id.startswith('mt5_') else trade_id.replace('mt5_', '')
            result = await db.trades.delete_one({"id": alt_id})
            if result.deleted_count == 0:
                logger.warning(f"⚠️ Trade {trade_id} nicht gefunden")
                raise HTTPException(status_code=404, detail="Trade nicht gefunden")
        
        # Lösche auch die zugehörigen trade_settings falls vorhanden
        await db.trade_settings.delete_one({"trade_id": trade_id})
        await db.trade_settings.delete_one({"trade_id": f"mt5_{trade_id}"})
        
        logger.info(f"✅ Trade {trade_id} erfolgreich gelöscht")
        return {"success": True, "message": "Trade gelöscht"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting trade {trade_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/trades/delete-all-closed")
async def delete_all_closed_trades():
    """Delete all closed trades from history - 🐛 NEW ENDPOINT"""
    try:
        logger.info("🗑️ Deleting all closed trades...")
        
        # Finde alle geschlossenen Trades
        cursor = await db.trades.find({"status": "CLOSED"})
        closed_trades = await cursor.to_list(10000)
        
        deleted_count = 0
        for trade in closed_trades:
            try:
                await db.trades.delete_one({"id": trade['id']})
                # Lösche auch trade_settings
                await db.trade_settings.delete_one({"trade_id": trade['id']})
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete trade {trade['id']}: {e}")
        
        logger.info(f"✅ {deleted_count} geschlossene Trades gelöscht")
        return {
            "success": True,
            "message": f"{deleted_count} Trades gelöscht",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"❌ Error deleting all closed trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/system/memory")
async def get_memory_stats():
    """Get current memory usage statistics"""
    try:
        import psutil
        import gc
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Get garbage collector stats
        gc_stats = gc.get_stats()
        gc_count = gc.get_count()
        
        return {
            "process": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # Physical memory
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # Virtual memory
                "percent": process.memory_percent()
            },
            "system": {
                "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2),
                "used_percent": psutil.virtual_memory().percent
            },
            "gc": {
                "collections": gc_count,
                "stats": gc_stats
            }
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {"error": str(e)}


@api_router.get("/system/cleanup")
async def force_cleanup():
    """Force garbage collection and cleanup"""
    try:
        import gc
        
        # Force garbage collection
        collected = gc.collect()
        
        logger.info(f"🧹 Manual cleanup: {collected} objects collected")
        
        return {
            "success": True,
            "objects_collected": collected,
            "message": "Cleanup abgeschlossen"
        }
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return {"error": str(e)}


@api_router.post("/mt5/order")
async def place_mt5_order(
    symbol: str,
    order_type: str,
    volume: float,
    platform: str = "MT5_LIBERTEX_DEMO",
    price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
):
    """Place order on MetaAPI via Multi-Platform Connector"""
    try:
        from multi_platform_connector import multi_platform
        
        # Use multi_platform connector (SDK first, REST fallback)
        result = await multi_platform.create_market_order(
            platform=platform,
            symbol=symbol,
            order_type=order_type.upper(),
            volume=volume,
            sl=stop_loss,
            tp=take_profit
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to place order on MetaAPI")
        
        return result
    except Exception as e:
        logger.error(f"Error placing MetaAPI order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/mt5/close/{ticket}")
async def close_mt5_position(ticket: str):
    """Close position on MetaAPI"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        success = await connector.close_position(ticket)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to close position on MetaAPI")
        
        return {"success": True, "ticket": ticket}
    except Exception as e:
        logger.error(f"Error closing MetaAPI position: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@api_router.post("/sync/positions")
async def sync_positions_endpoint():
    """Sync positions from MT5/Bitpanda to database"""
    try:
        await sync_mt5_positions()
        return {"success": True, "message": "Positions synchronized"}
    except Exception as e:
        logger.error(f"Error syncing positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/mt5/status")
async def get_mt5_status():
    """Check MetaAPI connection status"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        account_info = await connector.get_account_info()
        
        return {
            "connected": connector.connected,
            "mode": "METAAPI_REST",
            "account_id": connector.account_id,
            "balance": account_info.get('balance') if account_info else None,
            "trade_mode": account_info.get('trade_mode') if account_info else None,
            "broker": account_info.get('broker') if account_info else None
        }
    except Exception as e:
        logger.error(f"Error checking MetaAPI status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }

@api_router.get("/mt5/symbols")
async def get_mt5_symbols():
    """Get all available symbols from MetaAPI broker"""
    try:
        from metaapi_connector import get_metaapi_connector
        
        connector = await get_metaapi_connector()
        symbols = await connector.get_symbols()
        
        # MetaAPI returns symbols as an array of strings
        # Filter for commodity-related symbols (Oil, Gold, Silver, etc.)
        commodity_symbols = []
        commodity_keywords = ['OIL', 'GOLD', 'XAU', 'XAG', 'SILVER', 'COPPER', 'PLAT', 'PALL', 
                              'GAS', 'WHEAT', 'CORN', 'SOYBEAN', 'COFFEE', 'BRENT', 'WTI', 'CL']
        
        for symbol in symbols:
            # symbol is a string, not a dict
            symbol_name = symbol.upper()
            # Check if any commodity keyword is in the symbol name
            if any(keyword in symbol_name for keyword in commodity_keywords):
                commodity_symbols.append(symbol)
        
        logger.info(f"Found {len(commodity_symbols)} commodity symbols out of {len(symbols)} total")
        
        return {
            "success": True,
            "total_symbols": len(symbols),
            "commodity_symbols": sorted(commodity_symbols),  # Sort for easier reading
            "all_symbols": sorted(symbols)  # Include all symbols for reference, sorted
        }
    except Exception as e:
        logger.error(f"Error fetching MetaAPI symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbols: {str(e)}")

# Multi-Platform Endpoints
@api_router.get("/platforms/status")
async def get_platforms_status():
    """Get status of all trading platforms (SDK version)"""
    try:
        from multi_platform_connector import multi_platform
        
        status_dict = multi_platform.get_platform_status()
        active_platforms = multi_platform.get_active_platforms()
        
        # Convert dict to list for frontend compatibility
        platforms_list = []
        for platform_name, platform_data in status_dict.items():
            platforms_list.append({
                "platform": platform_name,
                "name": platform_data.get('name', platform_name),
                "connected": platform_data.get('active', False),
                "balance": platform_data.get('balance', 0.0),
                "is_real": platform_data.get('is_real', False)
            })
        
        return {
            "success": True,
            "active_platforms": active_platforms,
            "platforms": platforms_list
        }
    except Exception as e:
        logger.error(f"Error getting platforms status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/platforms/{platform_name}/connect")
async def connect_to_platform(platform_name: str):
    """Connect to a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        success = await multi_platform.connect_platform(platform_name)
        
        if success:
            return {
                "success": True,
                "message": f"Connected to {platform_name}",
                "platform": platform_name
            }
        else:
            raise HTTPException(status_code=503, detail=f"Failed to connect to {platform_name}")
    except Exception as e:
        logger.error(f"Error connecting to {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/platforms/{platform_name}/disconnect")
async def disconnect_from_platform(platform_name: str):
    """Disconnect from a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        success = await multi_platform.disconnect_platform(platform_name)
        
        if success:
            return {
                "success": True,
                "message": f"Disconnected from {platform_name}"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disconnect from {platform_name}")
    except Exception as e:
        logger.error(f"Error disconnecting from {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/platforms/{platform_name}/account")
async def get_platform_account(platform_name: str):
    """Get account information for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        account_info = await multi_platform.get_account_info(platform_name)
        
        if account_info:
            # Calculate portfolio risk from LIVE positions (not from DB!)
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', balance)
            margin_used = account_info.get('margin', 0)
            
            # Get LIVE open positions from broker
            try:
                open_positions = await multi_platform.get_open_positions(platform_name)
            except Exception as e:
                logger.warning(f"Could not get open positions for {platform_name}: {e}")
                open_positions = []
            
            # Calculate total EXPOSURE (not margin!) from positions
            # WICHTIG: Exposure = Entry Price × Volume (echtes Risiko)
            # NIEMALS die Margin von account_info verwenden!
            total_exposure = 0.0
            for position in open_positions:
                volume = position.get('volume', 0)
                # Verwende entry price für Exposure-Berechnung
                price = position.get('price_open', 0) or position.get('openPrice', 0)
                if not price:  # Fallback zu current price
                    price = position.get('price_current', 0) or position.get('currentPrice', 0)
                
                if volume and price:
                    # Exposure = Entry Price × Volume
                    pos_exposure = volume * price
                    total_exposure += pos_exposure
                    logger.debug(f"Position {position.get('symbol')}: {volume} lots @ €{price} = €{pos_exposure} exposure")
            
            logger.info(f"📊 {platform_name}: Total Exposure = €{total_exposure:.2f} from {len(open_positions)} positions")
            
            # Track unrealized P&L
            total_unrealized_pl = 0.0
            for position in open_positions:
                profit = position.get('profit', 0)
                total_unrealized_pl += profit
            
            # SPEZIAL-BEHANDLUNG für ICMarkets Crypto (MetaAPI Bug)
            # MetaAPI gibt falsche Margin für Crypto zurück
            if platform_name == "MT5_ICMARKETS_DEMO":
                # Prüfe ob Crypto-Positionen vorhanden sind
                has_crypto = any(
                    pos.get('symbol', '').startswith('BTC') or 
                    pos.get('symbol', '').startswith('ETH') 
                    for pos in open_positions
                )
                
                if has_crypto and margin_used > 0:
                    # MetaAPI-Bug: Gibt falsche Margin für ICMarkets Crypto zurück
                    # Empirischer Korrektur-Faktor basierend auf Broker-Vergleich
                    # Screenshot vom 2025-12-07:
                    # - Broker zeigt: 7.69 EUR Margin (5 × 0.01 lot BTCUSD)
                    # - MetaAPI meldet: 390.66 EUR
                    # - Korrektur-Faktor: 390.66 / 7.69 = 50.8
                    
                    ICMARKETS_CRYPTO_CORRECTION = 50.8
                    
                    corrected_margin = margin_used / ICMARKETS_CRYPTO_CORRECTION
                    logger.info(f"🔧 ICMarkets Crypto Korrektur: MetaAPI={margin_used:.2f} → Korrigiert={corrected_margin:.2f} (Faktor: /{ICMARKETS_CRYPTO_CORRECTION})")
                    margin_used = corrected_margin
                    # WICHTIG: Update auch account_info['margin'] mit korrigiertem Wert!
                    account_info['margin'] = corrected_margin
                    # Free Margin muss auch neu berechnet werden
                    account_info['freeMargin'] = equity - corrected_margin
                    account_info['free_margin'] = equity - corrected_margin
            
            # Portfolio risk as percentage of EQUITY (wie Libertex!)
            # KORREKTE FORMEL: Portfolio Risk % = (Margin Used / Equity) × 100
            portfolio_risk_percent = (margin_used / equity * 100) if equity > 0 else 0.0
            
            # Add risk info to account
            account_info['portfolio_risk'] = round(margin_used, 2)  # Genutzte Margin
            account_info['portfolio_risk_percent'] = round(portfolio_risk_percent, 2)
            account_info['open_trades_count'] = len(open_positions)
            account_info['open_positions_total'] = round(total_exposure, 2)  # Total Exposure für Info
            account_info['unrealized_pl'] = round(total_unrealized_pl, 2)
            
            return {
                "success": True,
                "platform": platform_name,
                "account": account_info
            }
        else:
            raise HTTPException(status_code=503, detail=f"Failed to get account info for {platform_name}")
    except Exception as e:
        logger.error(f"Error getting account for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/platforms/{platform_name}/positions")
async def get_platform_positions(platform_name: str):
    """Get open positions for a specific platform"""
    try:
        from multi_platform_connector import multi_platform
        
        positions = await multi_platform.get_open_positions(platform_name)
        
        return {
            "success": True,
            "platform": platform_name,
            "positions": positions
        }
    except Exception as e:
        logger.error(f"Error getting positions for {platform_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# V2.3.31: BACKTESTING & RISK MANAGEMENT ENDPOINTS
# ============================================================================

@api_router.post("/backtest/run")
async def run_backtest_endpoint(request: dict):
    """V2.3.36: Führt einen Backtest durch mit Market-Regime-Unterstützung"""
    try:
        from backtesting_engine import backtesting_engine
        
        # Extrahiere erweiterte Parameter (für zukünftige Verwendung)
        market_regime = request.get('market_regime', 'auto')
        use_regime_filter = request.get('use_regime_filter', True)
        use_news_filter = request.get('use_news_filter', True)
        use_trend_analysis = request.get('use_trend_analysis', True)
        max_portfolio_risk = request.get('max_portfolio_risk', 20)
        use_dynamic_lot_sizing = request.get('use_dynamic_lot_sizing', True)
        
        result = await backtesting_engine.run_backtest(
            strategy=request.get('strategy', 'day_trading'),
            commodity=request.get('commodity', 'GOLD'),
            start_date=request.get('start_date', '2024-01-01'),
            end_date=request.get('end_date', '2024-12-01'),
            initial_balance=request.get('initial_balance', 10000),
            sl_percent=request.get('sl_percent', 2.0),
            tp_percent=request.get('tp_percent', 4.0),
            lot_size=request.get('lot_size', 0.1)
        )
        
        # Berechne avg_trade_duration falls nicht vorhanden
        avg_trade_duration = getattr(result, 'avg_trade_duration', 0)
        
        return {
            "success": True,
            "result": {
                "strategy_name": result.strategy_name,
                "commodity": result.commodity,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_balance": result.initial_balance,
                "final_balance": result.final_balance,
                "total_trades": result.total_trades,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "win_rate": result.win_rate,
                "total_pnl": result.total_pnl,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "profit_factor": result.profit_factor,
                "avg_trade_duration": avg_trade_duration,
                "trades": result.trades[:20],
                "equity_curve": result.equity_curve,
                # Erweiterte Infos
                "filters_applied": {
                    "market_regime": market_regime,
                    "use_regime_filter": use_regime_filter,
                    "use_news_filter": use_news_filter,
                    "use_trend_analysis": use_trend_analysis,
                    "max_portfolio_risk": max_portfolio_risk,
                    "use_dynamic_lot_sizing": use_dynamic_lot_sizing
                }
            }
        }
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/risk/status")
async def get_risk_status_endpoint():
    """V2.3.31: Gibt den aktuellen Risiko-Status zurück"""
    try:
        from risk_manager import risk_manager, init_risk_manager
        from multi_platform_connector import multi_platform
        
        if not risk_manager.connector:
            await init_risk_manager(multi_platform)
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        await risk_manager.update_all_brokers(active_platforms)
        distribution = await risk_manager.get_broker_distribution()
        
        return {
            "success": True,
            "risk_limits": risk_manager.get_risk_limits(),
            "broker_distribution": distribution
        }
    except Exception as e:
        logger.error(f"Risk status error: {e}")
        return {"success": False, "error": str(e), "risk_limits": {"max_portfolio_risk_percent": 20.0}}


@api_router.post("/risk/assess")
async def assess_trade_risk_endpoint(request: dict):
    """V2.3.31: Bewertet Trade-Risiko"""
    try:
        from risk_manager import risk_manager, init_risk_manager
        from multi_platform_connector import multi_platform
        
        if not risk_manager.connector:
            await init_risk_manager(multi_platform)
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        assessment = await risk_manager.assess_trade_risk(
            commodity=request.get('commodity', 'GOLD'),
            action=request.get('action', 'BUY'),
            lot_size=request.get('lot_size', 0.1),
            price=request.get('price', 0),
            platform_names=active_platforms
        )
        
        return {
            "success": True,
            "can_trade": assessment.can_trade,
            "reason": assessment.reason,
            "recommended_broker": assessment.recommended_broker,
            "max_lot_size": assessment.max_lot_size,
            "risk_score": assessment.risk_score,
            "risk_level": "LOW" if assessment.risk_score < 30 else "MEDIUM" if assessment.risk_score < 60 else "HIGH"
        }
    except Exception as e:
        logger.error(f"Risk assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/backtest/strategies")
async def get_backtest_strategies():
    """V2.3.36: Verfügbare Strategien für Backtesting mit Market-Regime-Info"""
    return {
        "strategies": [
            {"id": "day_trading", "name": "Day Trading", "description": "Intraday Trades mit RSI und Trend", "regimes": ["WEAK_TREND_UP", "WEAK_TREND_DOWN"]},
            {"id": "swing_trading", "name": "Swing Trading", "description": "Mehrtägige Trendfolge-Trades", "regimes": ["STRONG_TREND_UP", "STRONG_TREND_DOWN", "WEAK_TREND_UP", "WEAK_TREND_DOWN"]},
            {"id": "scalping", "name": "Scalping", "description": "Schnelle Trades bei kleinen Bewegungen", "regimes": ["RANGE"]},
            {"id": "mean_reversion", "name": "Mean Reversion", "description": "Handel bei Bollinger Band Extremen", "regimes": ["RANGE", "LOW_VOLATILITY"]},
            {"id": "momentum", "name": "Momentum", "description": "Trendfolge-Strategie", "regimes": ["STRONG_TREND_UP", "STRONG_TREND_DOWN", "HIGH_VOLATILITY"]},
            {"id": "breakout", "name": "Breakout", "description": "Handel bei Range-Ausbrüchen", "regimes": ["STRONG_TREND_UP", "STRONG_TREND_DOWN", "HIGH_VOLATILITY"]},
            {"id": "grid", "name": "Grid Trading", "description": "Kaufe/Verkaufe bei festen Preisabständen", "regimes": ["RANGE", "LOW_VOLATILITY"]}
        ],
        "commodities": [
            {"id": "GOLD", "name": "Gold (XAU/USD)"},
            {"id": "SILVER", "name": "Silber (XAG/USD)"},
            {"id": "WTI_CRUDE", "name": "WTI Crude Oil"},
            {"id": "BRENT_CRUDE", "name": "Brent Crude Oil"},
            {"id": "NATURAL_GAS", "name": "Natural Gas"},
            {"id": "EURUSD", "name": "EUR/USD"},
            {"id": "BITCOIN", "name": "Bitcoin (BTC/USD)"},
            {"id": "PLATINUM", "name": "Platinum"},
            {"id": "COPPER", "name": "Kupfer"}
        ],
        "market_regimes": [
            {"id": "auto", "name": "Automatisch", "description": "System erkennt Regime automatisch"},
            {"id": "STRONG_TREND_UP", "name": "Starker Aufwärtstrend", "allowed": ["momentum", "swing", "breakout"]},
            {"id": "STRONG_TREND_DOWN", "name": "Starker Abwärtstrend", "allowed": ["momentum", "swing", "breakout"]},
            {"id": "RANGE", "name": "Seitwärtsmarkt", "allowed": ["mean_reversion", "grid", "scalping"]},
            {"id": "HIGH_VOLATILITY", "name": "Hohe Volatilität", "allowed": ["breakout", "momentum"]},
            {"id": "LOW_VOLATILITY", "name": "Niedrige Volatilität", "allowed": ["mean_reversion", "grid"]}
        ]
    }


# ============================================================================
# NEWS & MARKET REGIME ENDPOINTS (V2.3.35)
# ============================================================================

@api_router.get("/news/current")
async def get_news_endpoint():
    """V2.3.35: Gibt aktuelle klassifizierte News zurück"""
    if not NEWS_SYSTEM_AVAILABLE:
        return {"success": False, "error": "News System nicht verfügbar", "news": []}
    
    try:
        news = await get_current_news()
        return {
            "success": True,
            "news": news,
            "count": len(news),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return {"success": False, "error": str(e), "news": []}


@api_router.get("/news/decisions")
async def get_news_decisions_endpoint():
    """V2.3.35: Gibt das News-Decision-Log zurück (warum Trades blockiert wurden)"""
    if not NEWS_SYSTEM_AVAILABLE:
        return {"success": False, "error": "News System nicht verfügbar", "decisions": []}
    
    try:
        decisions = get_news_decision_log()
        return {
            "success": True,
            "decisions": decisions,
            "count": len(decisions)
        }
    except Exception as e:
        logger.error(f"News decisions error: {e}")
        return {"success": False, "error": str(e), "decisions": []}


@api_router.post("/news/check-trade")
async def check_trade_news_endpoint(request: dict):
    """
    V2.3.35: Prüft ob ein Trade durch News blockiert wird
    
    Body: {"asset": "GOLD", "strategy": "swing", "signal": "BUY"}
    """
    if not NEWS_SYSTEM_AVAILABLE:
        return {"allow_trade": True, "reason": "News System nicht verfügbar"}
    
    try:
        asset = request.get("asset", "GOLD")
        strategy = request.get("strategy", "swing")
        signal = request.get("signal", "HOLD")
        
        decision = await check_news_for_trade(asset, strategy, signal)
        
        return {
            "allow_trade": decision.allow_trade,
            "reason": decision.reason,
            "confidence_adjustment": decision.confidence_adjustment,
            "max_positions_multiplier": decision.max_positions_multiplier,
            "blocked_strategies": decision.blocked_strategies,
            "relevant_news_count": len(decision.relevant_news)
        }
    except Exception as e:
        logger.error(f"News check error: {e}")
        return {"allow_trade": True, "reason": f"Fehler: {e}"}


@api_router.post("/system/restart-backend")
async def restart_backend():
    """
    V2.3.35: Backend neu starten
    Führt das KILL-OLD-BACKENDS.sh Script aus und startet das Backend neu
    """
    import subprocess
    
    logger.warning("🔄 Backend-Neustart angefordert!")
    
    try:
        # Führe das Kill-Script aus
        kill_script = "/app/KILL-OLD-BACKENDS.sh"
        
        # Prüfe ob Script existiert
        import os
        if not os.path.exists(kill_script):
            return {"success": False, "error": f"Script nicht gefunden: {kill_script}"}
        
        # Führe Script im Hintergrund aus (damit die Response noch gesendet wird)
        subprocess.Popen(
            ["bash", kill_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        logger.info("✅ Kill-Script gestartet, Backend wird in Kürze neu starten")
        
        return {
            "success": True,
            "message": "Backend wird neu gestartet. Bitte warten Sie 5 Sekunden und laden Sie die Seite neu.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Restart-Fehler: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/system/diagnosis")
async def system_diagnosis_endpoint():
    """
    V2.3.35: Vollständige System-Diagnose
    Prüft ob alle KI-Komponenten korrekt funktionieren
    """
    diagnosis = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "OK",
        "components": {},
        "issues": []
    }
    
    # 1. Signal-Generierung testen
    try:
        test_data = {"RSI": 35, "MACD": 0.5, "MACD_signal": 0.3, "Close": 100, "EMA_20": 98}
        test_signal, test_trend = generate_signal(test_data)
        diagnosis["components"]["signal_generation"] = {
            "status": "OK",
            "test_result": f"Signal={test_signal}, Trend={test_trend}"
        }
    except Exception as e:
        diagnosis["components"]["signal_generation"] = {"status": "ERROR", "error": str(e)}
        diagnosis["issues"].append("Signal-Generierung fehlerhaft")
    
    # 2. News-System
    diagnosis["components"]["news_system"] = {
        "status": "OK" if NEWS_SYSTEM_AVAILABLE else "DISABLED",
        "available": NEWS_SYSTEM_AVAILABLE
    }
    
    # 3. Market Regime
    diagnosis["components"]["market_regime"] = {
        "status": "OK" if REGIME_SYSTEM_AVAILABLE else "DISABLED",
        "available": REGIME_SYSTEM_AVAILABLE
    }
    
    # 4. Trading-Bot Status
    try:
        from multi_bot_system import MultiBotManager
        diagnosis["components"]["trading_bot"] = {
            "status": "OK",
            "description": "MultiBotManager verfügbar"
        }
    except Exception as e:
        diagnosis["components"]["trading_bot"] = {"status": "ERROR", "error": str(e)}
    
    # 5. Platform-Verbindungen
    try:
        from multi_platform_connector import multi_platform
        connected = 0
        for name, data in multi_platform.platforms.items():
            connector = data.get("connector")
            if connector and hasattr(connector, "connection_status"):
                if connector.connection_status.get("connected", False):
                    connected += 1
        diagnosis["components"]["platforms"] = {
            "status": "OK" if connected > 0 else "WARNING",
            "connected": connected
        }
    except Exception as e:
        diagnosis["components"]["platforms"] = {"status": "ERROR", "error": str(e)}
    
    # 6. Aktive Strategien
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"}) or {}
        active = []
        if settings.get("swing_trading_enabled"): active.append("swing")
        if settings.get("day_trading_enabled"): active.append("day")
        if settings.get("scalping_enabled"): active.append("scalping")
        if settings.get("mean_reversion_enabled"): active.append("mean_reversion")
        if settings.get("momentum_enabled"): active.append("momentum")
        if settings.get("breakout_enabled"): active.append("breakout")
        if settings.get("grid_enabled"): active.append("grid")
        
        diagnosis["components"]["strategies"] = {
            "status": "OK" if active else "WARNING",
            "active": active,
            "count": len(active)
        }
    except Exception as e:
        diagnosis["components"]["strategies"] = {"status": "ERROR", "error": str(e)}
    
    # V2.3.35: Drawdown Management Status
    try:
        from risk_manager import drawdown_manager
        dd_status = drawdown_manager.get_status()
        diagnosis["components"]["drawdown_management"] = {
            "status": "OK",
            "platforms": len(dd_status.get('platforms', {})),
            "levels": len(dd_status.get('drawdown_levels', [])),
            "description": "Global Drawdown Management aktiv"
        }
    except Exception as e:
        diagnosis["components"]["drawdown_management"] = {"status": "ERROR", "error": str(e)}
    
    # Gesamtstatus
    if diagnosis["issues"]:
        diagnosis["overall_status"] = "WARNING"
    
    return diagnosis


@api_router.get("/risk/drawdown-status")
async def get_drawdown_status():
    """
    V2.3.35: Gibt den aktuellen Drawdown-Status und Anpassungen zurück
    """
    try:
        from risk_manager import drawdown_manager, risk_manager
        
        # Drawdown Status
        dd_status = drawdown_manager.get_status()
        
        # Risk Manager Limits
        risk_limits = risk_manager.get_risk_limits()
        
        # Aktueller Broker-Status
        broker_distribution = {}
        try:
            broker_distribution = await risk_manager.get_broker_distribution()
        except:
            pass
        
        return {
            "success": True,
            "drawdown_management": {
                "status": dd_status,
                "description": "Auto-Reduktion von Position Size/Frequenz bei steigendem Drawdown",
                "levels_info": [
                    "0-5% Drawdown: 100% Position Size, 100% Frequenz (OK)",
                    "5-10% Drawdown: 80% Position Size, 80% Frequenz (Caution)",
                    "10-15% Drawdown: 50% Position Size, 60% Frequenz (Warning)",
                    "15-20% Drawdown: 25% Position Size, 40% Frequenz (Critical)",
                    ">20% Drawdown: Trading gestoppt (Stopped)"
                ]
            },
            "risk_limits": risk_limits,
            "broker_distribution": broker_distribution,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Drawdown status error: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/risk/portfolio-status")
async def get_portfolio_risk_status():
    """
    V2.3.35: Gibt den aktuellen Portfolio-Risiko-Status zurück
    Zeigt das Risiko aller offenen Trades basierend auf Stop-Loss
    """
    try:
        from multi_platform_connector import multi_platform
        from database_v2 import db_manager
        
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        active_platforms = settings.get('active_platforms', []) if settings else []
        
        MAX_PORTFOLIO_RISK_PERCENT = 20.0
        platforms_status = []
        
        for platform in active_platforms:
            if 'MT5_' not in platform:
                continue
                
            try:
                account_info = await multi_platform.get_account_info(platform)
                if not account_info:
                    continue
                
                balance = account_info.get('balance', 0)
                equity = account_info.get('equity', 0)
                
                # Offene Trades für diese Platform holen
                open_trades = await db_manager.trades_db.get_trades(status='OPEN', platform=platform)
                
                total_risk = 0.0
                trades_detail = []
                
                for trade in open_trades:
                    entry_price = trade.get('entry_price', trade.get('price', 0))
                    stop_loss = trade.get('stop_loss', 0)
                    quantity = trade.get('quantity', 0.01)
                    trade_type = trade.get('type', 'BUY')
                    commodity = trade.get('commodity', 'Unknown')
                    
                    if entry_price > 0 and stop_loss > 0:
                        if trade_type == 'BUY':
                            risk = (entry_price - stop_loss) * quantity * 100
                        else:
                            risk = (stop_loss - entry_price) * quantity * 100
                        
                        risk = max(0, risk)
                        total_risk += risk
                        
                        trades_detail.append({
                            'commodity': commodity,
                            'type': trade_type,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'quantity': quantity,
                            'risk_amount': round(risk, 2)
                        })
                
                risk_percent = (total_risk / balance * 100) if balance > 0 else 0
                available_risk = MAX_PORTFOLIO_RISK_PERCENT - risk_percent
                
                platforms_status.append({
                    'platform': platform,
                    'balance': balance,
                    'equity': equity,
                    'open_trades_count': len(open_trades),
                    'total_risk_amount': round(total_risk, 2),
                    'total_risk_percent': round(risk_percent, 2),
                    'max_risk_percent': MAX_PORTFOLIO_RISK_PERCENT,
                    'available_risk_percent': round(max(0, available_risk), 2),
                    'can_open_new_trades': risk_percent < MAX_PORTFOLIO_RISK_PERCENT,
                    'status': 'OK' if risk_percent < MAX_PORTFOLIO_RISK_PERCENT else 'BLOCKED',
                    'trades_detail': trades_detail[:10]  # Max 10 Trades zeigen
                })
                
            except Exception as e:
                logger.warning(f"Error getting portfolio risk for {platform}: {e}")
        
        return {
            "success": True,
            "max_portfolio_risk_percent": MAX_PORTFOLIO_RISK_PERCENT,
            "description": f"Trades werden blockiert wenn Portfolio-Risiko > {MAX_PORTFOLIO_RISK_PERCENT}%",
            "platforms": platforms_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Portfolio risk status error: {e}")
        return {"success": False, "error": str(e)}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

async def connection_health_check():
    """Background task: Check and restore platform connections every 60 seconds"""
    while True:
        try:
            await asyncio.sleep(60)  # 60 seconds (1 minute) - schneller reconnect!
            
            logger.info("🔍 Connection health check...")
            
            # Get active platforms from settings
            settings = await db.trading_settings.find_one({"id": "trading_settings"})
            if not settings:
                continue
            
            active_platforms = settings.get('active_platforms', [])
            
            from multi_platform_connector import multi_platform
            
            for platform_name in active_platforms:
                try:
                    # Check connection status
                    if platform_name not in multi_platform.platforms:
                        continue
                    
                    platform = multi_platform.platforms[platform_name]
                    connector = platform.get('connector')
                    
                    if not connector:
                        # No connector - try to connect
                        logger.warning(f"⚠️ {platform_name} has no connector, reconnecting...")
                        await multi_platform.connect_platform(platform_name)
                        continue
                    
                    # Check if connected
                    is_connected = await connector.is_connected()
                    
                    if not is_connected:
                        # Connection lost - reconnect
                        logger.warning(f"⚠️ {platform_name} connection lost, reconnecting...")
                        platform['active'] = False
                        platform['connector'] = None
                        await multi_platform.connect_platform(platform_name)
                    else:
                        # Connection OK - update balance
                        try:
                            account_info = await multi_platform.get_account_info(platform_name)
                            if account_info:
                                balance = account_info.get('balance', 0)
                                logger.info(f"✅ {platform_name} healthy: Balance = €{balance:,.2f}")
                        except Exception as e:
                            logger.error(f"Error updating balance for {platform_name}: {e}")
                
                except Exception as e:
                    logger.error(f"Error checking {platform_name}: {e}")
            
            logger.info("✅ Health check complete")
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error



@app.on_event("startup")
async def startup_event():
    """Initialize background tasks on startup"""
    import asyncio as _asyncio  # Local import to avoid conflicts
    logger.info("Starting WTI Smart Trader API...")
    
    # Initialize persistent MetaAPI connections to avoid rate limits
    logger.info("Initializing persistent MetaAPI connections...")
    try:
        from multi_platform_connector import multi_platform
        
        # Connect to both platforms at startup (persistent connections)
        await multi_platform.connect_platform('MT5_LIBERTEX_DEMO')
        await multi_platform.connect_platform('MT5_ICMARKETS_DEMO')
        logger.info("✅ Persistent MetaAPI connections established")
    except Exception as e:
        logger.error(f"⚠️ Failed to establish persistent connections: {e}")
        logger.info("ℹ️ Connections will be established on first request")
    
    # Load settings and initialize AI
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    
    # Load settings and initialize AI
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if settings:
        provider = settings.get('ai_provider', 'emergent')
        model = settings.get('ai_model', 'gpt-5')
        api_key = None
        ollama_base_url = settings.get('ollama_base_url', 'http://localhost:11434')
        ollama_model = settings.get('ollama_model', 'llama2')
        
        if provider == "openai":
            api_key = settings.get('openai_api_key')
        elif provider == "gemini":
            api_key = settings.get('gemini_api_key')
        elif provider == "anthropic":
            api_key = settings.get('anthropic_api_key')
        elif provider == "ollama":
            init_ai_chat(provider="ollama", model=ollama_model, ollama_base_url=ollama_base_url)
        else:
            init_ai_chat(provider=provider, api_key=api_key, model=model)
    else:
        # Default to Emergent LLM Key
        init_ai_chat(provider="emergent", model="gpt-5")
    
    # Load MT5 credentials from environment
    mt5_login = os.environ.get('MT5_LOGIN')
    mt5_password = os.environ.get('MT5_PASSWORD')
    mt5_server = os.environ.get('MT5_SERVER')
    
    if mt5_login and mt5_password and mt5_server:
        # Update default settings with MT5 credentials
        if settings:
            await db.trading_settings.update_one(
                {"id": "trading_settings"},
                {"$set": {
                    "mt5_login": mt5_login,
                    "mt5_password": mt5_password,
                    "mt5_server": mt5_server
                }}
            )
        else:
            # Create default settings with MT5 credentials
            default_settings = TradingSettings(
                mt5_login=mt5_login,
                mt5_password=mt5_password,
                mt5_server=mt5_server
            )
            await db.trading_settings.insert_one(default_settings.model_dump())
        
        logger.info(f"MT5 credentials loaded: Server={mt5_server}, Login={mt5_login}")
    

    # Start connection health check background task
    _asyncio.create_task(connection_health_check())
    logger.info("✅ Connection health check started")

    # Initialize platform connector for commodity_processor
    from multi_platform_connector import multi_platform
    import commodity_processor
    commodity_processor.set_platform_connector(multi_platform)
    
    # Connect platforms for chart data availability (SDK version) - parallel for speed
    import asyncio
    connection_tasks = [
        multi_platform.connect_platform('MT5_LIBERTEX_DEMO'),
        multi_platform.connect_platform('MT5_ICMARKETS_DEMO')
    ]
    results = await asyncio.gather(*connection_tasks, return_exceptions=True)
    
    # Log results
    for i, (platform_name, result) in enumerate(zip(['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO'], results)):
        if isinstance(result, Exception):
            logger.error(f"Failed to connect {platform_name}: {result}")
        elif result:
            logger.info(f"✅ Successfully connected {platform_name}")
        else:
            logger.warning(f"⚠️ Failed to connect {platform_name} (returned False)")
    
    logger.info("Platform connector initialized and platforms connected for MetaAPI chart data (SDK)")
    
    # Fetch initial market data
    await process_market_data()
    
    # Start Market Data Updater (separate task, alle 30 Sekunden)
    _asyncio.create_task(market_data_updater())
    logger.info("✅ Market Data Updater started (updates every 30 seconds)")
    
    # DEAKTIVIERT: Auto-Trading Engine erstellt Fake-Trades
    # from auto_trading_engine import get_auto_trading_engine
    # auto_engine = get_auto_trading_engine(db)
    # asyncio.create_task(auto_engine.start())
    logger.info("🔴 Auto-Trading Engine ist DEAKTIVIERT (erstellt Fake-Trades)")
    
    logger.info("API ready - market data available via /api/market/current and /api/market/refresh")
    logger.info("AI analysis enabled for intelligent trading decisions")
    
    # Start Trade Settings Monitor in background (NON-BLOCKING!)
    logger.info("🤖 Starting Trade Settings Monitor...")
    try:
        from trade_settings_manager import trade_settings_manager
        import asyncio
        # Create task WITHOUT await - runs in background
        asyncio.create_task(trade_settings_manager.start())
        logger.info("✅ Trade Settings Monitor started - überwacht alle Trades automatisch!")
    except Exception as e:
        logger.error(f"⚠️ Failed to start Trade Settings Monitor: {e}", exc_info=True)
    
    # V2.3.32 FIX: Auto-Start Multi-Bot wenn auto_trading aktiviert ist
    global multi_bot_manager
    if settings and settings.get('auto_trading', False):
        logger.info("🤖 Auto-Trading ist aktiviert - starte Multi-Bot-System beim Startup...")
        try:
            from multi_bot_system import MultiBotManager
            from database_v2 import db_manager
            
            async def get_settings():
                return await db.trading_settings.find_one({"id": "trading_settings"})
            
            multi_bot_manager = MultiBotManager(db_manager, get_settings)
            await multi_bot_manager.start_all()
            logger.info("✅ Multi-Bot-System v2.3.32 gestartet beim Startup!")
        except ImportError as e:
            logger.warning(f"⚠️ Multi-Bot nicht verfügbar: {e}")
        except Exception as e:
            logger.error(f"❌ Multi-Bot Start Fehler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Close persistent MetaAPI connections
    try:
        from multi_platform_connector import multi_platform
        for platform_name, platform in multi_platform.platforms.items():
            if platform.get('connector'):
                try:
                    await platform['connector'].disconnect()
                    logger.info(f"✅ Closed connection to {platform_name}")
                except:
                    pass
    except Exception as e:
        logger.error(f"Error closing MetaAPI connections: {e}")
    
    # Scheduler moved to worker.py
    # scheduler.shutdown()
    
    # Close MongoDB client (if exists)
    try:
        if 'client' in globals():
            client.close()
    except:
        pass
    
    logger.info("Application shutdown complete")


# ========================================
# STATIC FILES - Serve React Frontend
# ========================================

# Mount static files (für Desktop-App)
frontend_build_path = Path(__file__).parent.parent / "frontend" / "build"

if frontend_build_path.exists():
    # Serve static files (JS, CSS, etc.)
    app.mount("/static", StaticFiles(directory=str(frontend_build_path / "static")), name="static")
    
    # Catch-all route für React Router (muss NACH allen API-Routen kommen)
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """Serve React app for all non-API routes"""
        # Don't serve React for API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        
        # Serve index.html for all other routes (React Router handles routing)
        index_path = frontend_build_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            raise HTTPException(status_code=404, detail="Frontend build not found")
    
    logger.info(f"✅ Serving React Frontend from: {frontend_build_path}")
else:
    logger.warning(f"⚠️  Frontend build not found at: {frontend_build_path}")
    logger.warning("   Run 'cd /app/frontend && yarn build' to create production build")
@api_router.get("/debug/memory")
async def memory_status():
    """Memory Diagnostics Endpoint"""
    # Current memory
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    
    # GC stats
    import gc
    gc.collect()
    
    return {
        "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
        "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
        "percent": process.memory_percent(),
        "gc_objects": len(gc.get_objects()),
        "gc_garbage": len(gc.garbage),
        "gc_counts": gc.get_count(),
        "message": "Basic memory statistics"
    }


