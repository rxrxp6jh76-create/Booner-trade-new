# 🤖 Booner Trade - KI-Trading-System Dokumentation

**Version:** 2.3.32  
**Stand:** 17. Dezember 2025

---

## 🎯 Übersicht

Das KI-Trading-System ist das Kernstück von Booner Trade. Es automatisiert den gesamten Trading-Prozess von der Marktanalyse bis zur Trade-Ausführung.

---

## 🔄 Workflow des KI-Systems

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KI-TRADING WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   📊 MARKTDATEN         🧠 SIGNAL-ANALYSE        💰 TRADE-AUSFÜHRUNG        │
│   ┌──────────────┐      ┌──────────────┐        ┌──────────────┐           │
│   │  MarketBot   │ ──▶  │  SignalBot   │  ──▶   │  TradeBot    │           │
│   │  (8 Sek)     │      │  (20 Sek)    │        │  (12 Sek)    │           │
│   └──────────────┘      └──────────────┘        └──────────────┘           │
│         │                     │                        │                    │
│         ▼                     ▼                        ▼                    │
│   ┌──────────────┐      ┌──────────────┐        ┌──────────────┐           │
│   │ Yahoo Finance│      │ RSI, MACD    │        │ MetaAPI      │           │
│   │ Alpha Vantage│      │ Trend, News  │        │ MT5 Broker   │           │
│   │ MetaAPI      │      │ Strategien   │        │ Portfolio    │           │
│   └──────────────┘      └──────────────┘        └──────────────┘           │
│         │                     │                        │                    │
│         ▼                     ▼                        ▼                    │
│   ┌──────────────┐      ┌──────────────┐        ┌──────────────┐           │
│   │ market_data  │      │ pending_     │        │ trades.db    │           │
│   │ .db          │      │ signals[]    │        │ MetaTrader   │           │
│   └──────────────┘      └──────────────┘        └──────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 MarketBot - Der Datensammler

### Aufgaben
1. **Preise abrufen** von Yahoo Finance und MetaAPI
2. **Indikatoren berechnen** (RSI, MACD, SMA, EMA)
3. **Trend bestimmen** (UP/DOWN)
4. **Daten speichern** in `market_data.db`

### Intervall
Alle **8 Sekunden**

### Code-Beispiel
```python
async def execute(self):
    for commodity in self.commodities:
        # Hole Preisdaten
        data = await get_price_data(commodity)
        
        # Berechne Indikatoren
        rsi = calculate_rsi(data, period=14)
        macd, signal, hist = calculate_macd(data)
        sma_20 = calculate_sma(data, period=20)
        ema_20 = calculate_ema(data, period=20)
        
        # Bestimme Trend
        trend = "UP" if ema_20 > sma_20 else "DOWN"
        
        # Speichere in DB
        await db.market_data.update({
            'commodity': commodity,
            'price': data['close'],
            'rsi': rsi,
            'macd': macd,
            'trend': trend,
            'timestamp': datetime.now()
        })
```

### Berechnete Indikatoren

| Indikator | Beschreibung | Verwendung |
|-----------|--------------|------------|
| **RSI** | Relative Strength Index (0-100) | Überkauft (>70) / Überverkauft (<30) |
| **MACD** | Moving Average Convergence Divergence | Trend-Richtung und Stärke |
| **SMA 20** | Simple Moving Average (20 Perioden) | Trend-Filter |
| **EMA 20** | Exponential Moving Average (20 Perioden) | Schnellere Trend-Erkennung |
| **Volumen** | Handelsvolumen | Bestätigung von Bewegungen |

---

## 🧠 SignalBot - Der Analyst

### Aufgaben
1. **Marktdaten laden** aus `market_data.db`
2. **Strategien anwenden** (7 verschiedene)
3. **Signale generieren** (BUY/SELL/HOLD)
4. **Konfidenz berechnen** (0.0 - 1.0)
5. **Signale zur Warteschlange hinzufügen**

### Intervall
Alle **20 Sekunden**

### Signal-Struktur
```python
signal = {
    'commodity': 'SILVER',
    'action': 'SELL',           # BUY, SELL, HOLD
    'strategy': 'mean_reversion',
    'confidence': 0.75,         # 0.0 - 1.0
    'price': 65.74,
    'reason': 'RSI > 70 (überkauft)',
    'timestamp': '2025-12-17T08:00:00Z'
}
```

### Strategie-Logik

