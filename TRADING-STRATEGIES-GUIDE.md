# 📊 Booner Trade - Trading Strategies Guide

**Version:** 2.3.29  
**Datum:** 16. Dezember 2024  
**Status:** Vollst\u00e4ndiger \u00dcberblick aller 7 Trading-Strategien

---

## \ud83c\udfaf \u00dcbersicht

Booner Trade unterst\u00fctzt **7 verschiedene Trading-Strategien**, jede mit spezifischen St\u00e4rken und Einsatzbereichen:

| # | Strategie | Best For | Risk Level | Haltezeit | Konfidenz Min |
|---|-----------|----------|------------|-----------|---------------|
| 1 | Swing Trading | Trends, Position Trading | \ud83d\udfe1 Niedrig | Tage-Wochen | 55% |
| 2 | Day Trading | Intraday Moves | \ud83d\udfe1 Mittel | Stunden | 60% |
| 3 | Scalping | Ultra-Short Trades | \ud83d\udd34 Hoch | Sekunden-Minuten | 60% |
| 4 | Mean Reversion | Range Markets | \ud83d\udfe1 Mittel | Stunden-Tage | 65% |
| 5 | Momentum | Trending Markets | \ud83d\udfe1 Mittel-Hoch | Tage | 70% |
| 6 | Breakout | Volatility Breakouts | \ud83d\udd34 Hoch | Stunden-Tage | 65% |
| 7 | Grid Trading | Sideways Markets | \ud83d\udfe1 Niedrig | Kontinuierlich | 65% |

---

## 1\ufe0f\u20e3 Swing Trading \ud83d\udcca

### Beschreibung
L\u00e4ngerfristige Positionshaltung, die von gr\u00f6\u00dferen Marktbewegungen profitiert.

### Wann verwenden?
- \u2705 Klare Trends (aufw\u00e4rts oder abw\u00e4rts)
- \u2705 Wenig Zeit f\u00fcr st\u00e4ndige \u00dcberwachung
- \u2705 H\u00f6here Gewinnziele (4%+)
- \u274c NICHT bei hoher Volatilit\u00e4t
- \u274c NICHT bei News-Events

### Parameter (Standard):
```
\u2022 Stop Loss: 2.0%
\u2022 Take Profit: 4.0%
\u2022 Max Positionen: 6
\u2022 Risk/Trade: 2.0%
\u2022 Trailing Stop: Optional (50 Pips)
\u2022 Min Konfidenz: 55%
```

### AI Erkennung:
- TP > 3.0% \u2192 Swing Trade
- Haltezeit > 1 Tag \u2192 Swing Trade

### Beispiel:
```
Gold @ $2,050
Entry: $2,050
SL: $2,009 (-2%)
TP: $2,132 (+4%)
Potenzial: $82/oz
Risk/Reward: 1:2
```

### Tipps:
- \ud83d\udca1 Setze Trailing Stop nach +2% Gewinn
- \ud83d\udca1 Nutze Weekly/Daily Charts
- \ud83d\udca1 Ignoriere kleine Schwankungen

---

## 2\ufe0f\u20e3 Day Trading \u26a1

### Beschreibung
Intraday-Trades, die innerhalb eines Handelstages ge\u00f6ffnet und geschlossen werden.

### Wann verwenden?
- \u2705 Aktive Marktstunden
- \u2705 Klare Intraday-Trends
- \u2705 Zeit f\u00fcr \u00dcberwachung
- \u274c NICHT \u00fcber Nacht halten
- \u274c NICHT bei Major News

### Parameter (Standard):
```
\u2022 Stop Loss: 2.0%
\u2022 Take Profit: 2.5%
\u2022 Max Positionen: 8
\u2022 Risk/Trade: 1.5%
\u2022 Trailing Stop: Optional (30 Pips)
\u2022 Min Konfidenz: 60%
```

### AI Erkennung:
- SL 1-2%, TP 2-3% \u2192 Day Trade
- Haltezeit < 24h \u2192 Day Trade

### Beispiel:
```
WTI Crude @ $72.50
Entry: $72.50
SL: $71.05 (-2%)
TP: $74.31 (+2.5%)
Potenzial: $1.81/barrel
Risk/Reward: 1:1.25
```

### Tipps:
- \ud83d\udca1 Trade nur w\u00e4hrend US/EU Markt\u00f6ffnung
- \ud83d\udca1 Schlie\u00dfe alle Positionen vor Marktschluss
- \ud83d\udca1 Nutze 1H/4H Charts

---

## 3\ufe0f\u20e3 Scalping \u26a1\ud83c\udfaf

### Beschreibung
Ultra-schnelle Trades mit sehr engen SL/TP, hohe Frequenz.

