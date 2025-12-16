# Booner Trade - macOS Setup Anleitung

## 🚀 Komplett Automatischer Build

Diese Anleitung zeigt dir, wie du die Booner Trade Desktop-App **komplett automatisch** bauen kannst.

---

## Schritt 1: Voraussetzungen prüfen

### Homebrew installiert?
```bash
brew --version
```

Falls nicht installiert:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Node.js & Yarn installiert?
```bash
node --version  # Sollte v18+ sein
yarn --version
```

Falls nicht:
```bash
brew install node
npm install -g yarn
```

---

## Schritt 2: Projekt vorbereiten

```bash
cd ~/mein_python_projekt/Rohstofftrader/Booner-Trade

# Backend-Patches anwenden
./PATCH-DESKTOP-APP.sh

# Neuste Build-Dateien von Emergent holen
# (Kopiere electron-app/BUILD-MACOS-COMPLETE.sh von der Platform)
```

---

## Schritt 3: BUILD starten

```bash
cd electron-app
chmod +x BUILD-MACOS-COMPLETE.sh
./BUILD-MACOS-COMPLETE.sh
```

### Was passiert automatisch:

1. ✅ **Port 8000 wird freigegeben**
2. ✅ **Frontend Dependencies** werden installiert
3. ✅ **Frontend wird gebaut** (REACT_APP_BACKEND_URL=localhost:8000)
4. ✅ **Python 3.11 wird installiert** (falls nicht vorhanden) ← NEU!
5. ✅ **Python venv** wird mit Python 3.11 erstellt
6. ✅ **Python Dependencies** werden installiert
7. ✅ **Resources** werden kopiert (Backend, Frontend, .env)
8. ✅ **Electron App** wird gebaut
9. ✅ **App wird installiert** in /Applications/
10. ✅ **Quarantine Flag** wird entfernt
11. ✅ **App wird geöffnet**

**Dauer:** Ca. 10-15 Minuten (erste Installation mit Python 3.11)

---

## Schritt 4: Testen

Die App sollte automatisch starten. Warte ca. 10 Sekunden für Backend-Start.

```bash
# Test Backend
curl http://localhost:8000/api/ping

# Test Balance
curl http://localhost:8000/api/platforms/LIBERTEX/account
```

**Erwartet:** JSON mit Balance und Equity

---

## 🐛 Troubleshooting

### Problem: "Python 3.11 installation failed"

```bash
# Manuell installieren:
brew install python@3.11

# Prüfen:
/opt/homebrew/bin/python3.11 --version
```

### Problem: "Port 8000 already in use"

```bash
# Port freigeben:
bash ~/mein_python_projekt/Rohstofftrader/Booner-Trade/electron-app/KILL-PORT-8000.sh

# Oder manuell:
kill -9 $(lsof -ti:8000)
```

### Problem: "Keine Balance sichtbar"

```bash
# Prüfe .env in der installierten App:
cat "/Applications/Booner Trade.app/Contents/Resources/app/backend/.env" | grep METAAPI

# Sollte zeigen:
# METAAPI_ACCOUNT_ID=booner-trade
# METAAPI_ICMARKETS_ACCOUNT_ID=booner-trade
```

Falls falsch: Neu bauen nach `./PATCH-DESKTOP-APP.sh`

### Problem: "App crashed sofort"

```bash
# Logs prüfen:
bash ~/mein_python_projekt/Rohstofftrader/Booner-Trade/electron-app/DEBUG-APP.sh
```

---

## 📝 Was ist NEU in dieser Version?

### Automatische Python 3.11 Installation

Das Build-Script prüft ob Python 3.11 installiert ist. Falls nicht:
- Installiert automatisch via Homebrew
- Erstellt venv mit Python 3.11
- Bundled diese venv in die App

**Ergebnis:**
- ✅ Dein System-Python (3.14) bleibt unverändert
- ✅ App nutzt eigene Python 3.11 venv
- ✅ MetaAPI SDK funktioniert perfekt (on-demand, keine Quota)
- ✅ Komplett isoliert vom System

### SDK mit REST API Fallback

Falls SDK aus irgendeinem Grund fehlschlägt:
- Automatischer Fallback zu REST API
- Funktioniert auf allen Python Versionen
- Transparenter Wechsel ohne Fehler

---

## ✅ Erfolgs-Checkliste

Nach erfolgreichem Build:

- [ ] App startet ohne Crash
- [ ] Frontend ist sichtbar (kein schwarzer Bildschirm)
- [ ] Balance wird angezeigt (nicht €0.00)
- [ ] Trades sind sichtbar
- [ ] Rohstoff-Preise werden aktualisiert
- [ ] Settings lassen sich ändern

---

## 🆘 Hilfe & Support

**Logs Location:**
- Main Log: `~/Library/Logs/Booner Trade/main.log`
- Error Log: `~/Library/Logs/Booner Trade/error.log`

**Dokumentation:**
- `/app/BOONER-TRADE-APP-VOLLSTAENDIGE-DOKUMENTATION.md`
- `/app/electron-app/TROUBLESHOOTING.md`
- `/app/electron-app/BUILD-INSTRUCTIONS.md`

**Weitere Tools:**
- `DEBUG-APP.sh` - Zeigt App-Struktur und startet Backend manuell
- `KILL-PORT-8000.sh` - Gibt Port 8000 frei
- `QUICK-FIX-MAIN-JS.sh` - Kopiert nur main.js (für schnelle Tests)
- `RESTORE-EMERGENT-ENV.sh` - Stellt Emergent .env wieder her

---

**Version:** 2.1  
**Letzte Aktualisierung:** Dezember 2025  
**Status:** ✅ Produktionsreif
