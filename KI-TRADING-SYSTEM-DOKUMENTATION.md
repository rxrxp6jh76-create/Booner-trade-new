# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 KI TRADING SYSTEM V2.6.0 - KOMPLETTE DOKUMENTATION
# ═══════════════════════════════════════════════════════════════════════════════
# Erstellt: 25.12.2024
# Letzte Änderung: 25.12.2024
# ═══════════════════════════════════════════════════════════════════════════════

## INHALTSVERZEICHNIS
1. Trading-Modi (3-Stufen-System)
2. Strategie-Profile (7 Strategien)
3. 4-Säulen-Modell Erklärung
4. Asset-Strategie Empfehlungen
5. Strategie-spezifische Indikatoren
6. COT-Daten Integration
7. Confidence Thresholds
8. Fehlerbehebung (macOS)

═══════════════════════════════════════════════════════════════════════════════
## 1. TRADING-MODI (3-STUFEN-SYSTEM)
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────┬─────────────┬─────────────┬─────────────┐
│ Markt-Zustand   │ Konservativ │ Neutral     │ Aggressiv   │
├─────────────────┼─────────────┼─────────────┼─────────────┤
│ Starker Trend   │ 70%         │ 62%         │ 55%         │
│ Normal Trend    │ 72%         │ 65%         │ 58%         │
│ Range           │ 75%         │ 68%         │ 60%         │
│ High Volatility │ 80%         │ 72%         │ 65%         │
│ Chaos           │ 88%         │ 80%         │ 72%         │
├─────────────────┼─────────────┼─────────────┼─────────────┤
│ MINIMUM         │ 75%         │ 68%         │ 60%         │
└─────────────────┴─────────────┴─────────────┴─────────────┘

🛡️ KONSERVATIV: Höchste Qualität, weniger Trades
⚖️ NEUTRAL:     Ausgewogene Balance
🔥 AGGRESSIV:   Maximale Aktivität, höheres Risiko

═══════════════════════════════════════════════════════════════════════════════
## 2. STRATEGIE-PROFILE (7 STRATEGIEN)
═══════════════════════════════════════════════════════════════════════════════

┌──────────────┬───────┬───────┬───────┬───────────┬───────────┬─────────────────────┐
│ Strategie    │ Basis │ Trend │ Vola  │ Sentiment │ Threshold │ Fokus               │
├──────────────┼───────┼───────┼───────┼───────────┼───────────┼─────────────────────┤
│ SWING        │ 30    │ 40    │ 10    │ 20        │ 75%       │ D1/W1 Konfluenz     │
│ DAY          │ 35    │ 25    │ 20    │ 20        │ 70%       │ EMA-Fächer + RSI    │
│ SCALPING     │ 40    │ 10    │ 40    │ 10        │ 60%       │ VWAP + Tick-Vola    │
│ MOMENTUM     │ 20    │ 30    │ 40    │ 10        │ 65%       │ ADX > 25            │
│ MEAN REV     │ 50    │ 10    │ 30    │ 10        │ 60%       │ Bollinger Touch     │
│ BREAKOUT     │ 30    │ 15    │ 45    │ 10        │ 72%       │ BB Squeeze          │
│ GRID         │ 10    │ 50    │ 30    │ 10        │ Auto      │ Range-Markt         │
└──────────────┴───────┴───────┴───────┴───────────┴───────────┴─────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
## 3. 4-SÄULEN-MODELL ERKLÄRUNG
═══════════════════════════════════════════════════════════════════════════════

### SÄULE 1: BASIS-SIGNAL (max 10-50 Punkte je nach Strategie)
- RSI Extreme (überverkauft < 30, überkauft > 70)
- MACD Crossover / Divergenz
- EMA Crossover (20/50/100/200)
- Bollinger Band Touch
- Signal vorhanden (BUY/SELL)
- Confluence-Bonus (mehrere Indikatoren stimmen überein)

### SÄULE 2: TREND-KONFLUENZ (max 10-50 Punkte je nach Strategie)
- D1 (Tages-Trend) Alignment
- H4 (4-Stunden-Trend) Alignment
- H1 (Stunden-Trend) Alignment
- ADX Stärke (> 25 = starker Trend)
- SONDERREGEL: Grid braucht KEINEN Trend (Seitwärtsmarkt)
- SONDERREGEL: Mean Reversion funktioniert besser bei Neutral

### SÄULE 3: VOLATILITÄTS-CHECK (max 10-45 Punkte je nach Strategie)
- ATR (Average True Range) Normalisierung
- Volume Bestätigung
- Bollinger Band Width (Squeeze = Ausbruch)
- Tick-Volume Spikes (für Scalping)

