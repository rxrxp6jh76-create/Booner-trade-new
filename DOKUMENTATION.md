# 📚 Booner Trade - Vollständige Dokumentation

**Version:** 2.3.32  
**Stand:** 17. Dezember 2025

---

## 📖 Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Architektur](#architektur)
3. [Features](#features)
4. [Trading-Strategien](#trading-strategien)
5. [API Referenz](#api-referenz)
6. [Datenbank-Schema](#datenbank-schema)
7. [Konfiguration](#konfiguration)
8. [Fehlerbehebung](#fehlerbehebung)

---

## 🎯 Überblick

Booner Trade ist eine professionelle Trading-Anwendung für den automatisierten und manuellen Handel mit Rohstoffen, Forex und Kryptowährungen. Die App verbindet sich mit MetaTrader 5 über MetaAPI und bietet KI-gestützte Handelsanalysen.

### Hauptfunktionen:
- 📊 **Live-Marktdaten** für 15+ Rohstoffe und Währungspaare
- 🤖 **KI-Trading-Bot** mit Multi-Bot-Architektur
- 📈 **6 Trading-Strategien** (Day, Swing, Scalping, Mean Reversion, Momentum, Breakout)
- 🔌 **MetaTrader 5 Integration** über MetaAPI
- 📱 **Backtesting** für Strategie-Optimierung
- 🛡️ **Risiko-Management** mit Portfolio-Schutz

### Unterstützte Broker:
- Libertex (Demo & Real)
- ICMarkets (Demo & Real)
- Bitpanda (geplant)

---

## 🏗️ Architektur

### Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| **Frontend** | React 18, Tailwind CSS, Shadcn UI |
| **Backend** | FastAPI (Python 3.11), Uvicorn |
| **Datenbank** | SQLite (Multi-DB: 3 separate Dateien) |
| **Trading API** | MetaAPI für MetaTrader 5 |
| **KI-Provider** | OpenAI, Google Gemini, Anthropic Claude, Ollama |
| **Marktdaten** | Yahoo Finance, Alpha Vantage |

### Ordnerstruktur

```
/app/
├── backend/
│   ├── server.py                 # FastAPI Server + alle API Routes
│   ├── database_v2.py            # Multi-Database Manager
│   ├── database.py               # Kompatibilitäts-Wrapper
│   ├── multi_bot_system.py       # 3 spezialisierte Bots
│   ├── ai_trading_bot.py         # Legacy Bot + Hilfsfunktionen
│   ├── risk_manager.py           # Portfolio-Risiko-Verwaltung
│   ├── backtesting_engine.py     # Backtesting-Engine
│   ├── metaapi_sdk_connector.py  # MT5 Verbindung
│   ├── commodity_processor.py    # Marktdaten-Verarbeitung
│   ├── strategies/               # Trading-Strategien
│   │   ├── __init__.py
│   │   ├── mean_reversion.py     # Mean Reversion Strategie
│   │   ├── momentum_trading.py   # Momentum Strategie
│   │   ├── breakout_strategy.py  # Breakout Strategie
│   │   └── grid_trading.py       # Grid Trading Strategie
│   ├── .env                      # Umgebungsvariablen
│   └── requirements.txt          # Python Dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.js                # Hauptapp mit ErrorBoundary
│   │   ├── pages/
│   │   │   └── Dashboard.jsx     # Haupt-Dashboard
│   │   └── components/
│   │       ├── AIChat.jsx        # KI-Chat mit Spracherkennung
│   │       ├── BacktestingPanel.jsx
│   │       ├── RiskDashboard.jsx
│   │       ├── SettingsDialog.jsx
│   │       ├── TradesTable.jsx
│   │       ├── PriceChart.jsx
│   │       ├── IndicatorsPanel.jsx
│   │       └── ui/               # Shadcn UI Komponenten
│   ├── .env                      # Frontend Umgebungsvariablen
│   └── package.json
│
├── electron-app/                 # Desktop-App Wrapper
│   ├── main.js
│   ├── preload.js
│   └── package.json
│
└── Dokumentation/
    ├── DOKUMENTATION.md          # Diese Datei
    ├── RELEASE-NOTES-V2.3.32.md
    ├── TRADING-STRATEGIES-GUIDE.md
    └── SCHNELLSTART.md
```

### Multi-Bot-System

Das Backend verwendet 3 spezialisierte Bots für optimale Performance:

```
┌─────────────────────────────────────────────────────────────┐
│                    MultiBotSystem                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   MarketBot     │   SignalBot     │      TradeBot           │
│   (8 Sek)       │   (20 Sek)      │      (12 Sek)           │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • Preise holen  │ • Signale       │ • Trades ausführen      │
│ • Indikatoren   │   analysieren   │ • Positionen überwachen │
│ • DB speichern  │ • News checken  │ • SL/TP prüfen          │
│                 │ • Strategien    │ • Auto-Close            │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Multi-Database-Architektur

```
┌──────────────────────────────────────────────────────────────┐
│                    Datenbank-Aufteilung                       │
├──────────────────┬──────────────────┬────────────────────────┤
│   settings.db    │    trades.db     │    market_data.db      │
├──────────────────┼──────────────────┼────────────────────────┤
│ • trading_settings│ • trades        │ • market_data          │
│ • api_keys       │ • closed_trades  │ • market_data_history  │
│                  │ • ticket_strategy│                        │
│                  │   _map           │                        │
├──────────────────┼──────────────────┼────────────────────────┤
│ Selten           │ Mittel           │ Sehr häufig            │
│ (bei Änderungen) │ (Trade-Aktivität)│ (alle 5-15 Sek)        │
└──────────────────┴──────────────────┴────────────────────────┘
```

---

## ✨ Features

### 1. Dashboard

Das Haupt-Dashboard zeigt:
- **Broker-Karten:** Balance, Margin, Profit/Loss pro Broker
- **Markt-Übersicht:** Live-Preise für alle aktiven Commodities
- **Trades-Tab:** Offene und geschlossene Trades
- **Charts-Tab:** Interaktive Preischarts mit Indikatoren
- **KI-Tab:** Chat mit KI für Marktanalysen
- **Backtesting-Tab:** Strategie-Backtesting
- **Risiko-Tab:** Portfolio-Risiko-Übersicht

### 2. KI-Trading-Bot

Der Bot kann:
- Marktdaten analysieren
- Trading-Signale generieren
- Trades automatisch öffnen/schließen
- News in die Analyse einbeziehen
- Verschiedene Strategien anwenden

**KI-Provider:**
- OpenAI (GPT-4, GPT-4o)
- Google Gemini
- Anthropic Claude
- Ollama (lokale Modelle)

### 3. Risiko-Management

- **Max Portfolio-Risiko:** 20% pro Broker
- **Max Drawdown:** 15%
- **Broker-Balancing:** Gleichmäßige Verteilung
- **Position-Limits:** Konfigurierbar pro Strategie

### 4. Backtesting

Testen Sie Strategien mit historischen Daten:
- Zeitraum wählbar (1 Woche - 2 Jahre)
- Alle 6 Strategien verfügbar
- Metriken: Win Rate, Sharpe Ratio, Profit Factor, Max Drawdown
- Equity Curve Visualisierung

---

## 📈 Trading-Strategien

### 1. Day Trading
- **Haltedauer:** Minuten bis Stunden
- **Indikatoren:** RSI, MACD, SMA/EMA
- **SL/TP Ratio:** 1:1.5

### 2. Swing Trading
- **Haltedauer:** Tage bis Wochen
- **Indikatoren:** RSI, Bollinger Bands, Trend
- **SL/TP Ratio:** 1:2

### 3. Scalping
- **Haltedauer:** Sekunden bis Minuten
- **Indikatoren:** RSI (schnell), Volumen
- **SL/TP Ratio:** 1:1

### 4. Mean Reversion
- **Konzept:** Preise kehren zum Mittelwert zurück
- **Indikatoren:** RSI Extreme, Bollinger Band Touch
- **Entry:** Bei RSI < 30 (überverkauft) oder RSI > 70 (überkauft)

### 5. Momentum
- **Konzept:** Trends fortsetzen sich
- **Indikatoren:** MACD Crossover, ADX, Volumen
- **Entry:** Bei starkem Momentum in Trendrichtung

### 6. Breakout
- **Konzept:** Ausbruch aus Range/Konsolidierung
- **Indikatoren:** Bollinger Band Breakout, Volumen Spike
- **Entry:** Bei Schlusskurs über/unter Bollinger Band

---

## 🔌 API Referenz

### Basis-URL
```
https://[your-domain]/api
```

### Endpunkte

#### Settings
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/settings` | Alle Settings abrufen |
| POST | `/api/settings` | Settings aktualisieren |
| GET | `/api/settings/api-keys` | API Keys abrufen |
| POST | `/api/settings/api-keys` | API Keys speichern |

#### Trades
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/trades/list` | Alle Trades abrufen |
| GET | `/api/trades/list?status=OPEN` | Nur offene Trades |
| POST | `/api/trades/close` | Trade schließen |
| GET | `/api/trades/stats` | Trade-Statistiken |
| DELETE | `/api/trades/closed/all` | Alle geschlossenen Trades löschen |

#### Marktdaten
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/commodities` | Alle Commodities |
| GET | `/api/market/current` | Aktuelle Marktdaten |
| GET | `/api/market/history` | Historische Snapshots |
| GET | `/api/market/ohlcv/{commodity}` | OHLCV Daten für Charts |

#### Plattformen
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/platforms` | Verfügbare Plattformen |
| GET | `/api/platforms/{platform}/account` | Account-Info |
| GET | `/api/platforms/{platform}/positions` | Offene Positionen |

#### Bot & Analyse
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/bot/status` | Multi-Bot Status |
| POST | `/api/bot/start` | Bot starten |
| POST | `/api/bot/stop` | Bot stoppen |
| POST | `/api/analyze/{commodity}` | KI-Analyse für Commodity |
| POST | `/api/chat` | KI-Chat Nachricht |

#### Backtesting
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | `/api/backtest/run` | Backtest starten |
| GET | `/api/backtest/results` | Backtest-Ergebnisse |

#### Risiko
| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/risk/status` | Risiko-Status |
| GET | `/api/risk/limits` | Risiko-Limits |

---

## 💾 Datenbank-Schema

### settings.db

#### trading_settings
```sql
CREATE TABLE trading_settings (
    id TEXT PRIMARY KEY,
    data TEXT,  -- JSON mit allen Settings
    updated_at TEXT
);
```

#### api_keys
```sql
CREATE TABLE api_keys (
    id TEXT PRIMARY KEY,
    data TEXT,  -- JSON mit verschlüsselten Keys
    updated_at TEXT
);
```

### trades.db

#### trades
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    mt5_ticket TEXT,
    symbol TEXT,
    commodity TEXT,
    type TEXT,  -- BUY/SELL
    entry_price REAL,
    quantity REAL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT,  -- OPEN/CLOSED
    strategy TEXT,
    platform TEXT,
    profit_loss REAL,
    timestamp TEXT,
    closed_at TEXT
);
```

#### ticket_strategy_map
```sql
CREATE TABLE ticket_strategy_map (
    ticket_id TEXT PRIMARY KEY,
    strategy TEXT,
    platform TEXT,
    created_at TEXT
);
```

### market_data.db

#### market_data
```sql
CREATE TABLE market_data (
    commodity TEXT PRIMARY KEY,
    timestamp TEXT,
    price REAL,
    volume REAL,
    sma_20 REAL,
    ema_20 REAL,
    rsi REAL,
    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,
    trend TEXT,
    signal TEXT,
    data_source TEXT
);
```

---

## ⚙️ Konfiguration

### Backend (.env)

```env
# SQLite Database
SQLITE_DB_PATH=/app/backend/trading.db

# MetaAPI
METAAPI_TOKEN=your_metaapi_token
METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941
METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39

# KI Provider (optional - einer reicht)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# Marktdaten (optional)
ALPHA_VANTAGE_KEY=...
NEWS_API_KEY=...
```

### Frontend (.env)

```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

### Trading Settings (UI)

Alle Trading-Settings können über die UI konfiguriert werden:
- Auto-Trading Ein/Aus
- Standard-Strategie
- Risiko-Level (Low/Medium/High)
- Position-Größe
- Stop-Loss/Take-Profit Prozente
- Aktive Plattformen
- KI-Provider Auswahl

---

## 🔧 Fehlerbehebung

### Häufige Probleme

#### 1. Schwarzer Bildschirm / Runtime Error
**Lösung v2.3.32:** ErrorBoundary zeigt jetzt Fehlermeldung mit "Seite neu laden" Button.

#### 2. "Database is locked"
**Lösung v2.3.31:** Multi-Database-Architektur eliminiert Lock-Konflikte.

#### 3. MetaAPI Verbindungsfehler
1. Prüfen Sie die Account IDs in `.env`
2. Stellen Sie sicher, dass MetaAPI Token gültig ist
3. MetaTrader 5 muss laufen (für Live-Daten)

#### 4. Trades werden nicht angezeigt
1. Prüfen Sie ob der richtige Broker aktiv ist
2. Backend-Logs prüfen: `tail -f /var/log/supervisor/backend.err.log`
3. Browser-Console auf Fehler prüfen

#### 5. KI antwortet nicht
1. Prüfen Sie ob ein KI-Provider konfiguriert ist
2. API-Key in Settings validieren
3. Bei Ollama: Ist der lokale Server gestartet?

### Logs prüfen

```bash
# Backend Logs
tail -f /var/log/supervisor/backend.err.log

# Frontend (Browser)
F12 → Console Tab

# Supervisor Status
sudo supervisorctl status
```

### Neustart

```bash
# Backend neu starten
sudo supervisorctl restart backend

# Frontend neu starten
sudo supervisorctl restart frontend
```

---

## 📞 Support

Bei Problemen:
1. Logs prüfen (siehe oben)
2. Release Notes lesen
3. Bekannte Issues in der Dokumentation prüfen

---

**Letzte Aktualisierung:** 17. Dezember 2025, v2.3.32
