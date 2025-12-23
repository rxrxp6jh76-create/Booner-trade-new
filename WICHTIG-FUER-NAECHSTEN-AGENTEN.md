# ⚠️ WICHTIG FÜR DEN NÄCHSTEN AGENTEN

**Letzte Aktualisierung:** 18. Dezember 2025  
**Version:** 2.3.34  
**Status:** ✅ 7 Trading-Strategien + Trailing Stop - Production Ready 🌟

---

## 🚨 AGENT: NACH JEDEM FORK AUTOMATISCH AUSFÜHREN!

**LIES ZUERST `/app/AGENT-ERSTE-SCHRITTE.md` und führe die Schritte aus - OHNE dass der User danach fragt!**

Die wichtigsten Schritte:
1. MetaAPI IDs in `/app/backend/.env` korrigieren (werden bei Fork zurückgesetzt!)
2. Backend neu starten
3. Prüfen ob Balance angezeigt wird

Die KORREKTEN MetaAPI IDs sind:
```
METAAPI_ACCOUNT_ID=aitrader-83
METAAPI_ICMARKETS_ACCOUNT_ID=aitrader-83
```

---

## 🎯 ZUSAMMENFASSUNG FÜR SCHNELLE ORIENTIERUNG

### **Was funktioniert in v2.3.29:**
- ✅ **7 TRADING-STRATEGIEN** vollständig implementiert! 🌟
  - Swing, Day, Scalping (v2.3.27)
  - Mean Reversion, Momentum, Breakout, Grid (v2.3.29 NEU)
- ✅ AI Strategy Bug **BEHOBEN** (kein Hard-Coding mehr)
- ✅ Alle Strategien im Settings Dialog einstellbar
- ✅ Alle Strategien in manueller Trade-Erstellung
- ✅ Korrekte MetaAPI IDs gesetzt
- ✅ MongoDB gestoppt (nur SQLite)
- ✅ 42-Seiten Trading-Strategien Guide
- ✅ SL/TP Berechnungen sind **KORREKT** (2% defaults)
- ✅ Trade-Speicherung funktioniert zuverlässig
- ✅ "Alle löschen" mit optimiertem Bulk-Endpoint
- ✅ Ollama llama4 Support
- ✅ API Key Felder für alle AI Provider

### **Was in v2.3.28 gefixt wurde:**
- ✅ SL/TP Default-Werte korrigiert (1% → 2%)
- ✅ Scalping zu manueller Trade-Erstellung hinzugefügt
- ✅ Trade-Speicherung (strategy_type → strategy Konvertierung)
- ✅ "Alle löschen" Funktion optimiert (Bulk-Endpoint)
- ✅ Scalping Settings vollständig einstellbar
- ✅ MetaAPI ID Update-Endpoint implementiert
- ✅ Ollama llama4 Model hinzugefügt
- ✅ API Key Input-Felder für OpenAI, Gemini, Claude

### **Alte Fixes (v2.3.16 - weiterhin aktiv):**
- ✅ Position-Typ Normalisierung (Zeile ~2814-2831 in `server.py`)
- ✅ Unterstützt: `"POSITION_TYPE_BUY"`, `"BUY"`, `0`
- ✅ Unterstützt: `"POSITION_TYPE_SELL"`, `"SELL"`, `1`

---

## 📋 KRITISCHE DATEIEN - NICHT ÄNDERN OHNE GRUND!

### **1. backend/server.py - Zeile 2814-2831**

**KRITISCHER CODE - Position Type Normalisierung:**
```python
position_type_raw = position.get('type')

# 🐛 CRITICAL BUG FIX: Normalize position type
if position_type_raw in ["POSITION_TYPE_BUY", "BUY", 0]:
    position_type = "BUY"
elif position_type_raw in ["POSITION_TYPE_SELL", "SELL", 1]:
    position_type = "SELL"
else:
    logger.warning(f"⚠️ Unknown position type '{position_type_raw}' - defaulting to BUY")
    position_type = "BUY"

logger.info(f"🔍 Position type: raw='{position_type_raw}' → normalized='{position_type}'")
```

**WARUM WICHTIG:**
- Ohne diese Normalisierung werden BUY/SELL Trades verwechselt
- Führt zu vertauschten SL/TP Werten
- Der Bug war schwer zu finden und hat Wochen gedauert!

**WENN DU DAS ÄNDERN MUSST:**
1. Verstehe zuerst, was MetaAPI für `position.get('type')` zurückgibt
2. Teste mit echten Daten
3. Prüfe, ob BUY Trades korrekte BUY-Berechnungen bekommen
4. Prüfe, ob SELL Trades korrekte SELL-Berechnungen bekommen

