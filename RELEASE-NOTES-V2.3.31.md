# 🚀 Booner Trade v2.3.31 - Performance Upgrade

**Release Datum:** 16. Dezember 2025

## 🎯 Hauptfeatures

### 1. Multi-Database Architektur 🗄️
Die Datenbank wurde in 3 separate SQLite-Dateien aufgeteilt, um Lock-Konflikte zu eliminieren:

| Datenbank | Inhalt | Zugriffsmuster |
|-----------|--------|----------------|
| `settings.db` | Trading Settings, API Keys | Selten (nur bei Änderungen) |
| `trades.db` | Trades, Trade Settings, Closed Trades | Mittel (bei Trade-Aktivität) |
| `market_data.db` | Marktdaten, Historische Daten | Sehr häufig (alle 5-15 Sek) |

**Vorteile:**
- ✅ Keine "database is locked" Fehler mehr
- ✅ 3-5x schnellere Datenbank-Operationen
- ✅ Parallele Lese-/Schreibzugriffe möglich
- ✅ Automatische Migration von alter trading.db

### 2. Multi-Bot-System 🤖
3 spezialisierte Bots arbeiten nun parallel:

| Bot | Aufgabe | Intervall |
|-----|---------|-----------|
| **MarketBot** | Marktdaten sammeln, Indikatoren berechnen | 8 Sek |
| **SignalBot** | Signale analysieren, News auswerten, Strategien | 20 Sek |
| **TradeBot** | Trades ausführen, Positionen überwachen, SL/TP | 12 Sek |

**Vorteile:**
- ✅ Parallele Verarbeitung = schnellere Reaktion
- ✅ Spezialisierte Aufgaben = bessere Performance
- ✅ Unabhängige Fehlerbehandlung pro Bot
- ✅ Detaillierter Status pro Bot abrufbar

### 3. Verbesserte SQLite Performance 🔧
- WAL-Modus aktiviert für bessere Concurrency
- 32MB Cache pro Datenbank
- 60s Timeout mit Retry-Logik
- Exponential Backoff bei Lock-Konflikten

## 🐛 Bug Fixes

- ✅ **"Database is locked"** - Komplett behoben durch Multi-DB
- ✅ **Ollama Modell-Auswahl** - Settings-Modell wird jetzt korrekt verwendet
- ✅ **MetaAPI IDs** - Korrekte Account IDs wiederhergestellt
- ✅ **SQLite data_source** - Spalte zur market_data Tabelle hinzugefügt

## 📊 Neue API Endpoints

### GET /api/bot/status
Gibt detaillierten Multi-Bot-Status zurück:
```json
{
  "running": true,
  "version": "2.3.31",
  "architecture": "multi-bot",
  "bots": {
    "market_bot": { "is_running": true, "run_count": 42, ... },
    "signal_bot": { "is_running": true, "run_count": 21, ... },
    "trade_bot": { "is_running": true, "run_count": 28, ... }
  },
  "statistics": {
    "total_trades_executed": 5,
    "total_trades_closed": 2,
    "pending_signals": 0
  }
}
```

## 📁 Neue Dateien

- `backend/database_v2.py` - Multi-Database Manager
- `backend/multi_bot_system.py` - Multi-Bot-System

## ⚙️ Technische Details

### Datenbankpfade (macOS)
```
~/Library/Application Support/booner-trade/database/
├── settings.db
├── trades.db
├── market_data.db
└── trading.db.backup  (alte DB als Backup)
```

### Bot-Intervalle (konfigurierbar)
- MarketBot: 8 Sekunden (Marktdaten)
- SignalBot: 20 Sekunden (Analyse)
- TradeBot: 12 Sekunden (Execution)

## 🔄 Migration

Die Migration von der alten Single-DB erfolgt **automatisch**:
1. Beim ersten Start werden die 3 neuen DBs erstellt
2. Daten werden aus `trading.db` migriert
3. Alte DB wird zu `trading.db.backup` umbenannt

## 📋 Bekannte Einschränkungen

- Multi-Bot-System erfordert aktiviertes Auto-Trading
- Legacy-Bot wird als Fallback verwendet wenn Multi-Bot nicht verfügbar

## 🔜 Geplant für v2.3.32

- Backtesting-Feature
- Erweiterte Portfolio-Risiko-Verwaltung
- News-Integration für SignalBot

---

**Vollständige Kompatibilität mit allen bisherigen Features!**
