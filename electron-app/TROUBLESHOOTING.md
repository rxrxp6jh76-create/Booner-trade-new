# Troubleshooting - Booner Trade macOS App

## 🔍 Häufige Probleme und Lösungen

---

## Problem: Keine Balance sichtbar (€0.00)

### Symptom
- App startet
- UI ist sichtbar
- Aber alle Balances zeigen €0.00
- Keine Trades sichtbar

### Ursache
MetaAPI kann nicht mit den Trading-Accounts verbinden.

### Lösung

**1. Prüfen Sie die Backend-Verbindung:**
```bash
curl http://localhost:8000/api/ping
# Sollte zurückgeben: {"status":"ok"...}

curl http://localhost:8000/api/platforms/LIBERTEX/account
# Sollte Balance anzeigen, NICHT {"detail":"503..."}
```

**2. Wenn 503 Error → .env prüfen:**
```bash
cat "/Applications/Booner Trade.app/Contents/Resources/app/backend/.env" | grep METAAPI_ACCOUNT_ID
```

**Muss enthalten:**
```
METAAPI_ACCOUNT_ID=booner-trade
METAAPI_ICMARKETS_ACCOUNT_ID=booner-trade
```

**Falls falsch (z.B. "trading-desktop"):**
```bash
sudo nano "/Applications/Booner Trade.app/Contents/Resources/app/backend/.env"
# Korrigieren und speichern: Control+O, Enter, Control+X
```

**3. App neu starten:**
```bash
killall "Booner Trade"
open "/Applications/Booner Trade.app"
```

---

## Problem: App zeigt schwarze Seite

### Symptom
- App öffnet sich
- Fenster ist komplett schwarz
- Keine UI sichtbar

### Ursache
Frontend-Build-Dateien fehlen oder falscher Pfad in main.js.

### Lösung

**1. Prüfen Sie ob Frontend-Dateien existieren:**
```bash
ls "/Applications/Booner Trade.app/Contents/Resources/app/frontend/"
# Sollte zeigen: index.html, static/, etc.
```

**2. Developer Console öffnen:**
- In der App: `Cmd + Option + I`
- Schauen Sie nach Fehlern

**3. Wenn "Frontend Build Missing" Fehlermeldung:**
```bash
# Kompletter Rebuild nötig
cd /path/to/project/electron-app
./BUILD-MACOS-COMPLETE.sh
```

---

## Problem: App crashed sofort beim Start

### Symptom
- App öffnet kurz
- Crashed sofort (Fenster schließt sich)

### Ursache
Meist: Backend kann nicht starten (Port belegt, Python fehlt, etc.)

### Lösung

**1. Prüfen Sie ob Port 8000 frei ist:**
```bash
lsof -ti:8000
# Wenn Prozess-ID zurückkommt → Port ist belegt
```

**Port freigeben:**
```bash
kill -9 $(lsof -ti:8000)
```

**2. Prüfen Sie die Logs:**
```bash
# Finden Sie die Log-Dateien
find ~/Library/Logs -name "*Booner*" -o -name "*booner*" 2>/dev/null

# Oder erstellen Sie einen Log-Ordner
mkdir -p ~/Library/Logs/Booner\ Trade/
```

**3. Testen Sie Backend manuell:**
```bash
cd "/Applications/Booner Trade.app/Contents/Resources/app/backend"
/Applications/Booner\ Trade.app/Contents/Resources/app/python/venv/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## Problem: Build-Script hängt

### Symptom
- `BUILD-MACOS-COMPLETE.sh` läuft
- Bleibt bei einem Schritt stehen
- Kein Fortschritt mehr

### Häufige Ursachen

**1. Port 8000 Check hängt:**
```bash
# In neuem Terminal:
bash /path/to/electron-app/KILL-PORT-8000.sh
```

**2. yarn install hängt:**
```bash
# Brechen Sie ab: Ctrl+C
# Löschen Sie node_modules:
cd frontend
rm -rf node_modules
yarn cache clean
yarn install
```

**3. Python venv hängt:**
```bash
# Brechen Sie ab: Ctrl+C
# Löschen Sie alte venv:
rm -rf /path/to/electron-app/resources/python
# Script neu starten
```

---

## Problem: "Permission denied" Fehler

### Symptom
```
cp: /Applications/Booner Trade.app: Permission denied
```

### Lösung
Das Script benötigt sudo-Rechte für `/Applications/`:

```bash
# Das Build-Script fragt automatisch nach sudo-Passwort
./BUILD-MACOS-COMPLETE.sh

# Falls das nicht funktioniert:
sudo ./BUILD-MACOS-COMPLETE.sh
```

---

## Problem: MetaAPI Rate Limit

### Symptom
In Logs:
```
Too Many Requests. Rate limited. Try after a while.
```

### Ursache
MetaAPI erlaubt nur begrenzte Anfragen pro Minute.

### Lösung
**Warten Sie 1-2 Minuten**, dann sollte es wieder funktionieren.

Die App hat Caching eingebaut (5 Sekunden), um Rate Limits zu vermeiden.

---

## Debugging-Tipps

### Developer Console in der App
```
Cmd + Option + I
```
Zeigt:
- JavaScript Fehler
- Network Requests
- Console Logs

### Backend Logs überprüfen
```bash
# In der App-Console schauen (Cmd+Option+I):
# - "Backend: ..." Meldungen zeigen Backend-Status

# Oder manuell Backend starten um Logs zu sehen:
cd "/Applications/Booner Trade.app/Contents/Resources/app/backend"
source ../python/venv/bin/activate
python3 server.py
```

### Netzwerk-Requests prüfen
1. Developer Console öffnen (`Cmd+Option+I`)
2. "Network" Tab
3. Seite refreshen (`Cmd+R`)
4. Schauen Sie welche API-Calls fehlschlagen (rot)

---

## Kontakte & Support

**Logs Location:**
- `~/Library/Logs/Booner Trade/main.log`
- `~/Library/Logs/Booner Trade/error.log`

**Dokumentation:**
- `/app/BOONER-TRADE-APP-VOLLSTAENDIGE-DOKUMENTATION.md`
- `/app/electron-app/BUILD-INSTRUCTIONS.md`
- `/app/electron-app/CHANGELOG.md`

**Bei Problemen:**
1. Prüfen Sie zuerst die Developer Console
2. Testen Sie Backend-Endpunkte mit curl
3. Schauen Sie in die Logs
4. Bei MetaAPI-Problemen: Rate Limit abwarten

---

## Kompletter Neustart (Clean Slate)

Falls alles fehlschlägt:

```bash
# 1. App komplett entfernen
sudo rm -rf "/Applications/Booner Trade.app"
rm -rf ~/Library/Application\ Support/Booner\ Trade/
rm -rf ~/Library/Logs/Booner\ Trade/

# 2. Projekt neu auschecken
cd ~/Projects  # Oder Ihr Projekt-Ordner
git clone <repository-url>
cd booner-trade

# 3. Kompletter Rebuild
cd electron-app
./BUILD-MACOS-COMPLETE.sh

# 4. Prüfen Sie die .env in der installierten App
cat "/Applications/Booner Trade.app/Contents/Resources/app/backend/.env"
# METAAPI_ACCOUNT_ID sollte NICHT "trading-desktop" sein!
```

---

**Letzte Aktualisierung:** Dezember 2025  
**Version:** 2.1