### Wann verwenden?
- \u2705 Hohe Liquidit\u00e4t
- \u2705 Geringe Spreads
- \u2705 Sehr aktive \u00dcberwachung
- \u274c NICHT f\u00fcr Anf\u00e4nger
- \u274c NICHT bei News-Events

### Parameter (Standard):
```
\u2022 Stop Loss: 0.08% (8 Pips)
\u2022 Take Profit: 0.15% (15 Pips)
\u2022 Max Positionen: 3
\u2022 Risk/Trade: 0.5%
\u2022 Max Haltezeit: 5 Minuten
\u2022 Min Konfidenz: 60%
```

### AI Erkennung:
- SL < 0.5%, TP < 1% \u2192 Scalping
- Haltezeit < 10 Min \u2192 Scalping

### Beispiel:
```
Gold @ $2,050.00
Entry: $2,050.00
SL: $2,048.36 (-0.08%)
TP: $2,053.08 (+0.15%)
Potenzial: $3.08/oz
Risk/Reward: 1:1.88
```

### Tipps:
- \ud83d\udca1 Nutze nur w\u00e4hrend liquidester Zeiten
- \ud83d\udca1 Max 3 Positionen gleichzeitig
- \ud83d\udca1 Sehr enge Stops - keine Emotionen!
- \ud83d\udca1 Nutze 1M/5M Charts

---

## 4\ufe0f\u20e3 Mean Reversion \ud83d\udcca

### Beschreibung
Handelt auf R\u00fcckkehr zum Mittelwert, nutzt \u00fcberkaufte/\u00fcberverkaufte Situationen.

### Wann verwenden?
- \u2705 Range-bound Markets
- \u2705 Hohe Bollinger Band Ausdehnung
- \u2705 Extreme RSI Werte
- \u274c NICHT bei starken Trends
- \u274c NICHT bei Breakouts

### Parameter (Standard):
```
\u2022 Bollinger Period: 20
\u2022 BB Std Dev: 2.0
\u2022 RSI Oversold: 30
\u2022 RSI Overbought: 70
\u2022 Stop Loss: 1.5%
\u2022 Take Profit: 2.0%
\u2022 Max Positionen: 5
\u2022 Risk/Trade: 1.5%
\u2022 Min Konfidenz: 65%
```

### AI Erkennung:
- Preis au\u00dferhalb Bollinger Bands
- RSI < 30 (BUY) oder > 70 (SELL)
- Confidence: 65-95% (je nach Distanz)

### Signal-Logik:
```python
BUY Signal:
- Preis < Lower Bollinger Band
- RSI < 30 (Oversold)
- Confidence = 65% + (Distanz zu Band * 100)

SELL Signal:
- Preis > Upper Bollinger Band  
- RSI > 70 (Overbought)
- Confidence = 65% + (Distanz zu Band * 100)
```

### Beispiel:
```
Silver @ $22.50
BB Lower: $22.80
BB Upper: $24.20
RSI: 28 (Oversold)

\u2192 BUY Signal
Entry: $22.50
SL: $22.16 (-1.5%)
TP: $22.95 (+2.0%)
```

### Tipps:
- \ud83d\udca1 Warte auf RSI Best\u00e4tigung
- \ud83d\udca1 Exit bei Preis-R\u00fcckkehr zu BB Middle
- \ud83d\udca1 Nicht gegen extrem starke Trends traden

---

## 5\ufe0f\u20e3 Momentum Trading \ud83d\ude80

### Beschreibung
Folgt starken Trends und Momentum, \"Trend is your friend\".

### Wann verwenden?
- \u2705 Starke Trends
- \u2705 MA Crossovers
- \u2705 Hohe Momentum-Werte
- \u274c NICHT bei Trend-Ersch\u00f6pfung
- \u274c NICHT in Ranges

### Parameter (Standard):
```
\u2022 Momentum Period: 14
\u2022 Momentum Threshold: 0.5%
\u2022 MA Fast: 50
\u2022 MA Slow: 200
\u2022 Stop Loss: 2.5%
\u2022 Take Profit: 5.0%
\u2022 Max Positionen: 8
\u2022 Risk/Trade: 2.0%
\u2022 Min Konfidenz: 70%
```

### AI Erkennung:
- Momentum > 0.5% + MA Fast > MA Slow
- Confidence = 70% + (Momentum / 10)

### Signal-Logik:
```python
BUY Signal:
- Momentum > +0.5%
- MA(50) > MA(200)  # Golden Cross
- Confidence = 70% + (Momentum Strength)

SELL Signal:
- Momentum < -0.5%
- MA(50) < MA(200)  # Death Cross
- Confidence = 70% + (|Momentum| Strength)
```

