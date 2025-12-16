# BOONER TRADE - macOS Desktop App Build (Version 2.0)

## 🚀 Schnellstart

**Ein Befehl macht alles:**

```bash
cd /app/electron-app
./BUILD-MACOS-COMPLETE.sh
```

Das war's! Das Script macht ALLES automatisch:
- ✅ Port 8000 freigeben
- ✅ Frontend bauen
- ✅ Python venv erstellen
- ✅ Dependencies installieren
- ✅ Resources kopieren
- ✅ Electron App bauen
- ✅ Alte App löschen
- ✅ Neue App installieren
- ✅ Quarantine Flag entfernen
- ✅ App öffnen

## ⚡ Quick-Fix (nur main.js ändern)

**Wenn du nur die main.js geändert hast:**

```bash
cd /app/electron-app
./QUICK-FIX-MAIN-JS.sh
```

Dieser Befehl kopiert die neue main.js direkt in die bereits installierte App - **ohne kompletten Rebuild!** Das spart enorm Zeit beim Testen.

---

## 📋 Voraussetzungen

**Auf deinem Mac muss installiert sein:**
- Node.js 18+ (für Electron)
- **Homebrew** (für automatische Python 3.11 Installation)
- Yarn (für Frontend)
- macOS M4 ARM64

**Python 3.11** wird automatisch vom Build-Script installiert falls nicht vorhanden!

### Homebrew installieren (falls noch nicht vorhanden):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Warum Python 3.11?** Das MetaAPI SDK hat Kompatibilitätsprobleme mit Python 3.14 (Pre-Release). Mit Python 3.11 funktioniert der SDK-Connector perfekt (on-demand, keine Quota-Limits). Das Build-Script installiert Python 3.11 automatisch in einer venv innerhalb der App - dein System-Python bleibt unverändert!

**Im Emergent Environment:**
Alles ist bereits installiert! ✅

---

## 🔧 Was das Script macht (im Detail)

### 1. Frontend Build
```bash
cd /app/frontend
export REACT_APP_BACKEND_URL="http://localhost:8000"
yarn build
```

### 2. Python venv erstellen
```bash
python3 -m venv --copies /app/electron-app/resources/app/python/venv
```
**Wichtig:** `--copies` für macOS (keine Symlinks!)

### 3. Dependencies installieren
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Resources kopieren
- Backend → `resources/app/backend/`
- Frontend → `resources/app/frontend/`
- .env → `resources/app/backend/.env`

### 5. Electron App bauen
```bash
npm run build  # → dist/mac-arm64/Booner Trade.app
```

### 6. Installation
```bash
sudo rm -rf "/Applications/Booner Trade.app"  # Alte löschen
sudo cp -R "dist/mac-arm64/Booner Trade.app" /Applications/
```

### 7. Quarantine entfernen
```bash
sudo xattr -cr "/Applications/Booner Trade.app"
```

### 8. App öffnen
```bash
open "/Applications/Booner Trade.app"
```

---

## ⚠️ WICHTIG: Nach jedem Fork

**MetaAPI IDs müssen neu eingesetzt werden!**

```bash
# Öffne .env
nano /app/backend/.env

# Ersetze:
METAAPI_ACCOUNT_ID=trading-desktop
METAAPI_ICMARKETS_ACCOUNT_ID=trading-desktop

# Speichern und Backend neu starten
sudo supervisorctl restart backend
```

---

## 🐛 Troubleshooting

### Problem: "Backend antwortet nicht"

**Lösung:**
```bash
# Prüfe Backend Logs
tail -100 /var/log/supervisor/backend.err.log

# Prüfe ob Backend läuft
ps aux | grep uvicorn

# Neu starten falls nötig
sudo supervisorctl restart backend
```

### Problem: "Keine Balancen / Trades"

**Ursache:** MetaAPI IDs fehlen oder falsch

**Lösung:** Siehe "Nach jedem Fork" oben

### Problem: "App öffnet nicht"

**Lösung:**
```bash
# Quarantine Flag manuell entfernen
sudo xattr -cr "/Applications/Booner Trade.app"

# App öffnen
open "/Applications/Booner Trade.app"
```

### Problem: "Python venv Fehler"

**Lösung:**
```bash
# Komplett neu bauen
cd /app/electron-app
rm -rf resources/
./BUILD-MACOS-COMPLETE.sh
```

---

## 📊 App URLs

Nach dem Start:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/api
- **Health Check:** http://localhost:8000/api/platforms/status

---

## 🔍 Logs & Debugging

### Backend Logs (in der App)
Die App startet Uvicorn im Hintergrund. Logs sind nicht direkt sichtbar.

### App Console öffnen
In der laufenden App: `Cmd + Option + I`

### Backend manuell starten (zum Testen)
```bash
cd /app/backend
source /app/electron-app/resources/app/python/venv/bin/activate
uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 📚 Weitere Dokumentation

- **Vollständige Doku:** `/app/BOONER-TRADE-APP-VOLLSTAENDIGE-DOKUMENTATION.md`
- **Quick Reference:** `/app/QUICK-REFERENCE.md`
- **Test Results:** `/app/test_result.md`

---

## ✅ Erfolgs-Checkliste

Nach dem Build solltest du sehen:
- ✅ App öffnet sich automatisch
- ✅ Dashboard lädt
- ✅ MT5 Libertex Balance wird angezeigt
- ✅ MT5 ICMarkets Balance wird angezeigt
- ✅ ~200 Trades werden angezeigt
- ✅ Portfolio-Risiko wird berechnet
- ✅ KI Monitor läuft (Trades werden geschlossen bei TP/SL Hit)

---

**Bei Problemen:** Siehe Dokumentation oder rufe Troubleshoot Agent
