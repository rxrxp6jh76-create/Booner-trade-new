# 📚 Booner Trade - Vollständige Dokumentation

**Version:** 2.3.32  
**Stand:** 17. Dezember 2025

---

## 📖 Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Architektur](#architektur)
3. [KI-Trading-System](#ki-trading-system)
4. [Multi-Bot-Architektur](#multi-bot-architektur)
5. [Trading-Strategien](#trading-strategien)
6. [SL/TP Berechnung](#sltp-berechnung)
7. [Portfolio-Risiko-Management](#portfolio-risiko-management)
8. [API Referenz](#api-referenz)
9. [Datenbank-Schema](#datenbank-schema)
10. [Konfiguration](#konfiguration)
11. [Fehlerbehebung](#fehlerbehebung)
12. [Changelog v2.3.32](#changelog-v2332)

---

## 🎯 Überblick

Booner Trade ist eine professionelle Trading-Anwendung für den automatisierten und manuellen Handel mit Rohstoffen, Forex und Kryptowährungen. Die App verbindet sich mit MetaTrader 5 über MetaAPI und bietet KI-gestützte Handelsanalysen.

### Hauptfunktionen:
- 📊 **Live-Marktdaten** für 15+ Rohstoffe und Währungspaare
- 🤖 **KI-Trading-Bot** mit Multi-Bot-Architektur (3 spezialisierte Bots)
- 📈 **7 Trading-Strategien** (Day, Swing, Scalping, Mean Reversion, Momentum, Breakout, Grid)
- 🔌 **MetaTrader 5 Integration** über MetaAPI
- 📱 **Backtesting** für Strategie-Optimierung
- 🛡️ **Risiko-Management** mit Portfolio-Schutz (max. 20% pro Broker)
- 💬 **KI-Chat** mit Spracherkennung für Marktanalysen

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
│   ├── multi_bot_system.py       # 🤖 KI Multi-Bot System
│   ├── database_v2.py            # Multi-Database Manager
│   ├── risk_manager.py           # Portfolio-Risiko-Verwaltung
│   ├── backtesting_engine.py     # Backtesting-Engine
│   ├── metaapi_sdk_connector.py  # MT5 Verbindung
│   ├── commodity_processor.py    # Marktdaten-Verarbeitung
│   └── strategies/               # Trading-Strategien
│       ├── mean_reversion.py
│       ├── momentum_trading.py
│       ├── breakout_strategy.py
│       └── grid_trading.py
│
├── frontend/
│   ├── src/
│   │   ├── App.js                # Hauptapp mit ErrorBoundary
│   │   ├── pages/Dashboard.jsx   # Haupt-Dashboard
│   │   └── components/
│   │       ├── AIChat.jsx        # KI-Chat mit Spracherkennung
│   │       ├── BacktestingPanel.jsx
│   │       ├── RiskDashboard.jsx
│   │       └── SettingsDialog.jsx
```

---

## 🤖 KI-Trading-System

### Übersicht

Das KI-System ist das Herzstück von Booner Trade. Es analysiert kontinuierlich Marktdaten, generiert Trading-Signale und führt Trades automatisch aus.

### Aufgaben der KI

| Aufgabe | Beschreibung | Intervall |
|---------|--------------|-----------|
| **Marktanalyse** | Sammelt Preisdaten, berechnet technische Indikatoren (RSI, MACD, SMA, EMA) | 8 Sekunden |
| **Signal-Generierung** | Analysiert Indikatoren, wendet Strategien an, generiert BUY/SELL/HOLD Signale | 20 Sekunden |
| **Trade-Ausführung** | Prüft Portfolio-Risiko, eröffnet Trades, setzt SL/TP | 12 Sekunden |
| **Position-Überwachung** | Überwacht offene Positionen, prüft ob TP erreicht, schließt Trades | 12 Sekunden |

### KI-Provider

Die KI kann mit verschiedenen Providern arbeiten:

```
┌─────────────────────────────────────────────────────────────┐
│                    KI-Provider Auswahl                       │
├─────────────────┬───────────────────────────────────────────┤
│  OpenAI         │  GPT-4, GPT-4o - Beste Qualität           │
│  Gemini         │  Google Gemini - Schnell & günstig        │
│  Claude         │  Anthropic Claude - Gute Analyse          │
│  Ollama         │  Lokal - Keine API-Kosten, privat         │
└─────────────────┴───────────────────────────────────────────┘
```

### KI-Chat Funktionen

Der integrierte KI-Chat bietet:
- **Textbasierte Analyse**: Fragen zu Marktbedingungen stellen
- **Spracherkennung**: Mikrofon-Button für Spracheingabe (Web Speech API)
- **Kontext-Bewusstsein**: KI kennt offene Trades und aktuelle Marktdaten
- **Multi-Sprache**: Unterstützt Deutsch und Englisch

---

## 🔄 Multi-Bot-Architektur

### Die 3 spezialisierten Bots

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MultiBotSystem v2.3.31                          │
├─────────────────────┬─────────────────────┬─────────────────────────┤
│      MarketBot      │      SignalBot      │       TradeBot          │
│      (8 Sek)        │      (20 Sek)       │       (12 Sek)          │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ 📊 Preise holen     │ 🧠 Signale          │ 💰 Trades ausführen     │
│ 📈 Indikatoren      │    analysieren      │ 👀 Positionen           │
│    berechnen        │ 📰 News checken     │    überwachen           │
│ 💾 In DB speichern  │ 🎯 Strategien       │ 🎯 SL/TP prüfen         │
│                     │    anwenden         │ ✅ Auto-Close bei TP    │
└─────────────────────┴─────────────────────┴─────────────────────────┘
```

### MarketBot - Datensammler

**Aufgabe**: Sammelt und verarbeitet Marktdaten

```python
# Berechnet für jedes Asset:
- Aktueller Preis (von Yahoo Finance / MetaAPI)
- RSI (Relative Strength Index) - Überkauft/Überverkauft
- MACD (Moving Average Convergence Divergence) - Trend
- SMA/EMA (Simple/Exponential Moving Average)
- Volumen
- Trend-Richtung (UP/DOWN)
```

### SignalBot - Strategie-Analyst

**Aufgabe**: Generiert Trading-Signale basierend auf Indikatoren

```python
# Signal-Generierung pro Strategie:

# Mean Reversion (🔄)
if RSI < 30:  # Überverkauft
    signal = "BUY", confidence = 0.7
elif RSI > 70:  # Überkauft
    signal = "SELL", confidence = 0.7

# Momentum (🚀)
if trend == "UP" and signal == "BUY":
    signal = "BUY", confidence = 0.65
elif trend == "DOWN" and signal == "SELL":
    signal = "SELL", confidence = 0.65

# Breakout (💥)
if RSI > 65 and trend == "UP":
    signal = "BUY", confidence = 0.6
elif RSI < 35 and trend == "DOWN":
    signal = "SELL", confidence = 0.6
```

### TradeBot - Trade-Executor

**Aufgabe**: Führt Trades aus und überwacht Positionen

```python
# Trade-Ausführung Workflow:
1. Signal aus pending_signals holen
2. Portfolio-Risiko prüfen (max 20%)
3. Max-Positionen pro Asset prüfen
4. Lot-Size berechnen
5. SL/TP basierend auf Strategie berechnen
6. Trade über MetaAPI ausführen
7. In ticket_strategy_map speichern
8. Position überwachen

# Auto-Close bei Take Profit:
for position in open_positions:
    if current_price >= take_profit (BUY):
        close_position()
    elif current_price <= take_profit (SELL):
        close_position()
```

---

## 📈 Trading-Strategien

### 7 verfügbare Strategien

| Strategie | Symbol | Beschreibung | Standard SL | Standard TP |
|-----------|--------|--------------|-------------|-------------|
| **Day Trading** | ⚡ | Intraday-Handel, schnelle Trades | 1.5% | 2.5% |
| **Swing Trading** | 📈 | Multi-Day Positionen, größere Moves | 2.0% | 4.0% |
| **Scalping** | ⚡ | Sekunden bis Minuten, kleine Gewinne | 0.5% | 1.0% |
| **Mean Reversion** | 🔄 | Rückkehr zum Mittelwert bei RSI-Extremen | 2.0% | 0.8% |
| **Momentum** | 🚀 | Trend-Following, starke Bewegungen | 2.5% | 5.0% |
| **Breakout** | 💥 | Ausbruch aus Konsolidierungen | 2.0% | 3.0% |
| **Grid Trading** | 📊 | Mehrere Orders in festem Abstand | 1.5% | 1.5% |

### Strategie-Aktivierung

Jede Strategie kann in den Settings aktiviert/deaktiviert werden:

```javascript
// Settings-Keys:
day_trading_enabled: true/false
swing_trading_enabled: true/false
scalping_enabled: true/false
mean_reversion_enabled: true/false
momentum_enabled: true/false
breakout_enabled: true/false
grid_enabled: true/false
```

### Signal-Logik Details

#### Mean Reversion
```
Konzept: Preise kehren zum Mittelwert zurück

Entry BUY:  RSI < 30 (überverkauft)
Entry SELL: RSI > 70 (überkauft)

Ideal für: Seitwärtsmärkte, Range-Bound Assets
```

#### Momentum
```
Konzept: Trends setzen sich fort

Entry BUY:  Trend = UP + Signal = BUY
Entry SELL: Trend = DOWN + Signal = SELL

Ideal für: Trending Markets, News-Events
```

#### Breakout
```
Konzept: Ausbruch aus Konsolidierung

Entry BUY:  RSI > 65 + Trend = UP
Entry SELL: RSI < 35 + Trend = DOWN

Ideal für: Volatilitäts-Ausbrüche
```

---

## 🎯 SL/TP Berechnung

### Automatische Berechnung

SL (Stop Loss) und TP (Take Profit) werden **automatisch** basierend auf der Strategie berechnet:

```python
# Für BUY Trades:
stop_loss = entry_price * (1 - sl_percent / 100)
take_profit = entry_price * (1 + tp_percent / 100)

# Für SELL Trades:
stop_loss = entry_price * (1 + sl_percent / 100)
take_profit = entry_price * (1 - tp_percent / 100)
```

### Beispiel: Mean Reversion SELL

```
Strategie: mean_reversion
SL-Setting: 2.0%
TP-Setting: 0.8%

Entry Price: $65.74 (Silber)

Stop Loss:   $65.74 * 1.02 = $67.05 (2% ÜBER Entry)
Take Profit: $65.74 * 0.992 = $65.21 (0.8% UNTER Entry)
```

### trade_settings Tabelle

Die SL/TP werden in der `trade_settings` Tabelle gespeichert:

```sql
CREATE TABLE trade_settings (
    trade_id TEXT PRIMARY KEY,  -- z.B. "mt5_76191436"
    stop_loss REAL,
    take_profit REAL,
    strategy TEXT,
    trailing_stop_enabled INTEGER,
    created_at TEXT
);
```

---

## 🛡️ Portfolio-Risiko-Management

### 20% Regel

Der Bot öffnet **keine neuen Trades** wenn das Portfolio-Risiko über 20% liegt:

```python
# Portfolio-Risiko Berechnung (v2.3.32 korrigiert):
portfolio_risk_percent = (margin_used / balance) * 100

# Prüfung vor Trade-Eröffnung:
if portfolio_risk_percent > 20:
    logger.warning(f"⚠️ Portfolio risk exceeded: {portfolio_risk_percent}%")
    skip_trade()
```

### Anzeige im Dashboard

| Broker | Balance | Margin Used | Risiko | Status |
|--------|---------|-------------|--------|--------|
| Libertex | €46.838 | €7.936 | 17% | ✅ Trades erlaubt |
| ICMarkets | €2.485 | €1.666 | 67% | ⚠️ BLOCKIERT |

### Max Positionen pro Asset

Zusätzlich zum Portfolio-Risiko gibt es Limits pro Asset:

```python
# Standard Limits:
max_positions_per_commodity = 5
max_total_positions = 20

# Prüfung:
if existing_positions >= max_positions:
    logger.warning(f"⚠️ Max positions reached for {commodity}")
    skip_trade()
```

---

## 🔌 API Referenz

### Basis-URL
```
https://[your-domain]/api
```

### Trading Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/trades/list` | Alle Trades abrufen |
| GET | `/api/trades/list?status=OPEN` | Nur offene Trades |
| POST | `/api/trades/close` | Trade schließen |
| GET | `/api/trades/stats` | Trade-Statistiken |

### Bot Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/bot/status` | Multi-Bot Status |
| POST | `/api/bot/start` | Bot starten |
| POST | `/api/bot/stop` | Bot stoppen |

### Bot Status Response

```json
{
  "running": true,
  "architecture": "multi-bot",
  "bots": {
    "market_bot": {
      "is_running": true,
      "run_count": 150,
      "error_count": 0
    },
    "signal_bot": {
      "is_running": true,
      "run_count": 50,
      "error_count": 0,
      "active_strategies": ["mean_reversion", "momentum", "day_trading"]
    },
    "trade_bot": {
      "is_running": true,
      "run_count": 75,
      "error_count": 0
    }
  },
  "statistics": {
    "total_trades_executed": 5,
    "pending_signals": 3
  }
}
```

---

## 💾 Datenbank-Schema

### Multi-Database Architektur

```
┌──────────────────┬──────────────────┬────────────────────────┐
│   settings.db    │    trades.db     │    market_data.db      │
├──────────────────┼──────────────────┼────────────────────────┤
│ trading_settings │ trades           │ market_data            │
│ api_keys         │ closed_trades    │ market_data_history    │
│                  │ trade_settings   │                        │
│                  │ ticket_strategy  │                        │
│                  │   _map           │                        │
└──────────────────┴──────────────────┴────────────────────────┘
```

### ticket_strategy_map (v2.3.32)

Speichert die Zuordnung von MT5-Ticket zu Strategie:

```sql
CREATE TABLE ticket_strategy_map (
    mt5_ticket TEXT PRIMARY KEY,
    strategy TEXT,
    commodity TEXT,
    platform TEXT,
    created_at TEXT
);
```

---

## ⚙️ Konfiguration

### Backend (.env)

```env
# MetaAPI (WICHTIG nach jedem Fork prüfen!)
METAAPI_TOKEN=your_metaapi_token
METAAPI_ACCOUNT_ID=trade-bugfix-hub
METAAPI_ICMARKETS_ACCOUNT_ID=trade-bugfix-hub

# KI Provider (einer reicht)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

### Trading Settings (UI)

Alle Trading-Settings können über die UI konfiguriert werden:
- Auto-Trading Ein/Aus
- Standard-Strategie
- SL/TP Prozente pro Strategie
- Max Positionen
- Aktive Plattformen
- KI-Provider Auswahl

---

## 🔧 Fehlerbehebung

### Häufige Probleme

#### 1. Runtime Error / Schwarzer Bildschirm
**Lösung v2.3.32**: ErrorBoundary zeigt jetzt Fehlermeldung mit "Seite neu laden" Button.

#### 2. Alle Trades zeigen "day" Strategie
**Lösung v2.3.32**: 
- Strategie-Mapping korrigiert
- `ticket_strategy_map` wird jetzt gefüllt
- Lokale DB-Strategie hat Priorität

#### 3. SL/TP entsprechen nicht den Settings
**Lösung v2.3.32**:
- `trade_settings` werden mit korrekter Strategie aktualisiert
- Berechnung: SL/TP basierend auf Strategie-spezifischen Prozenten

#### 4. Portfolio-Risiko falsch berechnet
**Lösung v2.3.32**:
```python
# ALT (falsch):
risk = ((balance - equity) / balance) * 100

# NEU (korrekt):
risk = (margin / balance) * 100
```

#### 5. "[object Object]" Fehlermeldung
**Lösung v2.3.32**: Bessere Error-Serialisierung im Frontend

### Logs prüfen

```bash
# Backend Logs
tail -f /var/log/supervisor/backend.err.log

# Neustart
sudo supervisorctl restart backend
```

---

## 📋 Changelog v2.3.32

### Kritische Bug Fixes

1. **Runtime Error `prev.map is not a function`**
   - Ursache: `commodities` war Objekt statt Array
   - Fix: Typ-Prüfung vor `.map()` Aufruf

2. **`'NoneType' object has no attribute 'deleted_count'`**
   - Ursache: `delete_many()` nicht implementiert
   - Fix: Vollständige Implementierung in `database.py`

3. **Portfolio-Risiko falsch berechnet**
   - Ursache: `(balance - equity)` statt `margin`
   - Fix: `(margin / balance) * 100`

4. **Nur "day" Strategie wurde verwendet**
   - Ursache: Setting-Keys Mapping falsch
   - Fix: `day_enabled` UND `day_trading_enabled` werden geprüft

5. **SL/TP nicht konsistent mit Strategy-Settings**
   - Ursache: `trade_settings` hatte alte Werte
   - Fix: Migration aller `mt5_*` Einträge mit korrekten Werten

6. **Fortschrittsanzeige inkonsistent mit P&L**
   - Ursache: Yahoo Finance Preis statt MT5 Preis
   - Fix: `trade.price` hat Priorität über `allMarkets[].price`

7. **Multi-Bot startete nicht automatisch**
   - Ursache: Nur bei Settings-Änderung gestartet
   - Fix: Auto-Start beim Server-Startup wenn `auto_trading = true`

8. **MarketBot Import-Fehler**
   - Ursache: `market_data_service` Modul nicht vorhanden
   - Fix: Verwendet `commodity_processor` stattdessen

### Neue Features

- **Alle 7 Strategien im Frontend angezeigt**
  - Mean Rev (🔄 pink)
  - Momentum (🚀 orange)
  - Scalping (⚡ gelb)
  - Breakout (💥 cyan)
  - Grid (📊 indigo)

- **ErrorBoundary Component**
  - Fängt React Fehler ab
  - Zeigt benutzerfreundliche Fehlermeldung
  - "Seite neu laden" Button

- **Verbesserte Fehlermeldungen**
  - Kein `[object Object]` mehr
  - JSON-Serialisierung bei komplexen Fehlern

---

## 📞 Support

Bei Problemen:
1. Logs prüfen (siehe oben)
2. Release Notes lesen
3. Bekannte Issues in der Dokumentation prüfen

---

**Letzte Aktualisierung:** 17. Dezember 2025, v2.3.32