### Beispiel:
```
WTI Crude @ $75.00
Momentum: +1.2% (Strong)
MA(50): $73.50
MA(200): $71.00

\u2192 BUY Signal
Entry: $75.00
SL: $73.13 (-2.5%)
TP: $78.75 (+5.0%)
Confidence: 82%
```

### Tipps:
- \ud83d\udca1 Nutze h\u00f6here Timeframes (4H, Daily)
- \ud83d\udca1 Lass Gewinne laufen mit Trailing Stop
- \ud83d\udca1 Exit bei Momentum-Schw\u00e4che

---

## 6\ufe0f\u20e3 Breakout Trading \ud83d\udca5

### Beschreibung
Handelt Ausbr\u00fcche aus Konsolidierungen/Ranges.

### Wann verwenden?
- \u2705 Nach langen Konsolidierungen
- \u2705 Volume-Best\u00e4tigung vorhanden
- \u2705 Klare Support/Resistance Levels
- \u274c NICHT bei False Breakouts
- \u274c NICHT ohne Volume-Best\u00e4tigung

### Parameter (Standard):
```
\u2022 Lookback Period: 20
\u2022 Confirmation Bars: 2
\u2022 Volume Multiplier: 1.5x
\u2022 Stop Loss: 2.0%
\u2022 Take Profit: 4.0%
\u2022 Max Positionen: 6
\u2022 Risk/Trade: 1.8%
\u2022 Min Konfidenz: 65%
```

### AI Erkennung:
- Preis bricht \u00fcber Resistance/unter Support
- Min. 2 Bars Best\u00e4tigung
- Volume >= 1.5x Durchschnitt

### Signal-Logik:
```python
BUY Signal:
- Preis > Resistance (20-period high)
- 2+ Bars \u00fcber Resistance
- Current Volume >= 1.5 * Avg Volume
- Confidence = 65% + (Breakout %)

SELL Signal:
- Preis < Support (20-period low)
- 2+ Bars unter Support
- Volume Best\u00e4tigung
```

### Beispiel:
```
Gold @ $2,100
Resistance (20d): $2,090
Support (20d): $2,020

Preis bricht auf $2,105 mit 2x Volume

\u2192 BUY Signal
Entry: $2,105
SL: $2,063 (-2%)
TP: $2,189 (+4%)
Confidence: 73%
```

### Tipps:
- \ud83d\udca1 Warte auf Volume-Best\u00e4tigung
- \ud83d\udca1 Enger Stop unter/\u00fcber Breakout-Level
- \ud83d\udca1 Re-Test des Breakout-Levels ist normal

---

## 7\ufe0f\u20e3 Grid Trading \ud83d\udd39

### Beschreibung
Platziert Buy/Sell Orders in Grid-Struktur, profitiert von Volatility.

### Wann verwenden?
- \u2705 Sideways/Range Markets
- \u2705 Hohe Volatility
- \u2705 Predictable Swings
- \u274c NICHT bei starken Trends
- \u274c NICHT bei Breakouts

### Parameter (Standard):
```
\u2022 Grid Size: 50 Pips
\u2022 Grid Levels: 5
\u2022 Grid Direction: BOTH (Long/Short)
\u2022 Stop Loss: 3.0%
\u2022 TP per Level: 1.0%
\u2022 Max Positionen: 10
\u2022 Risk/Trade: 1.0%
```

### AI Erkennung:
- Preis erreicht Grid-Level (\u00b110% Toleranz)
- Grid-Position z\u00e4hlt < Max Positions

### Signal-Logik:
```python
Grid Setup (aktueller Preis: $100):

BUY Levels (unter Preis):
- Level 1: $99.50 (-0.5%)
- Level 2: $99.00 (-1.0%)
- Level 3: $98.50 (-1.5%)
- Level 4: $98.00 (-2.0%)
- Level 5: $97.50 (-2.5%)

SELL Levels (\u00fcber Preis):
- Level 1: $100.50 (+0.5%)
- Level 2: $101.00 (+1.0%)
- Level 3: $101.50 (+1.5%)
- Level 4: $102.00 (+2.0%)
- Level 5: $102.50 (+2.5%)
```

### Beispiel:
```
Silver @ $24.00
Grid Size: 50 Pips ($0.50)

Buy Grid:
$23.50, $23.00, $22.50, $22.00, $21.50

Sell Grid:
$24.50, $25.00, $25.50, $26.00, $26.50

Wenn Preis $23.50 erreicht:
\u2192 BUY Signal
Entry: $23.50
TP: $24.00 (+2.1%)
SL: $22.80 (-3.0%)
```