#### 1. Mean Reversion (🔄)
```python
def analyze_mean_reversion(data):
    rsi = data.get('rsi', 50)
    
    if rsi < 30:  # Überverkauft
        return 'BUY', 0.70, f"RSI {rsi:.0f} < 30 (überverkauft)"
    elif rsi > 70:  # Überkauft
        return 'SELL', 0.70, f"RSI {rsi:.0f} > 70 (überkauft)"
    else:
        return 'HOLD', 0.5, "RSI neutral"
```

#### 2. Momentum (🚀)
```python
def analyze_momentum(data):
    trend = data.get('trend', 'NEUTRAL')
    signal = data.get('signal', 'HOLD')
    
    is_bullish = trend in ['UP', 'bullish']
    is_bearish = trend in ['DOWN', 'bearish']
    
    if signal == 'BUY':
        confidence = 0.70 if is_bullish else 0.55
        return 'BUY', confidence, f"Momentum BUY, Trend: {trend}"
    elif signal == 'SELL':
        confidence = 0.70 if is_bearish else 0.55
        return 'SELL', confidence, f"Momentum SELL, Trend: {trend}"
    else:
        return 'HOLD', 0.5, "Kein Momentum-Signal"
```

#### 3. Breakout (💥)
```python
def analyze_breakout(data):
    rsi = data.get('rsi', 50)
    trend = data.get('trend', 'NEUTRAL')
    
    is_bullish = trend in ['UP', 'bullish']
    is_bearish = trend in ['DOWN', 'bearish']
    
    if rsi > 65 and is_bullish:
        return 'BUY', 0.60, f"Bullish Breakout, RSI: {rsi:.0f}"
    elif rsi < 35 and is_bearish:
        return 'SELL', 0.60, f"Bearish Breakout, RSI: {rsi:.0f}"
    else:
        return 'HOLD', 0.5, "Kein Breakout"
```

#### 4. Swing Trading (📈)
```python
def analyze_swing(data):
    rsi = data.get('rsi', 50)
    trend = data.get('trend', 'NEUTRAL')
    
    is_bullish = trend in ['UP', 'bullish']
    is_bearish = trend in ['DOWN', 'bearish']
    
    if is_bullish and rsi < 45:
        return 'BUY', 0.65, "Swing BUY: Bullish + RSI Pullback"
    elif is_bearish and rsi > 55:
        return 'SELL', 0.65, "Swing SELL: Bearish + RSI Rally"
    else:
        return 'HOLD', 0.5, "Kein Swing-Signal"
```

---

## 💰 TradeBot - Der Executor

### Aufgaben
1. **Signale aus Warteschlange holen**
2. **Portfolio-Risiko prüfen** (max 20%)
3. **Max-Positionen prüfen** (pro Asset und Total)
4. **Lot-Size berechnen**
5. **SL/TP berechnen** (basierend auf Strategie)
6. **Trade über MetaAPI ausführen**
7. **In ticket_strategy_map speichern**
8. **Offene Positionen überwachen**
9. **Auto-Close bei Take Profit**

### Intervall
Alle **12 Sekunden**

### Trade-Ausführung Workflow

```python
async def _execute_signal(self, signal, settings):
    commodity = signal['commodity']
    action = signal['action']
    strategy = signal['strategy']
    price = signal['price']
    
    # 1. Prüfe Max-Positionen
    existing = await self._count_positions(commodity, strategy)
    if existing >= max_positions:
        logger.warning(f"Max positions reached: {existing}")
        return
    
    # 2. Portfolio-Risiko prüfen
    for platform in active_platforms:
        account = await get_account_info(platform)
        balance = account['balance']
        margin = account['margin']
        
        risk_percent = (margin / balance) * 100
        
        if risk_percent > 20:
            logger.warning(f"Portfolio risk too high: {risk_percent}%")
            continue
        
        # 3. SL/TP berechnen
        sl_percent = settings.get(f'{strategy}_stop_loss_percent', 2.0)
        tp_percent = settings.get(f'{strategy}_take_profit_percent', 4.0)
        
        if action == 'BUY':
            stop_loss = price * (1 - sl_percent / 100)
            take_profit = price * (1 + tp_percent / 100)
        else:  # SELL
            stop_loss = price * (1 + sl_percent / 100)
            take_profit = price * (1 - tp_percent / 100)
        
        # 4. Trade ausführen
        result = await multi_platform.execute_trade(
            platform_name=platform,
            symbol=self._get_mt5_symbol(commodity),
            action=action,
            volume=lot_size,
            stop_loss=None,  # KI überwacht SL/TP
            take_profit=None
        )
        
        # 5. In ticket_strategy_map speichern
        if result['success']:
            await db.trades_db.save_ticket_strategy(
                mt5_ticket=result['ticket'],
                strategy=strategy,
                commodity=commodity
            )
```

