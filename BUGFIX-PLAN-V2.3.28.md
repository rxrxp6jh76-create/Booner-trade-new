# 🐛 Bug Fix Plan - Version 2.3.28
**Datum:** 16. Dezember 2024
**Basis:** v2.3.27

## 🚨 PRIORITÄT 1 - KRITISCHE BUGS

### 1. ✅ SL/TP Falsche Berechnung ⚠️ **KRITISCH!**
**Problem:** TP wird mit 1% statt 2% berechnet
**Beispiel:** Natural Gas @ 3.92$, TP sollte 4.00$ sein, zeigt aber 3.96$
**Dateien:** 
- `/app/backend/trade_settings_manager.py` - Zeile 112, 144, 147
**Fix:**
- Zeile 112: `take_profit_percent = 2.0` (war 1.0)
- Zeile 144: `day_stop_loss_percent = 2.0` (war 1.0)
- Zeile 147: `day_take_profit_percent = 2.5` (war 0.5)

### 2. ✅ Backend nicht erreichbar (schwankt)
**Problem:** Backend ist instabil, schwankt zwischen erreichbar/nicht erreichbar
**Dateien:**
- `/app/backend/server.py` - Connection Handling
- `/app/backend/database.py` - SQLite Timeout
**Fix:**
- Erhöhe SQLite Timeout
- Verbessere Error Handling
- Implementiere Retry-Logik

### 3. ✅ AI macht immer Day Trades
**Problem:** Alle AI-Trades werden als "DAY_TRADING" kategorisiert
**Dateien:**
- `/app/backend/ai_trading_bot.py` - Strategie-Zuordnung
- `/app/backend/trade_settings_manager.py` - Strategie-Erkennung
**Fix:**
- Implementiere korrekte Strategie-Erkennung basierend auf Trade-Parametern

## ⚠️ PRIORITÄT 2 - WICHTIGE BUGS

### 4. ✅ Scalping nicht in manueller Trade-Erstellung
**Dateien:**
- `/app/frontend/src/pages/Dashboard.jsx` - Manuelle Trade-Erstellung
**Fix:**
- Füge "SCALPING" Option hinzu

### 5. ✅ Manuelle Trade-Erstellung speichert nicht
**Dateien:**
- `/app/frontend/src/pages/Dashboard.jsx` - Trade Submit Handler
- `/app/backend/server.py` - Trade Creation Endpoint
**Fix:**
- Debug und repariere Save-Funktion

### 6. ✅ Day Trading Kategorie immer vordergründig
**Dateien:**
- `/app/frontend/src/pages/Dashboard.jsx` - Kategorie-Anzeige
- `/app/frontend/src/components/TradesTable.jsx`
**Fix:**
- Korrekte Sortierung/Filterung implementieren

### 7. ✅ Libertex Balance Card: Margin schwankt
**Dateien:**
- `/app/backend/server.py` - Balance Calculation
- `/app/backend/metaapi_connector.py` - Libertex Connector
**Fix:**
- Vergleiche mit IC Markets Code
- Implementiere stabilen Margin-Calculation

### 8. ✅ "Alle löschen" Funktion funktioniert nicht
**Dateien:**
- `/app/frontend/src/components/TradesTable.jsx` - Delete All Handler
- `/app/backend/server.py` - Delete All Endpoint
**Fix:**
- Repariere Endpoint und Frontend Handler

## 🔧 PRIORITÄT 3 - FEATURE VERBESSERUNGEN

### 9. ✅ Scalping Settings nicht einstellbar
**Dateien:**
- `/app/frontend/src/components/SettingsDialog.jsx` - Scalping Section
**Fix:**
- Füge alle Scalping Settings Felder hinzu

### 10. ✅ MetaAPI ID Update funktioniert nicht
**Dateien:**
- `/app/frontend/src/components/SettingsDialog.jsx` - MetaAPI ID Input
- `/app/backend/server.py` - Settings Update
**Fix:**
- Implementiere MetaAPI ID Update Funktion

### 11. ✅ Ollama llama3.2 und llama4 Support
**Dateien:**
- `/app/backend/ai_chat_service.py` - Ollama Integration
- `/app/frontend/src/components/SettingsDialog.jsx` - Model Selection
**Fix:**
- Füge llama3.2, llama4 zu verfügbaren Modellen hinzu

