# 🚀 Booner Trade - macOS Installation (Fresh Start)

## 📋 Komplette Neu-Installation auf dem Mac

Diese Anleitung führt Sie durch eine **komplette Neu-Installation** der Booner Trade Desktop-App auf macOS.

---

## ⚠️ WICHTIG: Voraussetzungen

- **macOS:** ARM64 (M1/M2/M3/M4 Chip)
- **Internet-Verbindung:** Für Downloads
- **Admin-Rechte:** Für Installation von Homebrew und Tools
- **Freier Speicherplatz:** Mindestens 2 GB

---

## 🔧 Schritt-für-Schritt Anleitung

### 1️⃣ Alten App-Ordner löschen

Öffnen Sie das Terminal und führen Sie aus:

```bash
# Alte App löschen falls vorhanden
rm -rf /Applications/"Booner Trade.app"

# Alten Code-Ordner löschen (falls vorhanden)
cd ~
rm -rf Booner-Trade  # oder wo auch immer der alte Ordner war
```

---

### 2️⃣ Frischen Code von GitHub ziehen

```bash
# Neues Verzeichnis erstellen
cd ~
git clone https://github.com/IHR-USERNAME/Booner-Trade.git
cd Booner-Trade
```

**ODER falls Sie bereits einen lokalen Ordner haben:**

```bash
cd ~/Booner-Trade  # oder Ihr Pfad
git fetch --all
git reset --hard origin/main  # ACHTUNG: Löscht lokale Änderungen!
git pull origin main
```

---

### 3️⃣ Setup-Script ausführen

Jetzt kommt das magische Script, das **ALLES** automatisch macht:

```bash
sh COMPLETE-MACOS-SETUP.sh
```

**Das Script wird:**

✅ Homebrew installieren (falls nicht vorhanden)  
✅ Python 3.11 installieren  
✅ Node.js & Yarn installieren  
✅ Backend Dependencies installieren  
✅ Frontend Dependencies installieren  
✅ Frontend bauen  
✅ Python venv erstellen  
✅ Alle Files kopieren  
✅ Electron App bauen  
✅ App nach /Applications installieren  
✅ App starten  

**⏱️ Dauer:** Ca. 10-15 Minuten beim ersten Mal

---

### 4️⃣ App ist gestartet! ✅

Die App sollte sich automatisch öffnen. Falls nicht:

```bash
open "/Applications/Booner Trade.app"
```

---

## 🔍 Überprüfen ob SDK läuft

Öffnen Sie die Logs:

```bash
tail -f ~/Library/Logs/Booner\ Trade/main.log
```

**Sie sollten sehen:**

✅ **SDK läuft (RICHTIG):**
```
✅ SDK Connected: MT5_LIBERTEX_DEMO | Balance: €55201.45
✅ SDK Connected: MT5_ICMARKETS_DEMO | Balance: €2500.90
```

❌ **REST API als Fallback (NICHT GEWÜNSCHT):**
```
✅ Connected via REST API fallback
```

---

## 🐛 Fehlerbehandlung

### Problem: App startet nicht

**Lösung 1: Port 8000 prüfen**
```bash
lsof -ti:8000
# Falls PID angezeigt wird:
kill -9 $(lsof -ti:8000)
```

**Lösung 2: Logs prüfen**
```bash
cat ~/Library/Logs/Booner\ Trade/error.log
```

---

### Problem: "Permission denied" beim SDK

Das sollte mit dem Monkey-Patch nicht mehr passieren. Falls doch:

```bash
# MetaAPI Cache Verzeichnis erstellen
mkdir -p ~/Library/Application\ Support/Booner\ Trade/.metaapi
chmod -R 755 ~/Library/Application\ Support/Booner\ Trade
```

---

### Problem: .env Datei fehlt oder falsche IDs

**Prüfen:**
```bash
cat ~/Booner-Trade/backend/.env | grep METAAPI_ACCOUNT_ID
```

**Sollte zeigen:**
```
METAAPI_ACCOUNT_ID=trade-connect-65
METAAPI_ICMARKETS_ACCOUNT_ID=trade-connect-65
```

**Falls falsch, korrigieren:**
```bash
nano ~/Booner-Trade/backend/.env
# Dann App neu bauen:
sh ~/Booner-Trade/COMPLETE-MACOS-SETUP.sh
```

---

## 📂 Wichtige Verzeichnisse

| Was | Wo |
|-----|-----|
| **App** | `/Applications/Booner Trade.app` |
| **Logs** | `~/Library/Logs/Booner Trade/` |
| **Datenbank** | `~/Library/Application Support/Booner Trade/database/` |
| **MetaAPI Cache** | `~/Library/Application Support/Booner Trade/.metaapi/` |
| **Code** | `~/Booner-Trade/` (oder Ihr Pfad) |

---

## 🆘 Support

Bei Problemen:

1. **Logs prüfen:** `~/Library/Logs/Booner Trade/main.log`
2. **Error Log prüfen:** `~/Library/Logs/Booner Trade/error.log`
3. **Backend-Prozess prüfen:** `ps aux | grep uvicorn`
4. **Port prüfen:** `lsof -ti:8000`

---

## 🔄 App neu bauen (nach Code-Änderungen)

Falls Sie Code-Änderungen von Git ziehen:

```bash
cd ~/Booner-Trade
git pull
sh COMPLETE-MACOS-SETUP.sh
```

Das Script erkennt bereits installierte Tools und überspringt diese.

---

## ✅ Checkliste

- [ ] Alten App-Ordner gelöscht
- [ ] Code frisch von Git gezogen
- [ ] `COMPLETE-MACOS-SETUP.sh` ausgeführt
- [ ] App startet und zeigt Dashboard
- [ ] Logs zeigen "SDK Connected"
- [ ] EURUSD Trade kann geöffnet werden

---

**🎉 Fertig! Viel Erfolg mit Booner Trade!**
