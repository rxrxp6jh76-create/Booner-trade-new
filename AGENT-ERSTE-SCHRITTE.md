# 🚨 AGENT: LIES DAS ZUERST! - Pflichtlektüre nach jedem Fork

**Letzte Aktualisierung:** 18. Dezember 2025 (v2.3.34)

---

## ⚠️ KRITISCH: Diese Datei MUSS nach JEDEM Fork gelesen werden!

Der Agent MUSS diese Schritte **AUTOMATISCH und SOFORT** nach jedem Fork ausführen, 
**OHNE dass der User danach fragt!**

---

## 🔴 SCHRITT 1: MetaAPI IDs korrigieren (IMMER!)

Nach jedem Fork werden die MetaAPI IDs in `/app/backend/.env` auf falsche Werte zurückgesetzt.

### Die EINZIG KORREKTEN IDs sind:

```bash
# MT5 Libertex Demo (MT5-510038543)
METAAPI_ACCOUNT_ID=riskmanage-update

# MT5 ICMarkets Demo (MT5-52565616)
METAAPI_ICMARKETS_ACCOUNT_ID=riskmanage-update
```

### Korrektur-Befehl:

```bash
# IDs korrigieren (die korrekten UUIDs!)
sed -i 's/METAAPI_ACCOUNT_ID=.*/METAAPI_ACCOUNT_ID=riskmanage-update/' /app/backend/.env
sed -i 's/METAAPI_ICMARKETS_ACCOUNT_ID=.*/METAAPI_ICMARKETS_ACCOUNT_ID=riskmanage-update/' /app/backend/.env

# Backend neu starten
sudo supervisorctl restart backend
```

### Prüfen ob es funktioniert:

```bash
# Warte 5 Sekunden und prüfe Logs
sleep 5 && tail -n 20 /var/log/supervisor/backend.err.log | grep -i "account"
```

**Erwartetes Ergebnis:** Keine "account not found" Fehler mehr!

---

## 🟡 SCHRITT 2: Backend-Status prüfen

```bash
# Prüfe ob Backend läuft
sudo supervisorctl status backend

# Prüfe auf Syntax-Fehler
tail -n 50 /var/log/supervisor/backend.err.log | grep -i "error\|exception"
```

---

## 🟢 SCHRITT 3: Dokumentation lesen

Lies diese Dateien für vollständiges Verständnis:

| Datei | Inhalt |
|-------|--------|
| `WICHTIG-FUER-NAECHSTEN-AGENTEN.md` | Kritische Code-Stellen, Bug-Historie |
| `DOKUMENTATION.md` | Vollständige App-Dokumentation |
| `RELEASE-NOTES-V2.3.32.md` | Aktuelle Features und Fixes |

---

## 📋 Checkliste nach jedem Fork:

- [ ] MetaAPI IDs in `.env` korrigiert
- [ ] Backend neu gestartet
- [ ] Logs geprüft (keine "account not found" Fehler)
- [ ] Screenshot vom Dashboard gemacht (Balance wird angezeigt?)
- [ ] `WICHTIG-FUER-NAECHSTEN-AGENTEN.md` gelesen

---

## 🎯 Typische Fork-Probleme:

| Problem | Ursache | Lösung |
|---------|---------|--------|
| "Account not found" | Falsche MetaAPI IDs | Siehe Schritt 1 |
| Balance €0.00 | MetaAPI nicht verbunden | MetaAPI IDs prüfen |
| IndentationError | Code-Fehler vom letzten Fork | Logs prüfen, Fehler beheben |
| "database locked" | SQLite Konflikt | Backend neu starten |

---

## 🔗 Wichtige Pfade:

```
/app/backend/.env          # MetaAPI IDs hier!
/app/backend/server.py     # Hauptserver
/app/backend/trading.db    # SQLite Datenbank
/app/test_result.md        # Test-Status
```

---

**REMEMBER: Diese Schritte sind PFLICHT nach jedem Fork - nicht optional!**
