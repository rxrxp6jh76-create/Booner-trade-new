# 🤖 Booner Trade - Technical System Summary V2.6.1
**For External AI Architect Review**
*Generated: December 2025*

---

## 📋 Table of Contents
1. [System Architecture](#1-system-architecture)
2. [Logic & Data Flow](#2-logic--data-flow)
3. [4-Pillar Confidence Score](#3-4-pillar-confidence-score)
4. [Integrations](#4-integrations)
5. [Database Schema](#5-database-schema)
6. [AI Implementation](#6-ai-implementation)
7. [Open Tasks & Known Issues](#7-open-tasks--known-issues)

---

## 1. System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │ Dashboard   │ │ AIChat     │ │ Settings   │ │ Backtesting   │  │
│  │ (Main UI)   │ │ Component  │ │ Dialog     │ │ Panel         │  │
│  └──────┬──────┘ └──────┬─────┘ └──────┬─────┘ └───────┬───────┘  │
│         │               │              │               │           │
│         └───────────────┴──────────────┴───────────────┘           │
│                              │ REST API (Axios)                     │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     server.py (Main Router)                    │  │
│  │  - 100+ REST Endpoints                                         │  │
│  │  - WebSocket for real-time ticks                               │  │
│  │  - Background workers (trading loop)                           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│  ┌────────────────┬───────────┴───────────┬─────────────────────┐   │
│  │                │                       │                     │   │
│  ▼                ▼                       ▼                     ▼   │
│  ┌──────────────────┐  ┌───────────────────────┐  ┌────────────────┐│
│  │ multi_bot_system │  │ autonomous_trading    │  │ ai_chat_service││
│  │ .py              │  │ _intelligence.py      │  │ .py            ││
│  │                  │  │                       │  │                ││
│  │ - TradeBot       │  │ - 4-Pillar Score      │  │ - LLM Chat     ││
│  │ - SignalBot      │  │ - Strategy Profiles   │  │ - Market       ││
│  │ - MarketBot      │  │ - Risk Circuits       │  │   Analysis     ││
│  │ - Lot Sizing     │  │ - Mean Reversion      │  │                ││
│  └──────────────────┘  └───────────────────────┘  └────────────────┘│
│                               │                                      │
│  ┌────────────────────────────┴──────────────────────────────────┐  │
│  │                    DATA SERVICES                               │  │
│  ├─────────────────┬─────────────────┬───────────────────────────┤  │
│  │ hybrid_data_    │ cot_data_       │ metaapi_sdk_              │  │
│  │ fetcher.py      │ service.py      │ connector.py              │  │
│  │ (Yahoo/MetaAPI) │ (CFTC COT)      │ (Live Trading)            │  │
│  └─────────────────┴─────────────────┴───────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        DATABASE (SQLite)                             │
│  trades.db: trades, trading_settings, market_data, api_keys         │
└──────────────────────────────────────────────────────────────────────┘
```

### Frontend Structure (React + Vite)
```
/app/frontend/src/
├── App.js                      # Main router
├── pages/
│   └── Dashboard.jsx           # Main trading dashboard (~4000 lines)
│       ├── Asset Cards         # 16 tradeable assets
│       ├── Ampelsystem        # Traffic light confidence display
│       ├── Trade Tables       # Open/Closed trades
│       └── Charts             # TradingView integration
├── components/
│   ├── AIChat.jsx             # AI chat interface
│   ├── SettingsDialog.jsx     # 3-tier trading mode settings
│   ├── BacktestingPanel.jsx   # Strategy backtesting UI
│   ├── RiskDashboard.jsx      # Risk metrics display
│   └── ui/                    # shadcn/ui components
└── lib/
    └── utils.js               # Utility functions
```

### Backend Structure (FastAPI + Python 3.11)
```
/app/backend/
├── server.py                          # Main FastAPI app (~6000 lines)
├── autonomous_trading_intelligence.py # AI trading core (~2000 lines)
├── multi_bot_system.py                # Trade execution (~2000 lines)
├── ai_chat_service.py                 # LLM integration
├── hybrid_data_fetcher.py             # Multi-source data
├── cot_data_service.py                # COT data integration
├── metaapi_sdk_connector.py           # MetaAPI SDK
├── database.py                        # SQLite async wrapper
├── enhanced_self_learning.py          # Pattern learning
├── risk_manager.py                    # Risk calculations
└── commodity_processor.py             # Asset definitions
```

---

## 2. Logic & Data Flow

### Trading Pipeline

```
1. DATA COLLECTION (Every 30 seconds)
   ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
   │  Yahoo Finance │     │   MetaAPI      │     │   CFTC/COT     │
   │  (Prices)      │ ──► │   (Live Ticks) │ ──► │   (Sentiment)  │
   └────────────────┘     └────────────────┘     └────────────────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
                                  ▼
2. MARKET STATE DETECTION
   ┌─────────────────────────────────────────────────────────────┐
   │  detect_market_state()                                      │
   │  ├── Calculate ADX (Trend Strength)                        │
   │  ├── Calculate ATR (Volatility)                            │
   │  ├── Determine Trend Direction (EMA 20/50/200)             │
   │  └── Classify: STRONG_UPTREND | RANGE | HIGH_VOLATILITY    │
   └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
3. STRATEGY SELECTION
   ┌─────────────────────────────────────────────────────────────┐
   │  Select optimal strategy based on market state:             │
   │  ├── STRONG_TREND  → Swing Trading, Momentum               │
   │  ├── RANGE         → Mean Reversion, Grid                  │
   │  ├── HIGH_VOLATILITY → Scalping, Breakout                  │
   │  └── CHAOS         → No trading recommended                │
   └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
4. CONFIDENCE CALCULATION (4-Pillar Model)
   ┌─────────────────────────────────────────────────────────────┐
   │  calculate_universal_confidence()                           │
   │  Returns: UniversalConfidenceScore (0-100%)                │
   │  Details: See Section 3                                    │
   └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
5. TRADING MODE THRESHOLD CHECK
   ┌─────────────────────────────────────────────────────────────┐
   │  Trading Mode       │ Min Confidence │ Risk %              │
   │  ─────────────────────────────────────────────────────────  │
   │  Conservative       │ 75%            │ 0.5% - 1.0%         │
   │  Neutral            │ 68%            │ 0.5% - 1.5%         │
   │  Aggressive         │ 60%            │ 1.0% - 2.0%         │
   └─────────────────────────────────────────────────────────────┘
                                  │
                         ┌───────┴───────┐
                    PASS │               │ FAIL
                         ▼               ▼
6. TRADE EXECUTION          TRADE BLOCKED
   ┌────────────────┐       ┌────────────────┐
   │ Calculate Lot  │       │ Log rejection  │
   │ Send to MT5    │       │ reasons        │
   │ Store in DB    │       └────────────────┘
   └────────────────┘
```

---

## 3. 4-Pillar Confidence Score

### Overview
The confidence score is calculated in `autonomous_trading_intelligence.py::calculate_universal_confidence()`.
Each strategy has different pillar weightings to optimize for its specific trading style.

### Pillar Definitions

#### Pillar 1: Base Signal (max: strategy-dependent)
```python
# Evaluates: Strategy-Market fit + Indicator Confluence

Scoring Logic:
├── Strategy OPTIMAL for market:     +50% of pillar max
├── Strategy acceptable:             +30% of pillar max
├── 5+ indicators confirm:           +62.5% of pillar max
├── 3-4 indicators confirm:          +45% of pillar max
├── 2 indicators confirm:            +30% of pillar max
└── Strategy NOT suitable:           -12.5% of pillar max
```

#### Pillar 2: Trend Confluence (max: strategy-dependent)
```python
# Evaluates: Multi-timeframe alignment + Mean Reversion Correction (V2.6.1)

Scoring Logic:
├── D1 Trend aligned with signal:    +40% of pillar max
├── H4 Trend aligned:                +40% of pillar max
├── H1 Trend aligned:                +20% of pillar max
├── All 3 timeframes aligned:        BONUS
└── No timeframes aligned (conservative): PENALTY

# V2.6.1 Mean Reversion Correction:
├── Price 3-5% from EMA200:          -15% trend score
├── Price 5-8% from EMA200:          -30% trend score
├── Price >8% from EMA200:           -50% trend score
└── Signal against overextension:    +20% BONUS (Mean Rev Trade)
```

#### Pillar 3: Volatility (max: strategy-dependent)
```python
# Evaluates: ATR normalization + Volume confirmation

Scoring Logic:
├── Optimal volatility (0.8-1.5x):   +75% of pillar max
├── Acceptable (0.5-2.0x):           +50% of pillar max
├── Extreme (>2.5x):                 -25% of pillar max
└── Volume spike confirms signal:    +25% of pillar max
```

#### Pillar 4: Sentiment (max: strategy-dependent)
```python
# Evaluates: COT data (for commodities) or News sentiment

For Commodities (Gold, Oil, etc.):
├── COT Speculators aligned:         +40% of pillar max
├── COT Weekly momentum aligned:     +20% of pillar max
└── COT against signal:              PENALTY

For Forex/Crypto:
├── News supports signal:            +67% of pillar max
├── Neutral news:                    +33% of pillar max
└── News against signal:             -33% of pillar max

Global:
└── High-impact news pending:        -100% (full pillar penalty)
```

### Strategy-Specific Weights

| Strategy | Base Signal | Trend | Volatility | Sentiment | Threshold |
|----------|-------------|-------|------------|-----------|-----------|
| **Swing** | 30 | 40 | 10 | 20 | 75% |
| **Day Trading** | 35 | 25 | 20 | 20 | 70% |
| **Scalping** | 40 | 10 | 40 | 10 | 60% |
| **Momentum** | 20 | 30 | 40 | 10 | 65% |
| **Mean Reversion** | 50 | 10 | 30 | 10 | 60% |
| **Breakout** | 30 | 15 | 45 | 10 | 72% |
| **Grid** | 10 | 50* | 30 | 10 | 0% |

*Grid Trading: Trend confluence is scored NEGATIVELY (requires sideways market)

### Dynamic Lot Sizing Formula

```python
# In multi_bot_system.py::_calculate_lot_size_v2()

1. Determine Risk Level based on Trading Mode + Confidence:
   
   RISK_LEVELS = {
       'conservative': {
           'min_confidence': 75,    # Below this = no trade
           'low_risk_max': 80,      # 75-80% = low risk
           'medium_risk_max': 88,   # 80-88% = medium risk
           'low_risk': 0.005,       # 0.5% of balance
           'medium_risk': 0.0075,   # 0.75%
           'high_risk': 0.01,       # 1.0%
           'max_lot': 1.5
       },
       'neutral': {
           'min_confidence': 68,
           'low_risk': 0.005,       # 0.5%
           'medium_risk': 0.01,     # 1.0%
           'high_risk': 0.015,      # 1.5%
           'max_lot': 2.0
       },
       'aggressive': {
           'min_confidence': 60,
           'low_risk': 0.01,        # 1.0%
           'medium_risk': 0.015,    # 1.5%
           'high_risk': 0.02,       # 2.0%
           'max_lot': 2.5
       }
   }

2. Calculate Lot Size:
   risk_amount = balance * risk_percent
   lot_size = risk_amount / (stop_loss_pips * tick_value)
   lot_size = clamp(lot_size, MIN_LOT=0.01, MAX_LOT=mode.max_lot)
```

---

## 4. Integrations

### Market Data Sources

| Source | Purpose | Implementation | Rate Limit |
|--------|---------|----------------|------------|
| **MetaAPI** | Live tick data, trade execution | `metaapi_sdk_connector.py` | Account-based |
| **Yahoo Finance** | Fallback prices, historical data | `hybrid_data_fetcher.py` via `yfinance` | ~2000/hour |
| **CFTC/COT** | Commitment of Traders sentiment | `cot_data_service.py` | Weekly updates |

### Trading Platforms

| Platform | Connection | Symbols | Status |
|----------|------------|---------|--------|
| **MT5 Libertex Demo** | MetaAPI SDK | XAUUSD, XAGUSD, CL, etc. | Active |
| **MT5 ICMarkets Demo** | MetaAPI SDK | XAUUSD, WTI_F6, etc. | Active |
| **Bitpanda** | REST API | Limited support | Legacy |

### AI/LLM Providers

| Provider | Models | Purpose | Config Location |
|----------|--------|---------|-----------------|
| **Emergent** | GPT-5 | Default AI analysis | `ai_provider: "emergent"` |
| **OpenAI** | GPT-4o, GPT-4 | Analysis, chat | Requires API key |
| **Anthropic** | Claude 3.5 | Analysis | Requires API key |
| **Gemini** | Gemini Pro | Analysis | Requires API key |
| **Ollama** | llama3, mistral | Local inference | `ollama_base_url` |

### Data Flow into Database

```
External APIs                 Processing                    Storage
─────────────                 ──────────                    ───────
Yahoo Finance ──┐
                ├──► hybrid_data_fetcher.py ──► market_data table
MetaAPI ────────┘                              (price, volume, indicators)

CFTC API ──────────► cot_data_service.py ──► In-memory cache
                                              (weekly refresh)

NewsAPI ───────────► market_analysis.py ──► In-memory
                                            (real-time sentiment)

Trade Execution ───► multi_bot_system.py ──► trades table
                                             (entry, exit, P/L)
```

---

## 5. Database Schema

### SQLite Database: `trades.db`

#### Table: `trades`
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,              -- UUID
    timestamp TEXT NOT NULL,          -- ISO 8601
    commodity TEXT NOT NULL,          -- e.g., 'GOLD', 'EURUSD'
    type TEXT NOT NULL,               -- 'BUY' | 'SELL'
    price REAL NOT NULL,              -- Entry price
    quantity REAL DEFAULT 1.0,        -- Lot size
    status TEXT DEFAULT 'OPEN',       -- 'OPEN' | 'CLOSED'
    platform TEXT DEFAULT 'MT5_LIBERTEX',
    entry_price REAL NOT NULL,
    exit_price REAL,                  -- NULL until closed
    profit_loss REAL,                 -- Calculated on close
    stop_loss REAL,
    take_profit REAL,
    strategy_signal TEXT,             -- Signal reason
    strategy TEXT,                    -- 'swing', 'day', 'scalping', etc.
    closed_at TEXT,
    mt5_ticket TEXT,                  -- Broker ticket ID
    opened_at TEXT,
    opened_by TEXT,                   -- 'TradeBot' | 'Manual'
    closed_by TEXT,
    close_reason TEXT                 -- 'TAKE_PROFIT' | 'STOP_LOSS' | etc.
);
```

#### Table: `trading_settings`
```sql
CREATE TABLE trading_settings (
    id TEXT PRIMARY KEY,              -- Always 'trading_settings'
    data TEXT NOT NULL,               -- JSON blob
    updated_at TEXT NOT NULL
);

-- JSON Structure (data column):
{
    "active_platforms": ["MT5_LIBERTEX_DEMO", "MT5_ICMARKETS_DEMO"],
    "auto_trading": true,
    "trading_mode": "neutral",        -- 'conservative' | 'neutral' | 'aggressive'
    "ai_provider": "emergent",
    "enabled_commodities": ["GOLD", "SILVER", ...],
    "stop_loss_percent": 2.0,
    "take_profit_percent": 4.0,
    "max_portfolio_risk_percent": 20.0,
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "llama3:latest"
}
```

#### Table: `market_data`
```sql
CREATE TABLE market_data (
    commodity TEXT PRIMARY KEY,       -- e.g., 'GOLD'
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    volume REAL,
    sma_20 REAL,
    ema_20 REAL,
    rsi REAL,
    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,
    trend TEXT,                       -- 'UP' | 'DOWN' | 'NEUTRAL'
    signal TEXT,                      -- 'BUY' | 'SELL' | 'HOLD'
    data_source TEXT                  -- 'metaapi' | 'yfinance'
);
```

#### Table: `market_data_history`
```sql
CREATE TABLE market_data_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    volume REAL,
    sma_20 REAL,
    ema_20 REAL,
    rsi REAL,
    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,
    trend TEXT,
    signal TEXT
);
-- Index: CREATE INDEX idx_history_commodity_time ON market_data_history(commodity_id, timestamp);
```

#### Table: `api_keys`
```sql
CREATE TABLE api_keys (
    id TEXT PRIMARY KEY,
    metaapi_token TEXT,
    metaapi_account_id TEXT,
    metaapi_icmarkets_account_id TEXT,
    bitpanda_api_key TEXT,
    bitpanda_email TEXT,
    finnhub_api_key TEXT,
    updated_at TEXT NOT NULL
);
```

---

## 6. AI Implementation

### Ollama Integration

#### Configuration
```python
# In TradingSettings model (server.py):
ai_provider: Literal["emergent", "openai", "gemini", "anthropic", "ollama"] = "emergent"
ollama_base_url: Optional[str] = "http://127.0.0.1:11434"
ollama_model: Optional[str] = "llama3:latest"
```

#### Implementation (ai_chat_service.py)
```python
class OllamaChat:
    def __init__(self, base_url="http://localhost:11434", model="llama3:latest"):
        self.base_url = base_url
        self.model = model
    
    async def chat(self, message: str) -> str:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_message},
                    {"role": "user", "content": message}
                ],
                "stream": False
            }
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['message']['content']
```

#### System Prompt Template
```python
AI_SYSTEM_MESSAGE = """Du bist ein erfahrener Trading-Analyst für Rohstoffe und Forex.
Deine Aufgabe ist es, Marktdaten zu analysieren und präzise Handelssignale zu geben.

Analysiere folgende Aspekte:
1. Technische Indikatoren (RSI, MACD, Moving Averages)
2. Markttrends und Momentum
3. Unterstützungs- und Widerstandsniveaus
4. Risiko-Ertrags-Verhältnis

Antworte immer auf Deutsch und gib konkrete Empfehlungen."""
```

#### Supported Models
| Model | Provider | Use Case |
|-------|----------|----------|
| `llama3:latest` | Ollama | General analysis (default) |
| `mistral:latest` | Ollama | Fast inference |
| `codellama:latest` | Ollama | Technical analysis |
| `gpt-5` | Emergent/OpenAI | Premium analysis |
| `claude-3-sonnet` | Anthropic | Detailed explanations |

---

## 7. Open Tasks & Known Issues

### 🔴 High Priority (P0)

| Issue | Description | File | Status |
|-------|-------------|------|--------|
| Mode-dependent lot sizing verification | Verify lot sizes change correctly per trading mode | `multi_bot_system.py` | ✅ IMPLEMENTED, needs user verification |

### 🟠 Medium Priority (P1)

| Issue | Description | File | Status |
|-------|-------------|------|--------|
| "Unknown" strategy display | Closed trades show strategy as "unknown" in UI | `Dashboard.jsx` | NOT STARTED |
| Backend settings cleanup | Remove obsolete settings from backend code | `server.py` | NOT STARTED |

### 🟡 Low Priority (P2)

| Issue | Description | File | Status |
|-------|-------------|------|--------|
| AI Chat microphone bug | Reports "no internet connection" when clicked | `AIChat.jsx` | NOT STARTED |

### 📋 Backlog / Future Tasks

| Task | Description | Complexity |
|------|-------------|------------|
| Backtesting UI enhancement | Simulate multi-strategy AI decisions | Medium |
| Mobile app version | React Native / Flutter implementation | High |
| Full backend settings audit | Remove all dead code for obsolete settings | Low |

### ✅ Recently Completed (V2.6.x)

- [x] Multi-Strategy AI Engine (7 strategies)
- [x] 3-Tier Trading Mode (Conservative/Neutral/Aggressive)
- [x] Dynamic & Mode-Aware Lot Sizing
- [x] Mean Reversion Correction in Trend Pillar
- [x] Copper (COPPER) asset integration
- [x] macOS crash recovery scripts
- [x] UI/AI Confidence Sync (Ampelsystem fix)
- [x] COT Data Integration

---

## 📊 System Metrics

- **Total Backend Lines**: ~15,000+ (Python)
- **Total Frontend Lines**: ~5,000+ (JSX)
- **API Endpoints**: 100+
- **Tradeable Assets**: 16
- **Trading Strategies**: 7
- **Supported LLM Providers**: 5

---

*Document generated for external AI architect review. For questions, refer to the codebase or contact the development team.*
