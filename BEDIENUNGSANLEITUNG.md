# 📖 Booner Trade - Vollständige Bedienungsanleitung

**Version:** 2.3.34  
**Stand:** 18. Dezember 2025

---

## 📑 Inhaltsverzeichnis

1. [Übersicht](#1-übersicht)
2. [Dashboard - Hauptbildschirm](#2-dashboard---hauptbildschirm)
3. [Broker-Konten](#3-broker-konten)
4. [Rohstoffe & Marktdaten](#4-rohstoffe--marktdaten)
5. [Trades Tab](#5-trades-tab)
6. [Charts Tab](#6-charts-tab)
7. [Backtest Tab](#7-backtest-tab)
8. [Risiko Tab](#8-risiko-tab)
9. [Einstellungen](#9-einstellungen)
10. [KI-Chat Assistent](#10-ki-chat-assistent)
11. [Trading-Strategien erklärt](#11-trading-strategien-erklärt)
12. [Automatisches Trading](#12-automatisches-trading)
13. [Fehlerbehebung](#13-fehlerbehebung)

---

## 1. Übersicht

### Was ist Booner Trade?

Booner Trade ist eine professionelle Trading-Anwendung, die Ihnen ermöglicht:

- 📊 **Live-Marktdaten** für 15+ Rohstoffe zu verfolgen (Gold, Silber, Öl, etc.)
- 🤖 **Automatisches Trading** mit KI-gestützten Strategien
- 📈 **7 verschiedene Trading-Strategien** zu nutzen
- 💬 **KI-Chat** für Marktanalysen und Trade-Steuerung
- 🔌 **MetaTrader 5** Anbindung über MetaAPI

### Unterstützte Broker

| Broker | Status | Typ |
|--------|--------|-----|
| Libertex Demo | ✅ Aktiv | Demo-Konto |
| ICMarkets Demo | ✅ Aktiv | Demo-Konto |
| Libertex Real | 🔜 Geplant | Echtgeld-Konto |

---

## 2. Dashboard - Hauptbildschirm

### 2.1 Header-Bereich

| Element | Beschreibung | Was passiert wenn ich klicke? |
|---------|--------------|-------------------------------|
| **Live-Ticker** (Toggle) | Schaltet Echtzeit-Updates ein/aus | EIN: Preise aktualisieren sich automatisch alle 5-15 Sekunden. AUS: Keine automatischen Updates. |
| **Aktualisieren** | Manuelles Refresh | Lädt alle Daten neu (Preise, Trades, Kontostand) |
| **Einstellungen** | Öffnet Settings-Dialog | Hier können Sie alle Trading-Parameter konfigurieren |

### 2.2 KI-Status-Leiste

Die grüne/graue Leiste unter dem Header zeigt:

| Status | Bedeutung |
|--------|-----------|
| "Bereit für Analyse" | KI ist bereit, aber Auto-Trading ist AUS |
| "KI analysiert Marktdaten..." | Auto-Trading ist AN, KI sucht nach Signalen |
| "Provider: emergent/ollama" | Welcher KI-Provider aktiv ist |

**BEREIT-Button:** Startet eine manuelle KI-Analyse (unabhängig von Auto-Trading)

---

## 3. Broker-Konten

### 3.1 Kontokarten

Jede Karte zeigt ein verbundenes Broker-Konto:

| Feld | Bedeutung | Beispiel |
|------|-----------|----------|
| **Balance** | Ihr Kontostand (ohne offene Trades) | €42.652,50 |
| **Equity** | Aktueller Wert inkl. offener Trades | €43.139,36 |
| **Freie Margin** | Verfügbar für neue Trades | €11.886,75 |
| **Portfolio-Risiko** | Wie viel % ist in Trades gebunden | 72.5% / 20% |
| **Offene Positionen** | Wert und Anzahl offener Trades | €31.252,61 (14) |

### 3.2 Portfolio-Risiko verstehen

```
Portfolio-Risiko = (Gebundene Margin / Balance) × 100%

Beispiel:
Balance: €42.652,50
Gebundene Margin: €31.252,61
Risiko: 73.3%
```

**Farbcodes:**
- 🟢 **Grün (0-50%):** Sicherer Bereich, neue Trades möglich
- 🟡 **Gelb (50-70%):** Vorsicht, begrenzt neue Trades
- 🔴 **Rot (>70%):** Hohes Risiko, Auto-Trading pausiert neue Trades

### 3.3 Checkbox "Plattform aktiv"

- ✅ **Aktiviert:** Diese Plattform wird für Auto-Trading verwendet
- ⬜ **Deaktiviert:** Keine neuen Auto-Trades auf dieser Plattform

---

## 4. Rohstoffe & Marktdaten

### 4.1 Rohstoff-Karten

Jede Karte zeigt einen handelbaren Rohstoff:

| Element | Bedeutung |
|---------|-----------|
| **Name** (z.B. "Gold") | Der Rohstoff |
| **Kategorie** | Edelmetalle, Energie, Agrar, Forex, Crypto |
| **Preis** (grün) | Aktueller Marktpreis in USD |
| **Signal-Badge** | BUY (grün), SELL (rot), HOLD (grau) |
| **Handelszeiten** | Wann der Markt geöffnet ist |
| **Mini-Chart** | Preisentwicklung der letzten Stunden |

### 4.2 Signale verstehen

| Signal | Bedeutung | Was macht die KI? |
|--------|-----------|-------------------|
| **BUY** 🟢 | Kaufsignal - Preis wird steigen | Öffnet LONG-Position wenn Auto-Trading AN |
| **SELL** 🔴 | Verkaufssignal - Preis wird fallen | Öffnet SHORT-Position wenn Auto-Trading AN |
| **HOLD** ⚪ | Neutral - kein klares Signal | Keine neue Position, bestehende halten |

### 4.3 KAUFEN / VERKAUFEN Buttons

**KAUFEN (Grün):**
- Öffnet einen manuellen BUY-Trade
- Sie setzen auf steigende Preise
- Gewinn wenn Preis steigt, Verlust wenn er fällt

**VERKAUFEN (Rot):**
- Öffnet einen manuellen SELL-Trade (Short)
- Sie setzen auf fallende Preise
- Gewinn wenn Preis fällt, Verlust wenn er steigt

**Was passiert beim Klicken?**
1. Dialog öffnet sich mit Trade-Details
2. Sie wählen: Menge (Lots), Strategie, Plattform
3. Nach Bestätigung wird der Trade sofort ausgeführt
4. Trade erscheint im "Trades" Tab

---

## 5. Trades Tab

### 5.1 Offene Trades Tabelle

| Spalte | Bedeutung |
|--------|-----------|
| **Rohstoff** | Was gehandelt wird (z.B. XAUUSD = Gold) |
| **Typ** | BUY oder SELL |
| **Strategie** | Welche Strategie (Day, Swing, etc.) |
| **Menge** | Lot-Größe (0.01 = Micro-Lot) |
| **Entry** | Einstiegspreis |
| **Aktuell** | Aktueller Marktpreis |
| **SL** | Stop Loss Preis |
| **TP** | Take Profit Preis |
| **P/L** | Gewinn/Verlust in EUR |
| **Plattform** | Welcher Broker |

### 5.2 Trade-Aktionen

| Button | Was passiert? |
|--------|---------------|
| **Schließen** (X) | Trade wird sofort geschlossen, Gewinn/Verlust realisiert |
| **Bearbeiten** (✏️) | SL/TP ändern |
| **Alle schließen** | ALLE offenen Trades werden geschlossen |

### 5.3 Geschlossene Trades

- Tab "Geschlossene Trades" zeigt Trade-Historie
- **Statistiken zurücksetzen:** Löscht alle geschlossenen Trades aus der Anzeige

### 5.4 Stop Loss & Take Profit verstehen

**Stop Loss (SL):**
- Automatischer Verkauf bei Verlust
- Schützt vor großen Verlusten
- Beispiel: Entry $100, SL bei $98 = Max 2% Verlust

**Take Profit (TP):**
- Automatischer Verkauf bei Gewinn
- Sichert Gewinne
- Beispiel: Entry $100, TP bei $105 = 5% Gewinn gesichert

**Trailing Stop:**
- SL bewegt sich automatisch mit dem Preis
- Wenn Preis steigt, steigt auch SL
- Schützt Gewinne, aber gibt Raum für weitere Gewinne

---

## 6. Charts Tab

### 6.1 Preis-Chart

- Zeigt Preisverlauf des ausgewählten Rohstoffs
- Zeitrahmen wählbar (1H, 4H, 1D, 1W)
- Candlestick oder Linien-Darstellung

### 6.2 Technische Indikatoren

| Indikator | Was zeigt er? | Wie interpretieren? |
|-----------|---------------|---------------------|
| **RSI** | Relative Strength Index (0-100) | <30 = Überverkauft (kaufen?), >70 = Überkauft (verkaufen?) |
| **MACD** | Trend-Indikator | Linie über Signal = Bullish, darunter = Bearish |
| **SMA/EMA** | Gleitende Durchschnitte | Preis über SMA = Aufwärtstrend |

---

## 7. Backtest Tab

### 7.1 Was ist Backtesting?

Testen Sie Strategien mit historischen Daten, BEVOR Sie echtes Geld riskieren.

### 7.2 Backtest durchführen

1. **Strategie wählen:** Day, Swing, Scalping, etc.
2. **Rohstoff wählen:** Gold, Silber, etc.
3. **Zeitraum wählen:** Letzte 30/90/365 Tage
4. **Startkapital eingeben:** z.B. €10.000
5. **"Backtest starten" klicken**

### 7.3 Ergebnisse verstehen

| Metrik | Bedeutung | Gut wenn... |
|--------|-----------|-------------|
| **Win Rate** | % gewonnene Trades | >50% |
| **Profit Factor** | Gewinne / Verluste | >1.5 |
| **Max Drawdown** | Größter Verlust vom Höchststand | <20% |
| **Sharpe Ratio** | Risiko-adjustierte Rendite | >1.0 |
| **Total Return** | Gesamtrendite | Positiv! |

---

## 8. Risiko Tab

### 8.1 Portfolio-Übersicht

Zeigt das Gesamtrisiko über alle Broker:

- **Gesamt-Exposure:** Wie viel Geld ist in Trades gebunden
- **Risiko pro Plattform:** Verteilung auf Broker
- **Diversifikation:** Wie gut verteilt auf verschiedene Rohstoffe

### 8.2 Risiko-Regeln

| Regel | Beschreibung |
|-------|--------------|
| **Max 20% pro Plattform** | Nie mehr als 20% der Balance in einer Plattform |
| **Max 5 Positionen pro Asset** | Nicht zu viel in einem Rohstoff |
| **Trailing Stop** | Schützt laufende Gewinne |

---

## 9. Einstellungen

### 9.1 Allgemeine Einstellungen

| Einstellung | Was macht es? | Empfehlung |
|-------------|---------------|------------|
| **Auto-Trading** | KI handelt automatisch | Erst mit Demo testen! |
| **AI-Analyse** | KI analysiert Märkte | Immer AN lassen |
| **Standard-Plattform** | Welcher Broker für manuelle Trades | Libertex Demo |
| **Trailing Stop** | Automatische SL-Nachziehung | AN für Gewinnschutz |
| **Trailing Stop Distanz** | Abstand in % | 1.5-2% empfohlen |

### 9.2 KI-Provider Einstellungen

| Provider | Beschreibung | Wann nutzen? |
|----------|--------------|--------------|
| **Emergent** | Cloud-KI (GPT-5) | In der Web-App (Standard) |
| **OpenAI** | Eigener API-Key | Wenn Sie eigenen Key haben |
| **Ollama** | Lokale KI | Auf Mac für Offline-Nutzung |
| **Anthropic** | Claude KI | Alternative zu GPT |

### 9.3 Strategie-Einstellungen

Für JEDE der 7 Strategien können Sie einstellen:

| Einstellung | Bedeutung |
|-------------|-----------|
| **Aktiviert** | Strategie ein/aus |
| **Stop Loss %** | Automatischer Verlust-Stopp |
| **Take Profit %** | Automatischer Gewinn-Stopp |
| **Max Positionen** | Wie viele Trades gleichzeitig |
| **Min. Konfidenz** | Wie sicher muss das Signal sein |

---

## 10. KI-Chat Assistent

### 10.1 Chat öffnen

Klicken Sie auf den **Chat-Button** (unten rechts, blau/lila)

### 10.2 Spracheingabe

| Button | Farbe | Funktion |
|--------|-------|----------|
| **Browser** | Lila | Google Web Speech (braucht Internet) |
| **Whisper** | Orange | Lokale Spracherkennung (Offline) |

### 10.3 KI-Befehle

#### Trading-Befehle

| Befehl | Was passiert? |
|--------|---------------|
| "Kaufe Gold" | Öffnet BUY-Trade für Gold (0.01 Lots) |
| "Verkaufe WTI" | Öffnet SELL-Trade für WTI Öl |
| "Schließe alle" | Schließt ALLE offenen Trades |
| "Schließe alle positiven" | Schließt nur Trades mit Gewinn |
| "Schließe alle negativen" | Schließt nur Trades mit Verlust |
| "Schließe Gold" | Schließt alle Gold-Trades |

#### Informations-Befehle

| Befehl | Was passiert? |
|--------|---------------|
| "Zeige Portfolio" | Zeigt Balance, Equity, P/L aller Konten |
| "Welche Trades sind offen?" | Listet alle offenen Positionen |
| "Wie viele Trades habe ich?" | Zeigt Anzahl und Details |
| "Was ist der Gold-Preis?" | Aktueller Goldpreis + Signal |

#### Strategie-Befehle

| Befehl | Was passiert? |
|--------|---------------|
| "Welche Strategien sind aktiv?" | Listet alle aktiven Strategien |
| "Aktiviere Momentum" | Schaltet Momentum-Strategie EIN |
| "Deaktiviere Grid" | Schaltet Grid-Strategie AUS |
| "Bot an" / "Starte Bot" | Aktiviert Auto-Trading |
| "Bot aus" / "Stoppe Bot" | Deaktiviert Auto-Trading |

#### Analyse-Befehle

| Befehl | Was passiert? |
|--------|---------------|
| "Analysiere Gold" | KI-Analyse für Gold (RSI, Trend, Empfehlung) |
| "Was denkst du über Silber?" | Markteinschätzung |
| "Soll ich Gold kaufen?" | Empfehlung basierend auf Signalen |

### 10.4 Konversations-Beispiel

```
Sie: "Wie sieht mein Portfolio aus?"

KI: "📊 PORTFOLIO ZUSAMMENFASSUNG

💰 MT5 Libertex:
   Balance: €42.652,50
   Equity: €43.139,36
   P/L: +€486,86
   Positionen: 14

💰 MT5 ICMarkets:
   Balance: €2.403,26
   Equity: €2.403,26
   P/L: €0,00
   Positionen: 0

📈 GESAMT:
   Balance: €45.055,76
   P/L: +€486,86
   Offene Positionen: 14"

Sie: "Schließe alle positiven"

KI: "✅ 8 profitable Trades geschlossen"
```

---

## 11. Trading-Strategien erklärt

### 11.1 Die 7 Strategien im Überblick

| Strategie | Symbol | Haltezeit | Risiko | Für wen? |
|-----------|--------|-----------|--------|----------|
| **Day Trading** | ⚡ | Minuten-Stunden | Mittel | Aktive Trader |
| **Swing Trading** | 📈 | Tage-Wochen | Niedrig-Mittel | Geduldig |
| **Scalping** | 🎯 | Sekunden-Minuten | Hoch | Erfahrene |
| **Mean Reversion** | 🔄 | Stunden-Tage | Mittel | RSI-Fans |
| **Momentum** | 🚀 | Tage | Mittel-Hoch | Trend-Follower |
| **Breakout** | 💥 | Stunden-Tage | Hoch | Volatilitäts-Fans |
| **Grid** | 📐 | Variabel | Niedrig | Seitwärtsmärkte |

### 11.2 Day Trading ⚡

**Konzept:** Trades werden innerhalb eines Tages geöffnet und geschlossen.

**Wann kauft die KI?**
- RSI unter 40 (leicht überverkauft)
- Aufwärtstrend erkannt
- Konfidenz mindestens 40%

**Standard SL/TP:** 1.5% / 2.5%

**Gut für:** Rohstoffe mit hoher Volatilität (Gold, Öl)

### 11.3 Swing Trading 📈

**Konzept:** Positionen werden Tage bis Wochen gehalten.

**Wann kauft die KI?**
- Starkes Trendsignal
- RSI bestätigt Richtung
- Konfidenz mindestens 60%

**Standard SL/TP:** 2.0% / 4.0%

**Gut für:** Alle Rohstoffe, besonders bei klaren Trends

### 11.4 Scalping 🎯

**Konzept:** Sehr kurze Trades, kleine Gewinne summieren sich.

**Wann kauft die KI?**
- Schnelle Preisbewegung erkannt
- Hohe Liquidität
- Konfidenz mindestens 50%

**Standard SL/TP:** 0.5% / 1.0%

**Gut für:** Gold, EUR/USD (hohe Liquidität)

**⚠️ Achtung:** Hohe Handelsfrequenz = mehr Gebühren

### 11.5 Mean Reversion 🔄

**Konzept:** Preise kehren immer zum Durchschnitt zurück.

**Wann kauft die KI?**
- RSI unter 30 (stark überverkauft)
- Preis weit unter Durchschnitt

**Wann verkauft die KI?**
- RSI über 70 (stark überkauft)
- Preis weit über Durchschnitt

**Standard SL/TP:** 2.0% / 0.8%

**Gut für:** Seitwärtsmärkte, Range-gebundene Assets

### 11.6 Momentum 🚀

**Konzept:** Folge dem Trend - was steigt, steigt weiter.

**Wann kauft die KI?**
- Starker Aufwärtstrend
- Zunehmendes Volumen
- RSI zwischen 50-70

**Standard SL/TP:** 2.5% / 5.0%

**Gut für:** Trendende Märkte, News-Events

### 11.7 Breakout 💥

**Konzept:** Handel bei Ausbrüchen aus Konsolidierungszonen.

**Wann kauft die KI?**
- Preis durchbricht Widerstand
- Hohes Volumen bestätigt Ausbruch
- RSI über 65

**Standard SL/TP:** 2.0% / 3.0%

**Gut für:** Volatile Märkte, nach Konsolidierung

### 11.8 Grid Trading 📐

**Konzept:** Mehrere Orders in regelmäßigen Abständen.

**Wie funktioniert es?**
- Kaufaufträge werden unterhalb des Preises platziert
- Verkaufaufträge werden oberhalb platziert
- Profitiert von Auf- und Ab-Bewegungen

**Standard SL/TP:** 1.5% / 1.5%

**Gut für:** Seitwärtsmärkte ohne klaren Trend

---

## 12. Automatisches Trading

### 12.1 Auto-Trading aktivieren

1. Öffnen Sie **Einstellungen**
2. Aktivieren Sie **"Auto-Trading"**
3. Wählen Sie aktive **Strategien**
4. Setzen Sie **SL/TP** für jede Strategie
5. Speichern Sie die Einstellungen

### 12.2 Was macht der Bot?

```
Alle 8-20 Sekunden:

1. MarketBot sammelt Preise und berechnet Indikatoren
2. SignalBot analysiert und generiert BUY/SELL/HOLD Signale
3. TradeBot prüft:
   - Ist Portfolio-Risiko unter 20%?
   - Ist die Strategie aktiviert?
   - Ist das Signal stark genug?
   - Ist der Markt offen?
4. Wenn alles OK → Trade wird ausgeführt
5. Bot überwacht offene Trades und schließt bei SL/TP
```

### 12.3 Sicherheits-Checks

Der Bot macht KEINE neuen Trades wenn:

- ❌ Portfolio-Risiko über 20%
- ❌ Max-Positionen für diesen Rohstoff erreicht
- ❌ Markt ist geschlossen
- ❌ Signal-Konfidenz zu niedrig
- ❌ Kein aktiver Broker ausgewählt

### 12.4 Auto-Trading überwachen

- **Status-Leiste** zeigt ob Bot aktiv ist
- **Trades-Tab** zeigt neue Trades mit Strategie-Badge
- **Backend-Logs** zeigen detaillierte Bot-Aktivität

---

## 13. Fehlerbehebung

### 13.1 Häufige Probleme

| Problem | Ursache | Lösung |
|---------|---------|--------|
| Balance zeigt €0.00 | MetaAPI nicht verbunden | Backend neu starten, MetaAPI IDs prüfen |
| "Account not found" | Falsche MetaAPI ID | IDs in .env korrigieren |
| Keine Preise | Live-Ticker aus | Live-Ticker einschalten |
| KI antwortet nicht | Provider-Problem | Anderen Provider wählen oder Ollama nutzen |
| Mikrofon "Netzwerk-Fehler" | Google Server blockiert | Whisper-Button (orange) nutzen |
| Trades werden nicht ausgeführt | Portfolio-Risiko zu hoch | Einige Trades schließen |

### 13.2 Backend neu starten

Wenn die App nicht richtig funktioniert:

```bash
sudo supervisorctl restart backend
```

### 13.3 Logs prüfen

```bash
# Backend-Logs
tail -f /var/log/supervisor/backend.err.log

# Suche nach Fehlern
grep -i "error" /var/log/supervisor/backend.err.log | tail -20
```

### 13.4 MetaAPI IDs korrigieren

Falls Broker-Verbindung nicht funktioniert:

```bash
# Korrekte IDs setzen
sed -i 's/METAAPI_ACCOUNT_ID=.*/METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941/' /app/backend/.env
sed -i 's/METAAPI_ICMARKETS_ACCOUNT_ID=.*/METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39/' /app/backend/.env

# Backend neu starten
sudo supervisorctl restart backend
```

---

## 📞 Schnellhilfe

### Die wichtigsten Aktionen:

| Was möchte ich? | Wie mache ich es? |
|-----------------|-------------------|
| Gold kaufen | "Kaufe Gold" im Chat ODER grüner KAUFEN-Button |
| Alle Trades schließen | "Schließe alle" im Chat |
| Auto-Trading starten | Einstellungen → Auto-Trading AN |
| Strategie ändern | Einstellungen → Strategie aktivieren/deaktivieren |
| Portfolio sehen | "Portfolio" im Chat |
| SL/TP ändern | Einstellungen → Strategie → SL/TP anpassen |

### Tastenkürzel im Chat:

- **Enter:** Nachricht senden
- **Lila Mikrofon:** Browser-Spracherkennung (braucht Internet)
- **Orange Mikrofon:** Whisper (Offline, empfohlen für Mac)

---

**Viel Erfolg beim Trading!** 🚀📈

Bei Fragen nutzen Sie den KI-Chat - er kennt alle Funktionen und kann Ihnen helfen!
