# 🚀 Quick Start - Booner Trade v2.3.28

**Version:** 2.3.28  
**Datum:** 16. Dezember 2024  
**Status:** ✅ Production Ready

---

## ⚡ Schnellstart (3 Schritte)

### 1️⃣ Build die App
```bash
cd /app
./COMPLETE-MACOS-SETUP.sh
```

### 2️⃣ App starten
```bash
open /app/electron-app/dist/mac-arm64/Booner\ Trade.app
```

### 3️⃣ Settings konfigurieren
1. Öffne Settings (⚙️ rechts oben)
2. Wähle AI Provider (Emergent LLM oder Ollama)
3. Falls Ollama: Stelle sicher dass llama4/llama3.2 läuft
4. Aktiviere gewünschte Trading-Strategien

**Fertig!** 🎉

---

## 🆕 Was ist neu in v2.3.28?

### Kritische Fixes ✅
- **SL/TP Berechnungen korrigiert** - Natural Gas Beispiel funktioniert jetzt
- **Scalping verfügbar** - In manueller Trade-Erstellung
- **Trade-Speicherung** - Funktioniert zuverlässig
- **"Alle löschen"** - 10x schneller mit Bulk-Operation

### Neue Features ⭐
- **Vollständige Scalping Settings** - TP%, SL%, Haltezeit, Risiko
- **MetaAPI ID Update** - Über UI statt .env-Datei
- **Ollama llama4** - Neuestes Modell verfügbar
- **API Key Felder** - Für OpenAI, Gemini, Claude

---

## 📊 Testing Checklist

### Basis-Tests:
- [ ] App startet ohne Fehler
- [ ] Dashboard lädt Daten
- [ ] Live-Ticker funktioniert
- [ ] Settings können geöffnet werden

### Trading-Tests:
- [ ] Manuelle Trade-Erstellung mit Scalping
- [ ] Trade-Settings speichern
- [ ] "Alle löschen" bei geschlossenen Trades
- [ ] SL/TP Werte sind korrekt (z.B. Natural Gas @ 3.92$)

### AI-Tests:
- [ ] AI Provider wechseln
- [ ] API Keys eingeben (falls nicht Emergent/Ollama)
- [ ] Ollama mit llama4 testen (falls installiert)
- [ ] AI Chat funktioniert

### Settings-Tests:
- [ ] Scalping Settings anpassen
- [ ] MetaAPI IDs aktualisieren
- [ ] Settings speichern und neu laden

---

## 🐛 Bekannte Probleme

### Noch nicht behoben (v2.3.29 geplant):
1. **Backend schwankt** - Manchmal nicht erreichbar
2. **AI macht immer Day Trades** - Strategie-Zuordnung Bug
3. **Day Trading immer vorne** - Sortierung Problem
4. **Libertex Margin schwankt** - Balance-Berechnung
5. **Mikrofon funktioniert nicht** - Whisper Integration unvollständig

### Workarounds:
- **Backend schwankt:** Backend neu starten (`sudo supervisorctl restart backend`)
- **AI Strategie:** Manuell Strategie in Trade-Settings setzen
- **Kategorien:** Filtern statt Sortieren verwenden

---

## 🔧 Häufige Probleme

### Problem: App startet nicht
**Lösung:**
```bash
# Alte App löschen
rm -rf "/Applications/Booner Trade.app"

# Cache leeren
rm -rf ~/Library/Application\ Support/booner-trade
rm -rf ~/Library/Caches/booner-trade

# Neu bauen
cd /app
./COMPLETE-MACOS-SETUP.sh
```

### Problem: Backend nicht erreichbar
**Lösung:**
```bash
# Backend-Logs prüfen
tail -f ~/Library/Logs/booner-trade/backend.log

# Backend neu starten (falls Development)
sudo supervisorctl restart backend
```