### Position-Überwachung

```python
async def _monitor_positions(self, settings):
    for platform in active_platforms:
        positions = await get_open_positions(platform)
        
        for pos in positions:
            current_price = pos['currentPrice']
            take_profit = await get_take_profit(pos['ticket'])
            trade_type = pos['type']
            
            # Prüfe ob TP erreicht
            if trade_type == 'BUY' and current_price >= take_profit:
                logger.info(f"✅ TP reached for BUY {pos['symbol']}")
                await close_position(pos['ticket'])
                
            elif trade_type == 'SELL' and current_price <= take_profit:
                logger.info(f"✅ TP reached for SELL {pos['symbol']}")
                await close_position(pos['ticket'])
```

---

## 🎯 Symbol-Mapping

Der TradeBot konvertiert Commodity-Namen zu MT5-Symbolen:

```python
symbol_map = {
    # Edelmetalle
    'GOLD': 'XAUUSD',
    'SILVER': 'XAGUSD',
    'PLATINUM': 'XPTUSD',
    'PALLADIUM': 'XPDUSD',
    
    # Energie
    'CRUDE_OIL': 'XTIUSD',
    'BRENT_CRUDE': 'XBRUSD',
    'NATURAL_GAS': 'XNGUSD',
    
    # Forex
    'EURUSD': 'EURUSD',
    'GBPUSD': 'GBPUSD',
    'USDJPY': 'USDJPY',
    
    # Crypto
    'BITCOIN': 'BTCUSD',
    'ETHEREUM': 'ETHUSD',
    
    # Agrar
    'WHEAT': 'WHEAT',
    'CORN': 'CORN',
    'COFFEE': 'COFFEE',
    # ...
}
```

---

## 📊 Datenfluss

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATENFLUSS                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Yahoo Finance ──┐                                                          │
│                  │                                                          │
│  Alpha Vantage ──┼──▶ MarketBot ──▶ market_data.db                         │
│                  │                        │                                 │
│  MetaAPI ────────┘                        │                                 │
│                                           ▼                                 │
│                                     SignalBot                               │
│                                           │                                 │
│                                           ▼                                 │
│                                   pending_signals[]                         │
│                                           │                                 │
│                                           ▼                                 │
│                                     TradeBot                                │
│                                           │                                 │
│                           ┌───────────────┼───────────────┐                │
│                           ▼               ▼               ▼                │
│                      MetaAPI        trades.db      trade_settings          │
│                      (MT5)                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Fehlerbehandlung

### MarketBot Fehler
- Wenn Yahoo Finance nicht erreichbar → Fallback auf MetaAPI
- Wenn kein Preis verfügbar → Skip Commodity

### SignalBot Fehler
- Wenn keine Marktdaten → Skip Analyse
- Wenn RSI/MACD fehlen → Verwende Defaults

### TradeBot Fehler
- Wenn MetaAPI nicht verbunden → Retry mit Backoff
- Wenn "Market Closed" → Trade wird nicht ausgeführt
- Wenn Portfolio-Risiko zu hoch → Trade wird übersprungen

---

## 🔧 Konfiguration

### Bot-Intervalle

```python
# In multi_bot_system.py
MarketBot:  interval = 8 Sekunden
SignalBot:  interval = 20 Sekunden
TradeBot:   interval = 12 Sekunden
```

### Min. Konfidenz

Signale werden nur ausgeführt wenn `confidence >= min_confidence`:

```python
# Standard-Werte:
mean_reversion_min_confidence: 0.70
momentum_min_confidence: 0.65
breakout_min_confidence: 0.60
day_min_confidence: 0.65
swing_min_confidence: 0.65
```

---

## 📈 Performance-Metriken

Der Bot-Status Endpoint liefert detaillierte Metriken:

```json
{
  "statistics": {
    "total_trades_executed": 25,
    "pending_signals": 3,
    "total_positions_checked": 1500,
    "commodities_tracked": 15
  },
  "bots": {
    "market_bot": {
      "run_count": 450,
      "error_count": 2,
      "avg_duration_ms": 250
    },
    "signal_bot": {
      "run_count": 150,
      "error_count": 0,
      "active_strategies": ["mean_reversion", "momentum"]
    },
    "trade_bot": {
      "run_count": 225,
      "error_count": 1
    }
  }
}
```

---

**Letzte Aktualisierung:** 17. Dezember 2025, v2.3.32
