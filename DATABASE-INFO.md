# 💾 DATENBANK-INFORMATION

## ✅ **WICHTIG: Diese App nutzt SQLite, NICHT MongoDB!**

---

## 📊 **Datenbank-Architektur:**

### **SQLite (Lokale Datenbank)**
- **Typ:** Eingebettete Datenbank
- **Datei:** `trading.db`
- **Größe:** ~300 KB
- **Location auf Mac:** 
  ```
  ~/Library/Application Support/booner-trade/database/trading.db
  ```
- **Location Development:**
  ```
  /app/backend/trading.db
  ```

---

## 🔧 **Warum SQLite statt MongoDB?**

### **Vorteile für Desktop App:**
✅ **Keine Server nötig** - App läuft komplett offline
✅ **Schnell** - Keine Netzwerk-Latenz
✅ **Einfach** - Eine Datei, keine Konfiguration
✅ **Portabel** - Datei kann einfach gesichert werden
✅ **Plattformübergreifend** - Funktioniert auf Mac, Windows, Linux

### **MongoDB nur auf Emergent Preview:**
Die MongoDB die Du auf Emergent siehst ist NUR für die Preview-Umgebung.
- Wird vom Container automatisch gestartet
- Hat keine Auswirkung auf die Mac App
- Wird NICHT in der Mac App verwendet

---

## 📁 **Datenbank-Schema:**

### **Tabellen:**

**1. market_data**
- Rohstoffpreise, Indikatoren, Signale
- Aktualisiert alle 15 Sekunden

**2. trades**
- Alle Trades (OPEN & CLOSED)
- Enthält: Entry/Exit, P/L, TP/SL, etc.

**3. market_data_history**
- Historische Marktdaten
- Für Charts und Analysen

**4. trading_settings**
- Trading-Einstellungen
- Strategy, TP/SL, Risiko, etc.

**5. trade_settings**
- Trade-spezifische Settings
- TP/SL pro Trade

---

## 🗄️ **Datenbank-Verwaltung:**

### **Backup erstellen:**
```bash
# Auf Mac
cp ~/Library/Application\ Support/booner-trade/database/trading.db ~/Desktop/backup-$(date +%Y%m%d).db
```

### **Datenbank zurücksetzen:**
```bash
# Auf Mac - löscht ALLE Daten!
rm ~/Library/Application\ Support/booner-trade/database/trading.db
# App startet mit leerer Datenbank
```

### **Datenbank ansehen:**
```bash
# Mit DB Browser for SQLite (Mac App)
# Oder command line:
sqlite3 ~/Library/Application\ Support/booner-trade/database/trading.db

# Dann SQL ausführen:
SELECT * FROM trades LIMIT 10;
SELECT COUNT(*) FROM trades WHERE status='CLOSED';
```

---

## 🔍 **Troubleshooting:**

### **Problem: "Database is locked"**
**Ursache:** Mehrere Zugriffe gleichzeitig
**Lösung:** App neu starten

### **Problem: "No such table"**
**Ursache:** Datenbank wurde noch nicht initialisiert
**Lösung:** App neu starten (erstellt automatisch alle Tabellen)

### **Problem: Trades verschwinden**
**Ursache:** Datenbank wurde zurückgesetzt oder ist korrupt
**Lösung:** Backup wiederherstellen oder neu anfangen

---

## 📊 **Datenbank-Statistiken (Typisch):**

| Tabelle | Rows | Größe |
|---------|------|-------|
| market_data | ~15 | 1 KB |
| trades | 100-1000 | 50-500 KB |
| market_data_history | 1000-10000 | 100-1000 KB |
| trading_settings | 1 | <1 KB |
| trade_settings | 10-100 | 5-50 KB |

**Total:** 200-1500 KB (~300 KB durchschnittlich)

---

## 🚀 **Migration von MongoDB zu SQLite (bereits erledigt):**

Falls Du alte Daten von MongoDB hast:
```bash
python migrate_mongo_to_sqlite.py
```

Aber: Die App nutzt seit v2.3.0+ **NUR noch SQLite**!

---

## ✅ **Zusammenfassung:**

**Für Dich als User:**
- ✅ Keine MongoDB Installation nötig
- ✅ Keine Konfiguration nötig
- ✅ Alles funktioniert out-of-the-box
- ✅ Daten sind in einer Datei
- ✅ Einfach zu sichern
- ✅ Schnell und zuverlässig

**Die MongoDB auf Emergent ignorieren - sie ist nur für die Preview!**
