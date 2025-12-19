# ⚠️ WICHTIG: MetaAPI Account IDs - Referenz für jeden Fork!

**Letzte Aktualisierung:** 17. Dezember 2025 (v2.3.32)

---

## 🔴 ACHTUNG: Nach jedem Fork werden die IDs zurückgesetzt!

Die MetaAPI IDs in `/app/backend/.env` werden bei jedem Fork auf Platzhalter zurückgesetzt.
**Der erste Schritt nach jedem Fork muss die Korrektur der IDs sein!**

---

## 📋 Die korrekten MetaAPI IDs:

### 1. MT5 Libertex Demo (MT5-510038543)
```
METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941
```

### 2. MT5 ICMarkets Demo (MT5-52565616)
```
METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39
```

### 3. MT5 Libertex REAL (MT5-560031700)
```
# Noch nicht konfiguriert - Platzhalter verwenden bis echte ID vorhanden
METAAPI_LIBERTEX_REAL_ACCOUNT_ID=PLACEHOLDER_REAL_ACCOUNT_ID
```

---

## 🔧 So korrigieren Sie die IDs:

### Option 1: Manuell in .env
```bash
# Datei öffnen
nano /app/backend/.env

# Diese Zeilen finden und korrigieren:
METAAPI_ACCOUNT_ID=regime-trading-ai
METAAPI_ICMARKETS_ACCOUNT_ID=regime-trading-ai
```

### Option 2: Per Kommando
```bash
# Libertex Demo ID setzen (die korrekte UUID!)
sed -i 's/METAAPI_ACCOUNT_ID=.*/METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941/' /app/backend/.env

# ICMarkets Demo ID setzen (die korrekte UUID!)
sed -i 's/METAAPI_ICMARKETS_ACCOUNT_ID=.*/METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39/' /app/backend/.env

# Backend neu starten
sudo supervisorctl restart backend
```

---

## 🎯 Warum ist das wichtig?

Ohne die korrekten MetaAPI Account IDs kann die App:
- ❌ Keine Trades von MT5 abrufen
- ❌ Keine Positionen anzeigen
- ❌ Keine Balance/Margin Daten holen
- ❌ Keine Trades öffnen/schließen

**Die App zeigt "Account not found" Fehler ohne korrekte IDs!**

---

## ✅ Prüfen ob IDs korrekt sind:

Nach dem Setzen der IDs und Backend-Neustart:

```bash
# API testen
curl https://[your-domain]/api/platforms/MT5_LIBERTEX_DEMO/account

# Sollte Balance, Equity, Margin zeigen - NICHT "Account not found"
```

---

## 📝 Für zukünftige Agenten:

⚠️ **WICHTIG: Nach JEDEM Fork AUTOMATISCH diese Schritte ausführen - OHNE dass der User danach fragt!**

1. **SOFORT** als erstes `/app/AGENT-ERSTE-SCHRITTE.md` lesen
2. MetaAPI IDs aus dieser Dokumentation in `.env` setzen
3. Backend neu starten nach Änderung
4. Testen mit curl ob Verbindung funktioniert
5. Screenshot machen um zu prüfen dass Balance angezeigt wird

---

## 🔗 Weitere Dokumentation:

- `/app/DOKUMENTATION.md` - Vollständige App-Dokumentation
- `/app/RELEASE-NOTES-V2.3.32.md` - Aktuelle Version
- `/app/backend/.env` - Zu korrigierende Datei