### SÄULE 4: SENTIMENT (max 10-20 Punkte je nach Strategie)
- News-Sentiment (bullish/bearish/neutral)
- COT-Daten (Spekulanten-Positionen)
- High-Impact News Warning
- Fear & Greed Index

═══════════════════════════════════════════════════════════════════════════════
## 4. ASSET-STRATEGIE EMPFEHLUNGEN
═══════════════════════════════════════════════════════════════════════════════

┌────────────────────────┬──────────────────────────────────────────┐
│ Asset-Klasse           │ Empfohlene Strategien                    │
├────────────────────────┼──────────────────────────────────────────┤
│ Edelmetalle            │ Swing, Breakout, Momentum                │
│ (Gold, Silber, Platin) │                                          │
├────────────────────────┼──────────────────────────────────────────┤
│ Energie                │ Breakout, Momentum, Swing                │
│ (WTI, Brent, Gas)      │ (News-Abhängigkeit: OPEC, Krisen)        │
├────────────────────────┼──────────────────────────────────────────┤
│ Agrar                  │ Swing, Mean Reversion                    │
│ (Wheat, Corn, Coffee)  │ (Saisonale Muster)                       │
├────────────────────────┼──────────────────────────────────────────┤
│ Forex Major            │ Mean Reversion, Day, Scalping            │
│ (EUR/USD, GBP/USD)     │ (Hohe Liquidität, enge Spreads)          │
├────────────────────────┼──────────────────────────────────────────┤
│ Crypto                 │ Momentum, Scalping, Breakout             │
│ (Bitcoin)              │ (Hohe Volatilität, 24/7 Markt)           │
│                        │ SONDER-THRESHOLD: 62% (Aggressiv-Light)  │
├────────────────────────┼──────────────────────────────────────────┤
│ Indizes                │ Day, Swing, Momentum                     │
└────────────────────────┴──────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
## 5. STRATEGIE-SPEZIFISCHE INDIKATOREN
═══════════════════════════════════════════════════════════════════════════════

### SWING TRADING
- Primär: EMA 50/200 Golden Cross, MACD Signal-Line Cross (D1)
- Trend: W1 und D1 müssen in gleiche Richtung zeigen
- Vola: ATR(14) auf D1 muss stabil sein
- Sentiment: COT-Daten, Zentralbank-Entscheidungen

### DAY TRADING
- Primär: EMA-Fächer (20/50/100) auf H1 + RSI Bestätigung
- Trend: H4 Trendrichtung muss mit H1 übereinstimmen
- Vola: Session-Volumen (NY Open, London Open)
- Sentiment: Tagesaktuelle News (Wirtschaftskalender)

### SCALPING
- Primär: VWAP-Abweichung + Stochastik-Cross auf M1/M5
- Trend: Nur unmittelbarer M5 Trend relevant
- Vola: Tick-Volumen-Spikes (KRITISCH - ohne Vola kein Scalp!)
- Sentiment: Orderbuch-Ungleichgewicht (Bid vs. Ask)

### MOMENTUM
- Primär: Preis bricht über letztes Hoch/Tief
- Trend: ADX > 25 signalisiert Trendstärke (KRITISCH!)
- Vola: Stark steigender ATR oder Volumen-Expansion
- Sentiment: Social Media Buzz, News-Hype (besonders BTC)

### MEAN REVERSION
- Primär: Preis außerhalb 2. Standardabweichung Bollinger (FOKUS!)
- Trend: Funktioniert am besten bei NEUTRAL (Seitwärtsmarkt)
- Vola: Muss kurz peaken und dann nachlassen (Erschöpfung)
- Sentiment: Fear & Greed Index Extremwerte

### BREAKOUT
- Primär: Mehrfacher Test eines Levels (mind. 3 Kontakte)
- Trend: Übergeordneter Trend begünstigt Ausbruchsrichtung
- Vola: Bollinger Band Squeeze (Bänder eng, dann Expansion) (FOKUS!)
- Sentiment: Anstehende News-Events als Katalysator

### GRID TRADING
- Primär: Start an psychologischen Marken (Runde Zahlen)
- Trend: NEGATIVER Score bei starkem Trend! (Braucht Seitwärtsmarkt)
- Vola: Hohe "Ping-Pong" Volatilität (Zick-Zack-Kurs)
- Sentiment: Ruhige Nachrichtenlage (keine Trend-Events)
- SONDERREGEL: Läuft automatisch wenn Trend-Score < 20

