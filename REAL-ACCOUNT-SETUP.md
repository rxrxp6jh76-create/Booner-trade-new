# 💰 Real Account Setup - WICHTIG!

## ⚠️ WARNUNG: Echtes Geld!
Real-Accounts handeln mit ECHTEM GELD. Stellen Sie sicher, dass alle Tests mit Demo-Accounts erfolgreich waren.

---

## Account-Struktur (identisch für Demo & Real)

Alle Accounts haben die exakt gleiche Struktur:

```python
{
    'type': 'MT5',
    'name': 'MT5 Libertex REAL',
    'account_id': 'UUID von MetaAPI',
    'region': 'london',
    'connector': None,
    'active': False,
    'balance': 0.0,
    'is_real': True  # Einziger Unterschied!
}
```

---

## Schritt 1: MetaAPI Account erstellen

1. Gehen Sie zu https://app.metaapi.cloud
2. Fügen Sie Ihren MT5 Real-Account hinzu
3. Kopieren Sie die Account-ID (UUID)

---

## Schritt 2: .env konfigurieren

Ersetzen Sie die Placeholder in `/app/backend/.env`:

```bash
# Libertex Real
METAAPI_LIBERTEX_REAL_ACCOUNT_ID=IHRE-ECHTE-UUID-HIER

# ICMarkets Real (optional)
METAAPI_ICMARKETS_REAL_ACCOUNT_ID=IHRE-ECHTE-UUID-HIER
```

---

## Schritt 3: In Settings aktivieren

1. Öffnen Sie die App
2. Gehen Sie zu ⚙️ Einstellungen
3. Aktivieren Sie unter "Aktive Platforms":
   - ✅ MT5_LIBERTEX_REAL
   - ✅ MT5_ICMARKETS_REAL

---

## Risiko-Management (gilt für ALLE Accounts)

Die folgenden Sicherheitsmaßnahmen gelten automatisch:

| Regel | Beschreibung |
|-------|--------------|
| **20% Portfolio-Risiko** | Trade wird blockiert wenn Margin/Balance > 20% |
| **Balance-Anpassung** | Bei Balance < 1000€ → Risiko auf 25% reduziert |
| **Lot-Size Anpassung** | Automatische Reduzierung bei hohem Risiko |
| **Chart-Trend-Analyse** | Blockiert Trades gegen starken Trend (>60%) |

---

## Berechnung Portfolio-Risiko

```
Portfolio-Risiko = Gesamt-Margin / Balance × 100

Beispiel:
- Margin: €11.455
- Balance: €112.600
- Risiko: 10.2% ✅ (unter 20%)
```

---

## Checklist vor Aktivierung

- [ ] Demo-Account funktioniert fehlerfrei
- [ ] Alle Strategien getestet
- [ ] 20% Portfolio-Limit verstanden
- [ ] Balance-Anpassung getestet
- [ ] MetaAPI Real Account-ID bereit
- [ ] Backup der .env erstellt

---

## Support

Bei Problemen:
1. Prüfen Sie die Logs: `tail -f /var/log/supervisor/backend.err.log`
2. Prüfen Sie die MetaAPI-Verbindung
3. Stellen Sie sicher, dass die Account-ID korrekt ist
