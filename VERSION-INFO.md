# 🔖 Booner Trade Version 2.3.14

## 🐛 Debug-Version für SL/TP Vertauschungs-Bug

**Release Datum:** 13. Dezember 2024

### 🎯 Zweck dieser Version:
Diese Version enthält **umfangreiche Debug-Logs**, um den kritischen Bug zu finden, bei dem Stop Loss und Take Profit Werte nach dem Speichern der Settings vertauscht werden.

### ✨ Änderungen gegenüber v2.3.13:

#### **Frontend** (`SettingsDialog.jsx`):
- ✅ Neue Console-Logs zeigen SL/TP-Werte **vor** dem Senden ans Backend
- ✅ Separate Ausgabe für Day Trading und Swing Trading
- ✅ Zeigt alle 4 Werte: day_sl, day_tp, swing_sl, swing_tp

#### **Backend** (`server.py`):
- ✅ Logs beim Empfangen der Settings vom Frontend
- ✅ Logs vor dem Speichern in die Datenbank
- ✅ **Detaillierte Logs in `update_all_sltp_background()`:**
  - Welche Strategie verwendet wird (Day/Swing)
  - Geladene Prozentsätze aus Settings
  - Komplette mathematische Berechnung von SL/TP
  - Position-Type und Entry-Price
  - Finale gerundete Werte
  - Was in die Datenbank geschrieben wird

### 📋 So verwenden Sie diese Debug-Version:

1. **App bauen:**
   ```bash
   cd BOONER-V2.3.14
   ./COMPLETE-MACOS-SETUP.sh
   ```
   
   💡 **Hinweis:** Ein Skript reicht - es macht alles (Dependencies + Build)!

2. **App öffnen und Developer Console aktivieren:**
   - Drücken Sie: `Cmd + Option + I`

3. **Settings ändern:**
   - Gehen Sie zu Trading Strategien
   - Ändern Sie Day oder Swing Trading SL/TP
   - Klicken Sie "Speichern"

4. **Logs analysieren:**
   - **Browser Console:** Frontend-Logs
   - **Backend Log:** `~/Library/Logs/booner-trade/backend.log`
   - Oder im Terminal: `tail -f ~/Library/Logs/booner-trade/backend.log`

### 🔍 Was die Logs zeigen:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 FRONTEND: Sending settings to backend...
Day Trading:
  - day_stop_loss_percent: 1.5
  - day_take_profit_percent: 2.5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 BACKEND: Received settings from frontend...
Day Trading:
  - day_stop_loss_percent: 1.5
  - day_take_profit_percent: 2.5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 STRATEGY=DAY: Loaded from settings:
   sl_percent (from day_stop_loss_percent) = 1.5%
   tp_percent (from day_take_profit_percent) = 2.5%

🔍 BUY TRADE - Calculation:
   new_sl = 2500.00 * (1 - 1.5/100) = 2462.50
   new_tp = 2500.00 * (1 + 2.5/100) = 2562.50

🔍 WRITING TO DATABASE:
   trade_id = mt5_12345
   stop_loss = 2462.50
   take_profit = 2562.50
```

### 🎯 Nächste Schritte:

Nach dem Testen **BITTE senden Sie mir:**
1. Screenshot der Browser Console
2. Relevante Zeilen aus `backend.log`
3. Screenshot der Trades-Tabelle (wo die Werte vertauscht sind)

Mit diesen Logs kann ich **sofort** sehen, wo die Vertauschung passiert und den Bug beheben!

---

## 📦 App-Speicherort:

Nach dem Build:
```
BOONER-V2.3.14/electron-app/dist/mac-arm64/Booner Trade.app
```

## 🔧 Bekannte Probleme:

- ❌ SL/TP-Werte werden nach Settings-Speicherung vertauscht (wird mit dieser Version debuggt)
- ⚠️ "database is locked" Fehler (Retry-Mechanismus vorhanden)

## 📝 Nächste Version (2.3.15):

Wird den Bug-Fix enthalten, sobald die Root-Cause gefunden wurde!