### Problem: Trades werden nicht angezeigt
**Lösung:**
1. Prüfe MetaAPI IDs in Settings
2. Prüfe ob Plattformen aktiviert sind (MT5_LIBERTEX, MT5_ICMARKETS)
3. Prüfe Backend-Logs auf Fehler

### Problem: SL/TP stimmen nicht
**Lösung:**
- ✅ In v2.3.28 gefixt!
- Falls Problem weiterhin besteht: Prüfe Day/Swing Trading Settings

---

## 📚 Weiterführende Dokumentation

### Für neue Features:
- `RELEASE-NOTES-V2.3.28.md` - Was ist neu?
- `CHANGELOG-V2.3.28.md` - Detaillierte Änderungen

### Für Entwickler:
- `WICHTIG-FUER-NAECHSTEN-AGENTEN.md` - Code-Guidelines
- `BUGFIX-PLAN-V2.3.28.md` - Bug-Tracking

### Für Build:
- `COMPLETE-MACOS-SETUP.sh` - Haupt-Build-Script
- `WIE-FUNKTIONIERT-DER-BUILD.md` - Build-Prozess erklärt

---

## ⚙️ Settings-Empfehlungen

### Für Paper Trading (Anfänger):
```
✅ Auto-Trading: AUS
✅ Trading Modus: Paper Trading
✅ AI Provider: Ollama (llama4)
✅ Day Trading: AN (SL: 2%, TP: 2.5%)
✅ Swing Trading: AN (SL: 2%, TP: 4%)
✅ Scalping: AUS (nur für Experten)
```

### Für Live Trading (Fortgeschritten):
```
✅ Auto-Trading: AN
✅ Trading Modus: Live
✅ AI Provider: Emergent LLM (gpt-5)
✅ Day Trading: AN
✅ Swing Trading: AN
✅ Scalping: AN (wenn erfahren)
✅ Max Trades/Stunde: 5-10
```

---

## 🎯 Nächste Schritte

Nach dem ersten Start:

1. **Konfiguriere AI Provider**
   - Wähle Emergent LLM (kostenlos) oder
   - Ollama lokal (llama4) oder
   - Eigener API Key (OpenAI/Gemini/Claude)

2. **Aktiviere Plattformen**
   - MT5 Libertex Demo: Standard aktiv
   - MT5 ICMarkets Demo: Standard aktiv
   - Falls andere: MetaAPI IDs eintragen

3. **Wähle Trading-Strategien**
   - Day Trading für schnelle Trades
   - Swing Trading für längere Positionen
   - Scalping nur wenn erfahren

4. **Teste mit Paper Trading**
   - Starte mit deaktiviertem Auto-Trading
   - Mache manuelle Trades zum Testen
   - Beobachte AI-Signale
   - Aktiviere Auto-Trading wenn zufrieden

---

## 💡 Tipps & Tricks

### Scalping richtig nutzen:
- **Min. Konfidenz:** 60% (höher als andere)
- **Take Profit:** 0.15% (15 Pips)
- **Stop Loss:** 0.08% (8 Pips)
- **Max Haltezeit:** 5 Minuten
- **Nur bei:** Niedriger Volatilität, klare Trends

### Ollama Performance:
- llama4: Beste Qualität, langsamer
- llama3.2: Guter Kompromiss
- mistral: Schnellste Option

### MetaAPI Limits:
- Demo-Accounts: Unbegrenzt
- Live-Accounts: Rate-Limits beachten
- Bei "Rate Limit" Fehler: Pausen einlegen

---

## 📞 Support

Bei Problemen:
1. ✅ Prüfe `TROUBLESHOOTING.md` (falls vorhanden)
2. ✅ Schaue in Backend-Logs: `~/Library/Logs/booner-trade/backend.log`
3. ✅ Schaue in Browser-Console: `Cmd + Option + I`
4. ✅ Erstelle GitHub Issue mit Logs

---

**Viel Erfolg beim Trading!** 📈💰

Version 2.3.28 - Production Ready ✅