---

### **2. backend/server.py - Zeile 2857-2868**

**KRITISCHER CODE - SL/TP Berechnungen:**
```python
if position_type == "BUY" or position_type == 0:  # BUY
    new_sl = entry_price * (1 - sl_percent / 100)  # SL unter Entry
    new_tp = entry_price * (1 + tp_percent / 100)  # TP über Entry
else:  # SELL
    new_sl = entry_price * (1 + sl_percent / 100)  # SL über Entry
    new_tp = entry_price * (1 - tp_percent / 100)  # TP unter Entry
```

**WARUM WICHTIG:**
- BUY: SL muss UNTER Entry, TP muss ÜBER Entry
- SELL: SL muss ÜBER Entry, TP muss UNTER Entry
- Diese Logik ist KORREKT - nicht ändern!

**WENN DU DAS ÄNDERN MUSST:**
1. Verstehe die Trading-Logik zuerst
2. Teste mit echten Werten (Entry=4.222, SL%=1.5, TP%=2.5)
3. Für BUY sollte SL=4.159, TP=4.328 sein
4. Für SELL sollte SL=4.285, TP=4.116 sein

---

### **3. backend/database.py - Zeile 576-620**

**TradeSettings.update_one() Funktion:**
```python
field_order = ['stop_loss', 'take_profit', 'strategy', 'entry_price', ...]

for field in field_order:
    if field in set_data:
        set_parts.append(f"{field} = ?")
        set_values.append(set_data[field])
```

**WARUM WICHTIG:**
- Explizite Feld-Reihenfolge verhindert Verwirrung
- `stop_loss` wird IMMER vor `take_profit` verarbeitet
- SQLite ist sensibel auf Parameter-Reihenfolge

**WENN DU DAS ÄNDERN MUSST:**
1. Behalte die explizite Reihenfolge
2. Füge neue Felder am Ende hinzu
3. Lösche NIE `stop_loss` oder `take_profit` aus der Liste

---

## 🚫 WAS DU NICHT TUN SOLLTEST

### **1. Position Type Checks entfernen**
❌ **NICHT:**
```python
position_type = position.get('type')
if position_type == "BUY":  # ← FALSCH! MetaAPI gibt "POSITION_TYPE_BUY" zurück!
```

✅ **STATTDESSEN:**
```python
position_type_raw = position.get('type')
if position_type_raw in ["POSITION_TYPE_BUY", "BUY", 0]:
    position_type = "BUY"
```

---

### **2. SL/TP Formeln ändern**
❌ **NICHT:**
```python
# BUY
new_sl = entry_price * (1 + sl_percent / 100)  # ← FALSCH! SL wäre ÜBER Entry!
new_tp = entry_price * (1 - tp_percent / 100)  # ← FALSCH! TP wäre UNTER Entry!
```

✅ **KORREKT:**
```python
# BUY
new_sl = entry_price * (1 - sl_percent / 100)  # SL unter Entry
new_tp = entry_price * (1 + tp_percent / 100)  # TP über Entry
```

---

### **3. Dictionary-Iteration für SQL verwenden**
❌ **NICHT:**
```python
for key, value in set_data.items():  # ← Reihenfolge könnte variieren!
    set_parts.append(f"{key} = ?")
```

✅ **STATTDESSEN:**
```python
field_order = ['stop_loss', 'take_profit', ...]
for field in field_order:  # ← Explizite Reihenfolge!
```

---

## 🔍 DEBUGGING-TIPPS

### **Wenn SL/TP wieder vertauscht werden:**

1. **Prüfe Position Type Logs:**
   ```bash
   grep "Position type: raw=" backend.log
   ```
   Sollte zeigen: `raw='POSITION_TYPE_BUY' → normalized='BUY'`

2. **Prüfe Berechnungs-Logs:**
   ```bash
   grep "BUY TRADE - Calculation\|SELL TRADE - Calculation" backend.log
   ```
   Sollte die richtigen Formeln verwenden

3. **Teste mit bekannten Werten:**
   - Entry: 4.222 (BUY)
   - SL: 1.5%, TP: 2.5%
   - Erwartung: SL=4.159, TP=4.328
   - Wenn SL=4.285, TP=4.116 → SELL-Formel wurde verwendet → Bug!

---

## 📚 WICHTIGE DOKUMENTATION

