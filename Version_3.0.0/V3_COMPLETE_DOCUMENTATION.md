# Project EMERGENT V3.0.0 - Vollständige Dokumentation

## 🚀 Übersicht

Project EMERGENT V3.0.0 ist ein umfassendes Upgrade des autonomen Trading-Bots mit folgenden Hauptfunktionen:

1. **Vollständige Asset-Matrix (20 Assets)**
2. **4-Säulen-Confidence-Engine V2** mit asset-spezifischen Gewichtungen
3. **iMessage "Command & Control" Bridge**
4. **KI-Controller (Ollama/Llama 3.2)**
5. **Automatisiertes Reporting via AppleScript**

---

## 📊 1. Asset-Matrix (20 Assets)

### Vollständige Liste

| Kategorie | Assets |
|-----------|--------|
| **Edelmetalle** | Gold, Silber, Platin, Palladium |
| **Industriemetalle** | Kupfer, **Zink (NEU)** |
| **Energie** | WTI Öl, Brent Öl, Natural Gas |
| **Agrar** | Weizen, Mais, Sojabohnen, Kaffee, Zucker, Kakao |
| **Forex** | EUR/USD, **USD/JPY (NEU)** |
| **Crypto** | Bitcoin, **Ethereum (NEU)** |
| **Indizes** | **Nasdaq 100 (NEU)** |

### Neue Assets - Spezifische Einstellungen

- **Nasdaq 100**: US-Session (15:30-22:00 MEZ), Fokus auf Trend-Stabilität
- **USD/JPY**: Forex 24/5, JPY als Safe-Haven-Korrelation zu Gold
- **Ethereum**: 24/7 Crypto-Markt, hohe Volatilität
- **Zink**: LME-Handelszeiten (09:00-17:00 GMT), industrielle Basis-Signale

---

## 🧮 2. 4-Säulen-Confidence-Engine V2

### Asset-Spezifische Gewichtungen

| Asset | Basis-Signal | Trend-Konfluenz | Volatilität | Sentiment |
|-------|--------------|-----------------|-------------|-----------|
| **Nasdaq 100** | 25% | **45%** | 15% | 15% |
| **USD/JPY** | 30% | 25% | 15% | **30%** |
| **Ethereum** | 30% | 20% | **40%** | 10% |
| **Zink/Metalle** | **45%** | 25% | 20% | 10% |
| **Standard** | 35% | 25% | 25% | 15% |

### Risiko-Modi mit Threshold-Overrides

| Modus | Standard | Zink | Nasdaq 100 |
|-------|----------|------|------------|
| **Konservativ** | >75% | >70% | >72% |
| **Standard** | >68% | >62% | >65% |
| **Aggressiv** | >60% | >55% | >55% |

---

## 📱 3. iMessage "Command & Control" Bridge

### Voraussetzungen (macOS)

1. **Full Disk Access** für Terminal/Python aktivieren:
   - Systemeinstellungen > Datenschutz & Sicherheit > Voller Festplattenzugriff
   
2. **Autorisierte Absender**:
   - `+4917677868993`
   - `dj1dbr@yahoo.de`

### Verfügbare Befehle

| Befehl | Aktion | Beschreibung |
|--------|--------|--------------|
| `Status` / `Ampel` | GET_STATUS | Systemstatus abrufen |
| `Balance` / `Kontostand` | GET_BALANCE | Kontostand zeigen |
| `Trades` / `offene Trades` | GET_TRADES | Offene Positionen |
| `Gewinne sichern` | CLOSE_PROFIT | Gewinn-Trades schließen |
| `Start` / `Weiter` | START_TRADING | Trading starten |
| `Stop` / `Pause` | STOP_TRADING | Trading pausieren |
| `Hilfe` / `Help` | HELP | Befehlsliste |

### API-Endpoints

```bash
# Status der iMessage-Integration
GET /api/imessage/status

# Befehl manuell ausführen (für Tests)
POST /api/imessage/command?text=Status
```

---

## 🤖 4. KI-Controller (Ollama/Llama 3.2)