### Tipps:
- \ud83d\udca1 Starte mit kleinen Grid-Gr\u00f6\u00dfen
- \ud83d\udca1 Limitiere Max Positionen (Risiko!)
- \ud83d\udca1 Perfekt f\u00fcr Crypto/Forex Ranges
- \ud83d\udca1 Monitoring ist kritisch

---

## \ud83e\udd1d Strategie-Kombinationen

### Kombination 1: Trend + Mean Reversion
```
Momentum (Trend) + Mean Reversion (Pullbacks)
\u2192 Trade Momentum in Trend-Richtung
\u2192 Nutze Mean Reversion f\u00fcr Entries bei Pullbacks
```

### Kombination 2: Breakout + Momentum
```
Breakout (Entry) + Momentum (Confirmation)
\u2192 Trade Breakouts die von Momentum best\u00e4tigt sind
\u2192 H\u00f6here Erfolgsrate
```

### Kombination 3: Grid + Mean Reversion
```
Grid (Structure) + Mean Reversion (Signals)
\u2192 Platziere Grid nur in Mean Reversion Zones
\u2192 Bessere Risk/Reward
```

---

## \ud83d\udcc8 Market Conditions Guide

### Trending Markets (\ud83d\udc51 Best):
1. **Momentum Trading** - Folge dem Trend
2. **Breakout Trading** - Trade Breakout-Fortsetzungen
3. Swing Trading - L\u00e4ngerfristige Positionen

### Range-Bound Markets (\ud83d\udd39 Best):
1. **Mean Reversion** - Trade Extremen
2. **Grid Trading** - Profitiere von Swings
3. Day Trading - Intraday Ranges

### Volatile Markets (\ud83d\udca5 Best):
1. **Breakout Trading** - Volatility Breakouts
2. **Scalping** - Quick In-and-Out
3. Grid Trading - Vorsicht: Enge Stops!

### Low Volatility (\ud83d\udca4 Best):
1. **Swing Trading** - Geduld zahlt sich aus
2. Mean Reversion - Kleine Moves
3. NICHT: Scalping (Spreads!)

---

## \u26a0\ufe0f Risk Management

### Pro Strategie:
| Strategie | Max Risk/Trade | Max Gesamt-Risk | Stop Loss |
|-----------|----------------|-----------------|-----------|
| Swing | 2.0% | 10% | -2% |
| Day | 1.5% | 12% | -2% |
| Scalping | 0.5% | 1.5% | -0.08% |
| Mean Rev | 1.5% | 7.5% | -1.5% |
| Momentum | 2.0% | 16% | -2.5% |
| Breakout | 1.8% | 10.8% | -2% |
| Grid | 1.0% | 10% | -3% |

### Regeln:
1. \u2705 Nie mehr als 20% Gesamt-Risk
2. \u2705 Max 3 Strategien gleichzeitig
3. \u2705 Stop Loss IMMER setzen
4. \u2705 Position Sizing beachten
5. \u274c Keine Revenge Trading

---

## \ud83d\udcca Performance Expectations

### Realistisch (pro Monat):
- **Konservativ:** +2-5% (Swing + Mean Reversion)
- **Moderat:** +5-10% (Day + Momentum)
- **Aggressiv:** +10-20% (Scalping + Breakout + Grid)

### Risk of Ruin:
- **Niedrig:** Swing, Mean Reversion, Grid
- **Mittel:** Day, Momentum, Breakout
- **Hoch:** Scalping

---

## \ud83d\udee0\ufe0f AI Integration

### Automatische Strategie-Erkennung:
```python
AI analysiert Trade-Parameter:
- SL/TP Prozents\u00e4tze
- Haltezeit
- Market Conditions
- Indicators

\u2192 Weist automatisch passende Strategie zu
```

### Confidence Scores:
- **Scalping:** 60%+ (sehr selektiv)
- **Day Trading:** 60%+ (selektiv)
- **Swing Trading:** 55%+ (mehr Trades)
- **Mean Reversion:** 65%+ (klar definiert)
- **Momentum:** 70%+ (starke Signals)
- **Breakout:** 65%+ (Volume-best\u00e4tigt)
- **Grid:** 65% (fix, Grid-basiert)

---

## \ud83d\udcda Weitere Ressourcen

- **Backend:** `/app/backend/strategies/` - Strategie-Implementierungen
- **Settings:** Frontend Settings Dialog - Alle Parameter einstellbar
- **AI Logic:** `/app/backend/ai_trading_bot.py` - AI Integration
- **Trading Settings:** `/app/backend/trade_settings_manager.py` - Settings Management

---

**Viel Erfolg mit Booner Trade! \ud83d\ude80\ud83d\udcc8**

_F\u00fcr Fragen oder Probleme: Siehe README.md_