═══════════════════════════════════════════════════════════════════════════════
## 6. COT-DATEN INTEGRATION
═══════════════════════════════════════════════════════════════════════════════

### Datenquelle: CFTC PRE API (KOSTENLOS)
URL: https://publicreporting.cftc.gov/
Doku: https://publicreporting.cftc.gov/stories/s/User-s-Guide/p2fg-u73y/

### Update-Zyklus
- Veröffentlichung: Jeden Freitag 15:30 EST
- Daten von: Dienstag derselben Woche

### Verfügbare Daten
- commercial_net: Hedger-Positionen (Produzenten/Verbraucher)
- noncommercial_net: Spekulanten (Hedge Funds, CTAs)
- weekly_change: Änderung zur Vorwoche (Momentum)

### Interpretation
- Spekulanten bullish + Weekly Change positiv = Starkes BUY Signal
- Spekulanten bearish + Weekly Change negativ = Starkes SELL Signal
- Gegen-Signal = Warnung/Penalty

### Contract Codes (CFTC)
- GOLD: 088691
- SILVER: 084691
- WTI CRUDE: 067651
- NATURAL GAS: 023651
- WHEAT: 001602
- CORN: 002602
- EUR/USD: 099741
- BITCOIN: 133741

═══════════════════════════════════════════════════════════════════════════════
## 7. WICHTIGE DATEIEN
═══════════════════════════════════════════════════════════════════════════════

/app/backend/autonomous_trading_intelligence.py
  → Haupt-KI mit Strategie-Profilen und 4-Säulen-Modell

/app/backend/server.py
  → API Endpunkte inkl. /api/signals/status (Ampelsystem)

/app/backend/cot_data_service.py
  → COT-Daten Service für Commodity-Sentiment

/app/backend/advanced_filters.py
  → Zusätzliche Filter (DXY, Anti-Cluster, Spread)

/app/backend/self_learning_journal.py
  → Selbstlernendes System (Pattern Blacklist, Equity Curve)

/app/frontend/src/components/SettingsDialog.jsx
  → UI für 3-Stufen Trading-Modus

/app/frontend/src/pages/Dashboard.jsx
  → Ampelsystem mit Confidence-Anzeige

═══════════════════════════════════════════════════════════════════════════════
## 8. FEHLERBEHEBUNG (macOS)
═══════════════════════════════════════════════════════════════════════════════

### Problem: Backend startet nicht mehr / stürzt ab

LÖSUNG 1: fix_backend.sh Script ausführen
  $ cd /pfad/zum/backend
  $ chmod +x fix_backend.sh
  $ ./fix_backend.sh

LÖSUNG 2: Manueller Reset
  $ pkill -f "server.py"
  $ pkill -f "uvicorn"
  $ lsof -ti:8000 | xargs kill -9
  $ rm -f trading.db-journal trading.db-wal trading.db-shm

LÖSUNG 3: Python Recovery Script
  $ python backend_recovery.py --start

### Problem: Port 8000 blockiert

  $ lsof -i:8000
  $ kill -9 <PID>

### Problem: Datenbank gesperrt

  $ rm -f trading.db-journal
  $ rm -f trading.db-wal
  $ rm -f trading.db-shm

### API Endpoints für Diagnose

GET  /api/system/health       - System Status prüfen
POST /api/system/memory-cleanup - Memory aufräumen
POST /api/system/force-reload   - Hard Restart (macOS)

═══════════════════════════════════════════════════════════════════════════════
## ÄNDERUNGSHISTORIE
═══════════════════════════════════════════════════════════════════════════════

V2.6.0 (25.12.2024)
- 7 Strategie-Profile mit spezifischen Säulen-Gewichtungen
- 3-Stufen Trading-Modus (Konservativ, Neutral, Aggressiv)
- Strategie-spezifische Indikatoren in der Ampel
- Asset-Strategie Empfehlungen automatisch
- COT-Daten Integration
- Backend Recovery System für macOS
- Memory Cleanup Endpoint
- Health Check Endpoint

V2.5.2 (24.12.2024)
- Asset-spezifische Säulen-Gewichtungen
- BTC Aggressiv-Light Threshold
- Mindest-Confluence Regel
- Strengere Neutral-Behandlung

V2.5.0 (24.12.2024)
- Ultimate AI Trading System Upgrade
- Asset-Klassen-spezifische Logik
- macOS Stability Fixes
- Ampelsystem mit Confidence

═══════════════════════════════════════════════════════════════════════════════
