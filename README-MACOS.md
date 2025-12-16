# 🚀 BOONER TRADE v2.3.27 - macOS Setup Guide

## ✨ NEU in v2.3.27
- ⚡ **Scalping Trading Strategie** komplett implementiert (Frontend + Backend)
- 🦙 **Ollama AI Chat Fix** (Model: llama3:latest)
- 🐛 **Bug Fixes** für Closed Trades Speicherung
- 🎨 **UI Verbesserungen** in Settings Dialog

---

## 📋 Voraussetzungen

### Erforderlich:
1. **Python 3.9+** ([Download](https://www.python.org/downloads/))
2. **Node.js 18+** ([Download](https://nodejs.org/))
3. **Yarn** (nach Node.js: `npm install -g yarn`)

### Optional (für AI Chat):
4. **Ollama** ([Download](https://ollama.ai/))
   - Nach Installation: `ollama pull llama3:latest`

---

## 🔧 Installation

### Schritt 1: Komplettes Setup
```bash
cd /Pfad/zu/BOONER-V2.3.27
./COMPLETE-MACOS-SETUP.sh
```

**Dauer:** 15-20 Minuten (je nach Internet-Geschwindigkeit)

**Was passiert:**
- ✅ Clean Build (löscht alte Caches)
- ✅ Backend Dependencies installieren
- ✅ Frontend Build erstellen
- ✅ Electron App für macOS bauen

---

## 🚀 App Starten

### Option 1: Production App (empfohlen)
```bash
# Nach COMPLETE-MACOS-SETUP.sh
open electron-app/dist/mac/Booner-Trade.app
```

### Option 2: Development Mode
```bash
./START-APP-MAC.sh
```
**Vorteile:**
- Live Logs anzeigen
- Schnellerer Start
- Einfaches Debugging

---

## 🛑 App Stoppen

```bash
./STOP-APP-MAC.sh
```

Oder manuell:
```bash
pkill -f "python.*server.py"
pkill -f "electron"
```

---

## 🎯 Scalping Feature Testen

1. App starten
2. **Einstellungen** öffnen (Zahnrad-Icon)
3. Tab **"Trading Strategien"** anklicken
4. Nach unten scrollen
5. **"⚡ Scalping (Ultra-Schnell)"** sollte mit **lila Border** sichtbar sein

### Scalping Parameter:
- **Min. Konfidenz:** 60% (höher als andere Strategien)
- **Max. Positionen:** 3 (weniger als andere)
- **Take Profit:** 15 Pips (0,15%)
- **Stop Loss:** 8 Pips (0,08%)
- **Max Haltezeit:** 5 Minuten
- **Risiko/Trade:** 0,5%

---

## 🦙 Ollama AI Chat Setup

### Installation:
```bash
# Ollama installieren
brew install ollama

# Model herunterladen
ollama pull llama3:latest

# Ollama starten
ollama serve
```

### In der App:
1. **Einstellungen** → **AI Bot**
2. AI Provider: **Ollama**
3. Base URL: `http://127.0.0.1:11434`
4. Model: `llama3:latest`

---

## 📁 Projekt-Struktur

```
BOONER-V2.3.27/
├── backend/              # FastAPI Python Backend
│   ├── server.py        # Haupt-Server
│   ├── scalping_strategy.py  # Scalping Logik
│   └── requirements.txt
├── frontend/            # React Frontend
│   ├── src/
│   │   ├── pages/Dashboard.jsx
│   │   └── components/SettingsDialog.jsx  # Scalping UI
│   └── package.json
├── electron-app/        # Electron Desktop Wrapper
│   └── main.js
└── *.sh                # Setup & Start Scripts
```

---

## 🐛 Troubleshooting

### Problem: "No such file or directory: backend"
**Lösung:** Script aus dem falschen Verzeichnis gestartet
```bash
cd /vollständiger/Pfad/zu/BOONER-V2.3.27
./COMPLETE-MACOS-SETUP.sh
```

### Problem: "Permission denied"
**Lösung:** Scripts executable machen
```bash
chmod +x *.sh
```

### Problem: "Port already in use"
**Lösung:** Alte Prozesse beenden
```bash
./STOP-APP-MAC.sh
# oder
lsof -ti:8000 | xargs kill  # Backend Port
```

### Problem: "Yarn install fails"
**Lösung:** Node.js neu installieren
```bash
brew uninstall node
brew install node@18
npm install -g yarn
```

### Problem: "Scalping UI nicht sichtbar"
**Lösung:** Clean Build durchführen
```bash
# Caches löschen
rm -rf frontend/node_modules/.cache
rm -rf frontend/build
rm -rf electron-app/dist

# Neu bauen
cd frontend
yarn build

# App neu starten
cd ..
./START-APP-MAC.sh
```

---

## 📊 Logs anzeigen

### Backend Logs:
```bash
tail -f logs/backend.log
```

### Electron Logs:
```bash
tail -f logs/electron.log
```

### Python Errors:
```bash
cd backend
source venv/bin/activate
python server.py  # Direkt im Terminal starten
```

---

## 🔄 Updates

### Code aktualisiert?
```bash
# Frontend neu bauen
cd frontend
rm -rf build node_modules/.cache
yarn build

# Electron neu bauen
cd ../electron-app
yarn build:mac
```

### Dependencies aktualisiert?
```bash
# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
yarn install
```

---

## 📧 Support

Bei Problemen:
1. Logs prüfen (`logs/` Verzeichnis)
2. Clean Build versuchen
3. Dependencies neu installieren

---

## ✅ Checkliste nach Installation

- [ ] App startet ohne Fehler
- [ ] Dashboard lädt korrekt
- [ ] Einstellungen öffnen funktioniert
- [ ] **Scalping UI ist sichtbar** (mit lila Border)
- [ ] Commodity Cards zeigen Daten
- [ ] (Optional) Ollama AI Chat funktioniert

---

**Version:** 2.3.27  
**Letzte Aktualisierung:** Dezember 2024  
**Platform:** macOS (Intel & Apple Silicon)

🚀 **Viel Erfolg beim Trading!**