### Installation auf macOS

```bash
# Ollama installieren
brew install ollama

# Llama 3.2 Modell laden
ollama pull llama3.2

# Ollama starten
ollama serve
```

### Konfiguration

- **Modell**: Llama 3.2 (32k Context-Fenster)
- **URL**: `http://localhost:11434`
- **Fallback**: Pattern-Matching wenn Ollama nicht verfügbar

### Funktionen

1. **Befehlsanalyse**: Übersetzt natürliche Sprache in Aktionen
2. **Signal-Reasoning**: Generiert Begründungen für Trading-Signale
3. **NLP**: Verarbeitet unbekannte Befehle

---

## 📊 5. Automatisiertes Reporting

### Scheduled Reports

| Zeit | Report | Inhalt |
|------|--------|--------|
| **07:00 Uhr** | Morgen-Heartbeat | System-Status, Balance, aktive Assets |
| **22:00 Uhr** | Tages-Report | P&L, Trade-Statistiken, Balance |

### Live Signal-Alerts

Bei Ampelwechsel auf **GRÜN** (Confidence > Threshold):

```
🟢 Signal GOLD
📊 Score: 78%
📐 Stärkste Säule: Trend-Konfluenz
⏱️ Cooldown: 5 Min
```

### API-Endpoints

```bash
# Reporting-Status
GET /api/reporting/status

# Reporting starten/stoppen
POST /api/reporting/start
POST /api/reporting/stop

# Test-Nachrichten (sendet auf macOS)
POST /api/reporting/test/heartbeat
POST /api/reporting/test/evening
POST /api/reporting/test/signal?asset=GOLD&signal=BUY&confidence=78
```

---

## 🔧 Dateien & Struktur

```
/app/Version_3.0.0/
├── backend/
│   ├── server.py                    # Haupt-API mit allen V3.0.0 Endpoints
│   ├── autonomous_trading_intelligence.py  # 4-Säulen-Engine V2
│   ├── commodity_processor.py       # Asset-Definitionen (20 Assets)
│   ├── multi_bot_system.py          # Trading-Logik
│   ├── hybrid_data_fetcher.py       # Marktdaten-Quellen
│   ├── imessage_bridge.py           # iMessage "Command & Control"
│   ├── ollama_controller.py         # KI-Controller (Llama 3.2)
│   └── automated_reporting.py       # Automatische Reports
└── frontend/
    └── src/
        ├── pages/Dashboard.jsx      # Haupt-Dashboard
        └── components/
            └── AIIntelligenceWidget.jsx
```

---

## 🚀 Quick Start

### 1. Backend starten (auf Emergent-Server)

```bash
# Ist bereits konfiguriert und läuft
sudo supervisorctl status backend
```

### 2. Auf macOS deployen

1. Code herunterladen
2. Ollama installieren: `brew install ollama && ollama pull llama3.2`
3. Full Disk Access aktivieren
4. Backend starten: `cd backend && python server.py`

### 3. iMessage-Befehle testen

Senden Sie eine Nachricht mit "Status" an die App (von der autorisierten Nummer).

---

## 📝 API-Übersicht

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v3/info` | GET | Vollständige V3.0.0 Feature-Info |
| `/api/commodities` | GET | Alle 20 Assets |
| `/api/settings` | GET/POST | Trading-Einstellungen |
| `/api/imessage/status` | GET | iMessage-Integration Status |
| `/api/imessage/command` | POST | Befehl ausführen |
| `/api/reporting/status` | GET | Reporting-System Status |
| `/api/reporting/test/*` | POST | Test-Nachrichten |

---

## ⚠️ Hinweise

1. **iMessage funktioniert NUR auf macOS** mit aktiviertem Full Disk Access
2. **Ollama muss lokal laufen** für KI-gestützte Befehlsanalyse
3. **MetaAPI-Verbindung** erforderlich für Live-Trading und Balance
4. **Signal-Alerts haben 5 Min Cooldown** um Spam zu vermeiden

---

*Version 3.0.0 - Project EMERGENT - Dezember 2025*
