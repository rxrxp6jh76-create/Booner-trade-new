# 🚀 Booner Trade v2.3.28 - PRODUCTION READY

**KI-gesteuerte Trading-Plattform für MetaTrader 5**

✅ **Status:** Alle kritischen Bugs behoben! Production-ready Version.

## ✨ Was ist neu in v2.3.28?

Diese Version enthält **umfangreiche Bug-Fixes** und **neue Features**:

**Kritische Fixes:**
- ✅ SL/TP Berechnungen korrigiert (2% statt 1%)
- ✅ Scalping in manueller Trade-Erstellung verfügbar
- ✅ Trade-Speicherung funktioniert zuverlässig
- ✅ "Alle löschen" mit Bulk-Endpoint optimiert
- ✅ Scalping Settings vollständig einstellbar
- ✅ MetaAPI ID Update über UI möglich
- ✅ Ollama llama4 Support
- ✅ API Key Felder für alle AI Provider

## 🚀 Schnellstart

### 1. App bauen:
```bash
cd BOONER-V2.3.14

# Alles in einem Schritt (dauert 2-3 Minuten)
./COMPLETE-MACOS-SETUP.sh
```

💡 **Hinweis:** `COMPLETE-MACOS-SETUP.sh` macht ALLES - Sie brauchen `INSTALL.sh` NICHT!

### 2. App finden:
```bash
# Automatisch suchen und öffnen
./FINDE-APP.sh
```

**Oder manuell:**
```
BOONER-V2.3.14/electron-app/dist/mac-arm64/Booner Trade.app
```

### 3. Debug-Logs aktivieren:
- App öffnen
- Developer Console: `Cmd + Option + I`
- Settings ändern und speichern
- Logs in Console und `~/Library/Logs/booner-trade/backend.log` prüfen

## 📋 Wichtige Dateien

- `VERSION-INFO.md` - Detaillierte Änderungen und Anleitung
- `BUILD-UND-FINDEN.md` - Build & Finde-Anleitung
- `FINDE-APP.sh` - Automatisches Such-Skript
- `INSTALL.sh` - Installiert Dependencies
- `COMPLETE-MACOS-SETUP.sh` - Baut die macOS App

## 🔍 Debug-Logs

Die Logs zeigen **jeden Schritt** der SL/TP-Berechnung:
1. Frontend: Werte vor dem Senden
2. Backend: Empfangene Werte
3. Backend: Geladene Prozentsätze aus DB
4. Backend: Mathematische Berechnung
5. Backend: Was in DB geschrieben wird

**Log-Dateien:**
- Frontend: Browser Console (Cmd+Option+I)
- Backend: `~/Library/Logs/booner-trade/backend.log`

## 🎯 Nach dem Testen

**Bitte senden Sie:**
1. Screenshot der Browser Console (Frontend-Logs)
2. Relevante Backend-Log-Zeilen
3. Screenshot der Trades-Tabelle

→ Damit kann ich den Bug sofort finden und beheben!

## 📞 Support

Bei Fragen oder Problemen, bitte melden mit:
- Version: **2.3.14**
- Problem-Beschreibung
- Screenshots/Logs

---

**Version:** 2.3.14 (DEBUG)  
**Build Datum:** 13. Dezember 2024  
**Zweck:** SL/TP Bug Debugging
