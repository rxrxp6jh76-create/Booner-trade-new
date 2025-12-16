# 🚀 Booner Trade - App Bauen und Finden

## Schritt 1: App Bauen

Führen Sie **EIN** Skript aus (macht alles):

```bash
cd /pfad/zu/BOONER-V2.3.14

# Alles in einem Schritt
./COMPLETE-MACOS-SETUP.sh
```

💡 **Wichtig:** Sie brauchen `INSTALL.sh` NICHT - `COMPLETE-MACOS-SETUP.sh` macht alles!

## Schritt 2: App Finden

Nach dem erfolgreichen Build finden Sie die App hier:

```
BOONER-V2.3.13/electron-app/dist/mac-arm64/Booner Trade.app
```

**Vollständiger Pfad:**
```
/pfad/zu/BOONER-V2.3.13/electron-app/dist/mac-arm64/Booner Trade.app
```

## Schritt 3: App Öffnen

### Methode A: Finder
1. Öffnen Sie den Finder
2. Navigieren Sie zu: `BOONER-V2.3.13/electron-app/dist/mac-arm64/`
3. Doppelklick auf `Booner Trade.app`

### Methode B: Terminal
```bash
cd BOONER-V2.3.13/electron-app/dist/mac-arm64
open "Booner Trade.app"
```

## 🔍 App nicht gefunden?

Falls die App nicht existiert, überprüfen Sie:

```bash
# Prüfen Sie, ob der Build-Ordner existiert
ls -la electron-app/dist/

# Suchen Sie nach .app Dateien
find electron-app/dist -name "*.app" -type d
```

## 📋 Developer Console öffnen (für Debug-Logs)

Wenn die App läuft:
- Drücken Sie: `Cmd + Option + I`
- Oder im Menü: `View → Developer → Developer Tools`

## 🐛 Debug-Logs finden

Die Logs der App finden Sie hier:
```
~/Library/Logs/booner-trade/backend.log
~/Library/Logs/booner-trade/frontend.log
```

Oder im Terminal:
```bash
tail -f ~/Library/Logs/booner-trade/backend.log
```

## ⚠️ Erste Start-Warnung

Beim ersten Start kann macOS eine Sicherheitswarnung zeigen:
1. Klicken Sie auf "Abbrechen"
2. Gehen Sie zu: **Systemeinstellungen → Sicherheit**
3. Klicken Sie auf "Trotzdem öffnen"
4. Bestätigen Sie mit "Öffnen"

## 🎯 Version 2.3.14 mit Debug-Logs

Diese Version enthält umfangreiche Debug-Logs für den SL/TP Bug!
Bitte öffnen Sie die Developer Console beim Testen.