### 12. ✅ Whisper Service pip Installation
**Dateien:**
- `/app/backend/requirements.txt` - Dependencies
- `/app/backend/whisper_service.py` - Whisper Integration
**Fix:**
- Füge `openai-whisper` zu requirements.txt hinzu

### 13. ✅ KI Chat Mikrofon "keine Internetverbindung"
**Dateien:**
- `/app/frontend/src/pages/Dashboard.jsx` - Mikrofon Handler
- `/app/backend/whisper_service.py` - Audio Processing
**Fix:**
- Debug und repariere Audio Upload

### 14. ✅ AI Bot Tab: API Key Eingabefelder fehlen
**Dateien:**
- `/app/frontend/src/components/SettingsDialog.jsx` - AI Bot Tab
**Fix:**
- Füge API Key Input Fields für OpenAI, Gemini, Claude hinzu

## 📚 PRIORITÄT 4 - NEUE FEATURES

### 15. ✅ Zusätzliche Trading-Strategien
**Strategien:**
- Mean Reversion (Rückkehr zum Mittelwert)
- Momentum Trading (Trendfolge)
- Breakout Trading (Ausbrüche handeln)
- Grid Trading (Netz-Strategie)

**Dateien:**
- `/app/backend/trading_strategies/` - Neue Dateien
- `/app/backend/ai_trading_bot.py` - Integration
- `/app/frontend/src/components/SettingsDialog.jsx` - UI

### 16. ✅ Backtesting-Funktionalität
**Dateien:**
- `/app/backend/backtesting.py` - Neues Modul
- `/app/frontend/src/pages/Backtesting.jsx` - Neue Seite
**Features:**
- Historische Daten laden
- Strategien testen
- Performance-Metriken
- Visualisierung

### 17. ✅ Portfolio Management
**Features:**
- Gesamt-Portfolio Übersicht
- Asset-Allokation
- Diversifikation-Analyse
- Risk-Metrics

### 18. ✅ Risk Management Tools
**Features:**
- Position Sizing Calculator
- Risk/Reward Ratio
- Max Drawdown Monitoring
- Value at Risk (VaR)

## 📝 DOKUMENTATION & VERSIONIERUNG

### 19. ✅ Version 2.3.28 erstellen
**Dateien:**
- `/app/VERSION.txt` - Update zu 2.3.28
- `/app/README.md` - Aktualisieren
- `/app/RELEASE-NOTES-V2.3.28.md` - Neu erstellen
- `/app/CHANGELOG.md` - Neu erstellen

### 20. ✅ Dokumentation aktualisieren
**Dateien:**
- Alle MD-Dateien durchgehen
- Veraltete Informationen korrigieren
- Neue Features dokumentieren

### 21. ✅ MetaAPI IDs eintragen
**Dateien:**
- `/app/backend/.env` - Korrekte IDs
- `/app/COMPLETE-MACOS-SETUP.sh` - Auto-Korrektur prüfen

## ✅ CHECKLISTE FÜR FERTIGSTELLUNG

- [ ] Alle kritischen Bugs behoben
- [ ] Alle wichtigen Bugs behoben
- [ ] Alle Feature-Verbesserungen implementiert
- [ ] Neue Features implementiert (optional/zeitbasiert)
- [ ] Version 2.3.28 erstellt
- [ ] Dokumentation aktualisiert
- [ ] MetaAPI IDs korrekt
- [ ] COMPLETE-MACOS-SETUP.sh funktioniert
- [ ] Testing durchgeführt
- [ ] Release Notes erstellt

## 🎯 ERWARTETES ERGEBNIS

Nach Abschluss wird Version 2.3.28:
- ✅ Alle kritischen Bugs behoben haben
- ✅ Alle Features vollständig funktionieren
- ✅ Neue Trading-Strategien unterstützen
- ✅ Backtesting ermöglichen
- ✅ Vollständig dokumentiert sein
- ✅ Produktionsreif sein

---

**Status:** IN ARBEIT 🚧
**Letzte Aktualisierung:** 16. Dezember 2024
