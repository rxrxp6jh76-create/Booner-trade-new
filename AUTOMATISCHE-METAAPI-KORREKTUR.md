# 🔧 Automatische MetaAPI ID Korrektur

## ✅ Was ist neu in v2.3.14?

Das Build-Skript `COMPLETE-MACOS-SETUP.sh` prüft und korrigiert jetzt **automatisch** die MetaAPI Account IDs!

## 🎯 Problem gelöst:

**Vorher:** Nach jedem Fork oder bei falschen IDs musste man manuell die .env Datei korrigieren.

**Jetzt:** Das Build-Skript macht das automatisch! ✨

---

## 🔍 Wie funktioniert es?

### **Beim Build:**

```bash
./COMPLETE-MACOS-SETUP.sh
```

### **Das Skript:**

1. **Liest die aktuellen IDs** aus `backend/.env`
2. **Vergleicht mit den korrekten IDs** aus der Dokumentation
3. **Korrigiert automatisch**, falls falsch
4. **Erstellt ein Backup** (`.env.backup.YYYYMMDD_HHMMSS`)
5. **Zeigt an**, welche IDs korrigiert wurden

---

## 📋 Die EINZIG KORREKTEN IDs:

```bash
# MT5 Libertex Demo (MT5-510038543)
METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941

# MT5 ICMarkets Demo (MT5-52565616)
METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39
```

⚠️ **AGENT: Nach JEDEM Fork diese IDs automatisch in `/app/backend/.env` setzen!**
Siehe `/app/AGENT-ERSTE-SCHRITTE.md` für Details.

---

## 🖥️ Was Sie sehen werden:

### **Fall 1: IDs sind korrekt**
```bash
⚙️ Backend .env Datei prüfen und korrigieren...
🔍 Prüfe MetaAPI Account IDs...
   ✅ Libertex ID korrekt
   ✅ ICMarkets ID korrekt
✅ MetaAPI Account IDs sind jetzt garantiert korrekt!
   Libertex Demo: 5cc9abd1-671a-447e-ab93-5abbfe0ed941
   ICMarkets Demo: d2605e89-7bc2-4144-9f7c-951edd596c39
```

### **Fall 2: IDs werden korrigiert**
```bash
⚙️ Backend .env Datei prüfen und korrigieren...
🔍 Prüfe MetaAPI Account IDs...
⚠️  Libertex ID ist falsch: 'metatrade-hub'
   Korrigiere zu: 5cc9abd1-671a-447e-ab93-5abbfe0ed941
   ✅ Libertex ID korrigiert!
⚠️  ICMarkets ID ist falsch: 'metatrade-hub'
   Korrigiere zu: d2605e89-7bc2-4144-9f7c-951edd596c39
   ✅ ICMarkets ID korrigiert!
✅ MetaAPI Account IDs sind jetzt garantiert korrekt!
   Libertex Demo: 5cc9abd1-671a-447e-ab93-5abbfe0ed941
   ICMarkets Demo: d2605e89-7bc2-4144-9f7c-951edd596c39
```

---

## 🔒 Sicherheit:

### **Automatisches Backup:**
Wenn IDs korrigiert werden, wird automatisch ein Backup erstellt:
```
backend/.env.backup.20241213_143022
```

So können Sie bei Bedarf zur alten Version zurückkehren.

---

## 💡 Vorteile:

✅ **Nach jedem Fork:** IDs werden automatisch korrigiert  
✅ **Keine manuellen Änderungen:** Vergessen Sie nie wieder die IDs  
✅ **Fehlersicher:** Die App hat immer die korrekten IDs  
✅ **Transparent:** Sie sehen genau, was korrigiert wurde  
✅ **Sicher:** Automatisches Backup vor Änderungen  

---

## 🎯 Zusammenfassung:

**Sie müssen NIE wieder an die MetaAPI IDs denken!**

Einfach nur:
```bash
./COMPLETE-MACOS-SETUP.sh
```

Das Skript stellt sicher, dass die IDs **immer korrekt** sind! 🚀

---

## 📝 Technische Details:

### **Skript-Logik:**
```bash
# Korrekte IDs definiert
CORRECT_LIBERTEX_ID="5cc9abd1-671a-447e-ab93-5abbfe0ed941"
CORRECT_ICMARKETS_ID="d2605e89-7bc2-4144-9f7c-951edd596c39"

# Aktuelle ID auslesen
CURRENT_LIBERTEX=$(grep "^METAAPI_ACCOUNT_ID=" .env | cut -d'=' -f2)

# Vergleichen und korrigieren
if [ "$CURRENT_LIBERTEX" != "$CORRECT_LIBERTEX_ID" ]; then
    # Backup erstellen
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Korrigieren (macOS-kompatibel)
    sed -i '' "s|^METAAPI_ACCOUNT_ID=.*|METAAPI_ACCOUNT_ID=$CORRECT_LIBERTEX_ID|g" .env
fi
```

### **macOS & Linux kompatibel:**
Das Skript erkennt automatisch macOS und verwendet die richtige `sed` Syntax!

---

## 🙏 Credits:

Diese Funktion wurde auf Wunsch des Benutzers hinzugefügt, um sicherzustellen, dass nach jedem Fork die MetaAPI IDs garantiert korrekt sind! 

**Hervorragende Idee!** 👏