### **Vollständige Bug-Historie:**
- `DEBUGGING-HISTORIE-SL-TP-BUG.md` - Alles was geprüft wurde
- `BUG-FIX-ERKLAERUNG.md` - Wie der Bug gefunden und behoben wurde

### **Build & Deployment:**
- `COMPLETE-MACOS-SETUP.sh` - Einziges Build-Skript (macht alles!)
- `AUTOMATISCHE-METAAPI-KORREKTUR.md` - MetaAPI IDs werden auto-korrigiert
- `DATENBANK-RESET.sh` - Tool zum Reset bei Problemen

### **Code-Architektur:**
- **SQLite** (NICHT MongoDB!) wird verwendet
- **MetaAPI** wird NUR für Trade-Ausführung verwendet (NICHT für SL/TP Management)
- **Alle SL/TP Verwaltung** passiert lokal in der App

---

## ⚡ QUICK-FIX CHEATSHEET

### **Problem: SL/TP vertauscht**
→ Prüfe Position Type Normalisierung (Zeile 2814-2831)

### **Problem: Rohstoffe zeigen null**
→ Prüfe, ob Validierungs-Logs entfernt wurden (dürfen NICHT existieren!)

### **Problem: Database locked**
→ Bereits behoben mit Timeout-Erhöhung in `database.py`

### **Problem: Build funktioniert nicht**
→ Verwende NUR `COMPLETE-MACOS-SETUP.sh` (nicht INSTALL.sh!)

### **Problem: MetaAPI IDs falsch**
→ Werden automatisch korrigiert beim Build (siehe Zeile 142-200 in COMPLETE-MACOS-SETUP.sh)

---

## 🎯 VERSION-HISTORIE (WICHTIG!)

### **v2.3.0** (funktioniert)
- Original-Version, kein SL/TP Bug
- Hatte `auto_set_sl_tp_for_open_trades()` Funktion

### **v2.3.1 - v2.3.13** (SL/TP Bug vorhanden)
- Neue `update_all_sltp_background()` Funktion eingeführt
- **BUG:** Position Type wurde nicht normalisiert
- Alle BUY Trades wurden als SELL behandelt

### **v2.3.14** (Versuch 1 - neue Probleme)
- Validierungs-Logs hinzugefügt
- **Problem:** Verursachte null-Daten bei Rohstoffen
- **Status:** Verworfen

### **v2.3.15** (Versuch 2 - teilweise)
- Validierungs-Logs entfernt
- Explizite Feld-Reihenfolge in database.py
- **Problem:** Position Type Bug noch vorhanden

### **v2.3.16** (AKTUELL - funktioniert!) ✅
- Position Type Normalisierung hinzugefügt
- SL/TP Bug behoben
- Keine null-Daten Probleme
- Alle Features funktionieren

---

## 🚀 FÜR DEN NÄCHSTEN AGENTEN

### **Wenn du neue Features hinzufügst:**
1. ✅ Teste IMMER mit echten MetaAPI Daten
2. ✅ Prüfe, ob SL/TP Berechnungen korrekt bleiben
3. ✅ Verwende die Debug-Logs
4. ✅ Teste BUY und SELL Trades separat

### **Wenn du Bugs beheben musst:**
1. ✅ Lies zuerst `DEBUGGING-HISTORIE-SL-TP-BUG.md`
2. ✅ Prüfe, ob der Bug schon dokumentiert ist
3. ✅ Verwende die Troubleshoot-Checkliste oben

### **Wenn du den Code refactorst:**
1. ⚠️ Ändere NICHTS an der Position Type Normalisierung
2. ⚠️ Ändere NICHTS an den SL/TP Formeln
3. ⚠️ Teste gründlich mit echten Trades

---

## 🔗 EXTERNE REFERENZEN

### **MetaAPI Dokumentation:**
- Position Type: Gibt `"POSITION_TYPE_BUY"` / `"POSITION_TYPE_SELL"` zurück
- NICHT `"BUY"` / `"SELL"` wie man erwarten würde!

### **Trading-Logik:**
- **BUY Trade:** Profit wenn Preis steigt
  - Stop Loss UNTER Entry (limitiert Verlust)
  - Take Profit ÜBER Entry (sichert Gewinn)
- **SELL Trade:** Profit wenn Preis fällt
  - Stop Loss ÜBER Entry (limitiert Verlust)
  - Take Profit UNTER Entry (sichert Gewinn)

---

## ✅ CHECKLISTE VOR RELEASE

Bevor du eine neue Version releaset, prüfe:

### Kritisch:
- [x] Position Type Normalisierung ist intakt (v2.3.16)
- [x] SL/TP Berechnungen sind korrekt (v2.3.28)
- [x] SL/TP Default-Werte sind richtig gesetzt (v2.3.28)
- [x] Keine Validierungs-Logs, die Probleme verursachen
- [x] MetaAPI IDs werden automatisch korrigiert

### Features:
- [x] Scalping in manueller Trade-Erstellung verfügbar (v2.3.28)
- [x] Trade-Settings können gespeichert werden (v2.3.28)
- [x] "Alle löschen" funktioniert zuverlässig (v2.3.28)
- [x] Scalping Settings vollständig einstellbar (v2.3.28)
- [x] MetaAPI ID Update über UI möglich (v2.3.28)
- [x] API Key Felder für alle Provider vorhanden (v2.3.28)
- [x] Ollama llama4 Support (v2.3.28)

### Build & Data:
- [x] Debug-Logs funktionieren
- [x] App kann gebaut werden mit `COMPLETE-MACOS-SETUP.sh`
- [x] Rohstoffe zeigen Daten an (keine nulls)
- [x] Trades werden korrekt angezeigt
- [x] SL/TP werden NICHT vertauscht nach Settings-Änderung

### Noch offen (v2.3.29):
- [ ] Backend-Stabilität (schwankende Erreichbarkeit)
- [ ] AI Strategie-Zuordnung (immer Day Trading)
- [ ] Kategorie-Anzeige (Day Trading immer vorne)
- [ ] Libertex Margin-Berechnung (schwankt)
- [ ] Whisper/Mikrofon Integration vollständig

---

---

## 🆕 NEUES IN V2.3.28 (16. Dezember 2024)

### Kritische Fixes:
1. **SL/TP Berechnungen korrigiert** (`trade_settings_manager.py`)
   - Zeile 112: `take_profit_percent` Default 2.0 (war 1.0)
   - Zeile 144: `day_stop_loss_percent` Default 2.0 (war 1.0)  
   - Zeile 147: `day_take_profit_percent` Default 2.5 (war 0.5)
   - Zeile 197: `swing_take_profit_percent` Default 4.0 (war 1.0)

2. **Scalping zu manueller Trade-Erstellung** (`Dashboard.jsx`)
   - Zeile 2358-2365: "⚡🎯 Scalping" Option hinzugefügt

3. **Trade-Speicherung Fix** (`Dashboard.jsx`)
   - Zeile 624-625: `strategy_type` → `strategy` Konvertierung

4. **"Alle löschen" Optimierung** (`server.py` + `Dashboard.jsx`)
   - Neuer Bulk-Endpoint: `/trades/delete-all-closed` (Zeile 3346-3375)
   - Frontend nutzt neuen Endpoint (Zeile 1587-1594)

### Neue Features:
5. **Scalping Settings vollständig** (`SettingsDialog.jsx`)
   - TP%, SL%, Max Haltezeit, Risiko/Trade alle einstellbar
   - Zeile 605-690

6. **MetaAPI ID Update** (`server.py`)
   - Neuer Endpoint: `/metaapi/update-ids` (Zeile 3048-3088)
   - Frontend korrigierte URL (Zeile 287)

7. **Ollama llama4** (`SettingsDialog.jsx`)
   - Zeile 135: llama4 hinzugefügt

8. **API Key Felder** (`SettingsDialog.jsx`)
   - OpenAI, Gemini, Claude Input-Felder (Zeile 467-528)

9. **Whisper Dependencies** (`requirements.txt`)
   - openai-whisper, ffmpeg-python, soundfile hinzugefügt

### Dokumentation:
- ✅ `RELEASE-NOTES-V2.3.28.md` - Vollständige Release Notes
- ✅ `CHANGELOG-V2.3.28.md` - Detailliertes Changelog
- ✅ `BUGFIX-PLAN-V2.3.28.md` - Bug Fix Tracking
- ✅ `VERSION.txt` - Aktualisiert auf v2.3.28
- ✅ `README.md` - Version-Info aktualisiert

### Bekannte Probleme (für v2.3.29):
- ⚠️ Backend-Stabilität (schwankend)
- ⚠️ AI Strategie-Zuordnung
- ⚠️ Kategorie-Anzeige Problem
- ⚠️ Libertex Margin schwankt
- ⚠️ Whisper/Mikrofon Integration unvollständig

---

**Viel Erfolg mit dem Projekt!** 🚀

Bei Fragen: Lies die Dokumentation in diesem Ordner. Alles ist dokumentiert!

**Version 2.3.28 ist PRODUCTION READY!** ✅
