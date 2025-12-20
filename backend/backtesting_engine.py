"""
📊 Booner Trade v2.3.31 - Backtesting Engine
============================================
Ermöglicht das Testen von Trading-Strategien gegen historische Daten:
- Historische Daten laden (Yahoo Finance)
- Strategien simulieren
- Performance-Metriken berechnen
- Visualisierbare Ergebnisse
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Einzelner Trade im Backtest"""
    id: int
    entry_time: datetime
    exit_time: Optional[datetime]
    commodity: str
    action: str  # BUY or SELL
    entry_price: float
    exit_price: Optional[float]
    lot_size: float
    stop_loss: float
    take_profit: float
    pnl: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED_TP, CLOSED_SL, CLOSED_TIME
    

@dataclass
class BacktestResult:
    """Ergebnis eines Backtests"""
    strategy_name: str
    commodity: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    avg_trade_duration: float  # in Stunden
    trades: List[Dict] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)


class BacktestingEngine:
    """
    Backtesting Engine für Trading-Strategien
    
    Usage:
        engine = BacktestingEngine()
        result = await engine.run_backtest(
            strategy="mean_reversion",
            commodity="GOLD",
            start_date="2024-01-01",
            end_date="2024-12-01",
            initial_balance=10000
        )
    """
    
    def __init__(self):
        self.historical_data: Dict[str, List[Dict]] = {}
        self.current_balance = 0
        self.trades: List[BacktestTrade] = []
        self.trade_counter = 0
        self.equity_curve: List[Dict] = []
        logger.info("📊 BacktestingEngine initialized")
    
    async def load_historical_data(self, commodity: str, start_date: str, end_date: str) -> List[Dict]:
        """Lädt historische Daten von Yahoo Finance"""
        try:
            import yfinance as yf
            
            # Symbol Mapping
            symbol_map = {
                'GOLD': 'GC=F',
                'SILVER': 'SI=F',
                'PLATINUM': 'PL=F',
                'PALLADIUM': 'PA=F',
                'CRUDE_OIL': 'CL=F',
                'BRENT_CRUDE': 'BZ=F',
                'NATURAL_GAS': 'NG=F',
                'EURUSD': 'EURUSD=X',
                'GBPUSD': 'GBPUSD=X',
                'USDJPY': 'USDJPY=X',
                'BTCUSD': 'BTC-USD',
                'ETHUSD': 'ETH-USD'
            }
            
            symbol = symbol_map.get(commodity, commodity)
            
            logger.info(f"📥 Loading historical data for {commodity} ({symbol})")
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1h')
            
            if df.empty:
                # Fallback zu täglichen Daten
                df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if df.empty:
                logger.warning(f"No historical data found for {commodity}")
                return []
            
            # Konvertiere zu Liste von Dicts
            data = []
            for idx, row in df.iterrows():
                data.append({
                    'timestamp': idx.isoformat(),
                    'open': row['Open'],
                    'high': row['High'],
                    'low': row['Low'],
                    'close': row['Close'],
                    'volume': row.get('Volume', 0)
                })
            
            self.historical_data[commodity] = data
            logger.info(f"✅ Loaded {len(data)} data points for {commodity}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return []
    
    async def run_backtest(self,
                          strategy: str,
                          commodity: str,
                          start_date: str,
                          end_date: str,
                          initial_balance: float = 10000,
                          sl_percent: float = 2.0,
                          tp_percent: float = 4.0,
                          lot_size: float = 0.1) -> BacktestResult:
        """
        Führt einen Backtest durch
        
        Args:
            strategy: Name der Strategie (mean_reversion, momentum, breakout, etc.)
            commodity: Rohstoff/Asset
            start_date: Start-Datum (YYYY-MM-DD)
            end_date: End-Datum (YYYY-MM-DD)
            initial_balance: Startkapital
            sl_percent: Stop Loss in Prozent
            tp_percent: Take Profit in Prozent
            lot_size: Lot Size pro Trade
        """
        logger.info(f"🚀 Starting backtest: {strategy} on {commodity}")
        
        # Reset State
        self.current_balance = initial_balance
        self.trades = []
        self.trade_counter = 0
        self.equity_curve = []
        
        # Lade historische Daten
        data = await self.load_historical_data(commodity, start_date, end_date)
        
        if not data:
            return BacktestResult(
                strategy_name=strategy,
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                final_balance=initial_balance,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                max_drawdown=0,
                sharpe_ratio=0,
                profit_factor=0,
                avg_trade_duration=0
            )
        
        # Berechne Indikatoren
        data = self._calculate_indicators(data)
        
        # Simuliere Trading
        open_trade: Optional[BacktestTrade] = None
        peak_balance = initial_balance
        max_drawdown = 0
        
        for i, candle in enumerate(data):
            timestamp = datetime.fromisoformat(candle['timestamp'].replace('Z', '+00:00')) if isinstance(candle['timestamp'], str) else candle['timestamp']
            price = candle['close']
            
            # Update Equity Curve
            current_equity = self.current_balance
            if open_trade:
                unrealized_pnl = self._calculate_pnl(open_trade, price)
                current_equity += unrealized_pnl
            
            self.equity_curve.append({
                'timestamp': candle['timestamp'],
                'equity': current_equity,
                'balance': self.current_balance
            })
            
            # Update Max Drawdown
            if current_equity > peak_balance:
                peak_balance = current_equity
            drawdown = ((peak_balance - current_equity) / peak_balance) * 100
            max_drawdown = max(max_drawdown, drawdown)
            
            # Prüfe offenen Trade auf SL/TP
            if open_trade:
                should_close, close_reason = self._check_sl_tp(open_trade, candle)
                if should_close:
                    self._close_trade(open_trade, price, timestamp, close_reason)
                    open_trade = None
            
            # Generiere Signal wenn kein offener Trade
            if not open_trade:
                signal = self._generate_signal(strategy, candle, data[:i+1])
                
                if signal in ['BUY', 'SELL']:
                    open_trade = self._open_trade(
                        timestamp=timestamp,
                        commodity=commodity,
                        action=signal,
                        price=price,
                        lot_size=lot_size,
                        sl_percent=sl_percent,
                        tp_percent=tp_percent
                    )
        
        # Schließe offenen Trade am Ende
        if open_trade and data:
            final_price = data[-1]['close']
            final_time = datetime.fromisoformat(data[-1]['timestamp'].replace('Z', '+00:00')) if isinstance(data[-1]['timestamp'], str) else data[-1]['timestamp']
            self._close_trade(open_trade, final_price, final_time, "END_OF_BACKTEST")
        
        # Berechne Statistiken
        return self._calculate_statistics(
            strategy, commodity, start_date, end_date, 
            initial_balance, max_drawdown
        )
    
    def _calculate_indicators(self, data: List[Dict]) -> List[Dict]:
        """Berechnet technische Indikatoren für die Daten"""
        closes = [d['close'] for d in data]
        
        for i, candle in enumerate(data):
            # SMA 20
            if i >= 19:
                candle['sma_20'] = sum(closes[i-19:i+1]) / 20
            else:
                candle['sma_20'] = candle['close']
            
            # EMA 20
            if i == 0:
                candle['ema_20'] = candle['close']
            else:
                multiplier = 2 / (20 + 1)
                candle['ema_20'] = (candle['close'] - data[i-1].get('ema_20', candle['close'])) * multiplier + data[i-1].get('ema_20', candle['close'])
            
            # RSI 14
            if i >= 14:
                gains = []
                losses = []
                for j in range(i-13, i+1):
                    change = closes[j] - closes[j-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                avg_gain = sum(gains) / 14
                avg_loss = sum(losses) / 14
                
                if avg_loss == 0:
                    candle['rsi'] = 100
                else:
                    rs = avg_gain / avg_loss
                    candle['rsi'] = 100 - (100 / (1 + rs))
            else:
                candle['rsi'] = 50
            
            # Bollinger Bands (für Mean Reversion)
            if i >= 19:
                sma = candle['sma_20']
                variance = sum((closes[j] - sma) ** 2 for j in range(i-19, i+1)) / 20
                std = variance ** 0.5
                candle['bb_upper'] = sma + (2 * std)
                candle['bb_lower'] = sma - (2 * std)
            else:
                candle['bb_upper'] = candle['close'] * 1.02
                candle['bb_lower'] = candle['close'] * 0.98
            
            # Trend
            if candle['close'] > candle['sma_20']:
                candle['trend'] = 'bullish'
            elif candle['close'] < candle['sma_20']:
                candle['trend'] = 'bearish'
            else:
                candle['trend'] = 'neutral'
        
        return data
    
    def _generate_signal(self, strategy: str, candle: Dict, history: List[Dict]) -> str:
        """Generiert ein Trading-Signal basierend auf der Strategie"""
        
        price = candle['close']
        rsi = candle.get('rsi', 50)
        sma = candle.get('sma_20', price)
        bb_upper = candle.get('bb_upper', price * 1.02)
        bb_lower = candle.get('bb_lower', price * 0.98)
        trend = candle.get('trend', 'neutral')
        
        # V2.3.35: Verbesserte Backtest-Strategien
        
        if strategy == 'mean_reversion':
            # Mean Reversion: Kaufe bei überverkauft, verkaufe bei überkauft
            if price <= bb_lower and rsi < 35:
                return 'BUY'
            elif price >= bb_upper and rsi > 65:
                return 'SELL'
                
        elif strategy == 'momentum':
            # Momentum: Folge dem starken Trend
            if rsi > 55 and trend == 'bullish' and price > sma * 1.005:
                return 'BUY'
            elif rsi < 45 and trend == 'bearish' and price < sma * 0.995:
                return 'SELL'
                
        elif strategy == 'breakout':
            # Breakout: Handele bei Ausbruch aus Range
            if len(history) >= 20:
                recent_high = max(h['high'] for h in history[-20:])
                recent_low = min(h['low'] for h in history[-20:])
                range_size = recent_high - recent_low
                
                if price > recent_high and range_size > 0:  # Klarer Breakout nach oben
                    return 'BUY'
                elif price < recent_low and range_size > 0:  # Klarer Breakout nach unten
                    return 'SELL'
                    
        elif strategy == 'day_trading':
            # Day Trading: Kombinierte Signale
            if rsi < 40 and trend == 'bullish':
                return 'BUY'
            elif rsi > 60 and trend == 'bearish':
                return 'SELL'
                
        elif strategy == 'scalping':
            # Scalping: Schnelle Trades bei RSI-Extremen
            if rsi < 30:
                return 'BUY'
            elif rsi > 70:
                return 'SELL'
        
        elif strategy == 'swing_trading':
            # Swing Trading: Mittelfristige Trendfolge
            if len(history) >= 5:
                recent_closes = [h['close'] for h in history[-5:]]
                avg_recent = sum(recent_closes) / len(recent_closes)
                
                if price > avg_recent and rsi > 45 and rsi < 70 and trend == 'bullish':
                    return 'BUY'
                elif price < avg_recent and rsi < 55 and rsi > 30 and trend == 'bearish':
                    return 'SELL'
        
        elif strategy == 'grid':
            # Grid Trading: Kaufe in regelmäßigen Abständen
            if len(history) >= 10:
                avg_price = sum(h['close'] for h in history[-10:]) / 10
                deviation = (price - avg_price) / avg_price * 100
                
                if deviation < -1.5:  # 1.5% unter Durchschnitt
                    return 'BUY'
                elif deviation > 1.5:  # 1.5% über Durchschnitt
                    return 'SELL'
        
        return 'HOLD'
    
    def _open_trade(self, timestamp: datetime, commodity: str, action: str,
                   price: float, lot_size: float, sl_percent: float, tp_percent: float) -> BacktestTrade:
        """Öffnet einen neuen Trade"""
        self.trade_counter += 1
        
        if action == 'BUY':
            stop_loss = price * (1 - sl_percent / 100)
            take_profit = price * (1 + tp_percent / 100)
        else:
            stop_loss = price * (1 + sl_percent / 100)
            take_profit = price * (1 - tp_percent / 100)
        
        trade = BacktestTrade(
            id=self.trade_counter,
            entry_time=timestamp,
            exit_time=None,
            commodity=commodity,
            action=action,
            entry_price=price,
            exit_price=None,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        logger.debug(f"📈 Opened {action} trade #{trade.id} @ {price:.2f}")
        return trade
    
    def _check_sl_tp(self, trade: BacktestTrade, candle: Dict) -> tuple:
        """Prüft ob SL oder TP erreicht wurde"""
        high = candle['high']
        low = candle['low']
        
        if trade.action == 'BUY':
            if low <= trade.stop_loss:
                return True, 'CLOSED_SL'
            elif high >= trade.take_profit:
                return True, 'CLOSED_TP'
        else:  # SELL
            if high >= trade.stop_loss:
                return True, 'CLOSED_SL'
            elif low <= trade.take_profit:
                return True, 'CLOSED_TP'
        
        return False, None
    
    def _close_trade(self, trade: BacktestTrade, price: float, timestamp: datetime, reason: str):
        """Schließt einen Trade"""
        trade.exit_time = timestamp
        trade.exit_price = price
        trade.status = reason
        trade.pnl = self._calculate_pnl(trade, price)
        
        self.current_balance += trade.pnl
        self.trades.append(trade)
        
        logger.debug(f"📉 Closed trade #{trade.id}: {reason}, PnL: {trade.pnl:.2f}")
    
    def _calculate_pnl(self, trade: BacktestTrade, current_price: float) -> float:
        """Berechnet den PnL eines Trades"""
        if trade.action == 'BUY':
            return (current_price - trade.entry_price) * trade.lot_size * 100
        else:
            return (trade.entry_price - current_price) * trade.lot_size * 100
    
    def _calculate_statistics(self, strategy: str, commodity: str, 
                            start_date: str, end_date: str,
                            initial_balance: float, max_drawdown: float) -> BacktestResult:
        """Berechnet die Backtest-Statistiken"""
        
        total_trades = len(self.trades)
        
        if total_trades == 0:
            return BacktestResult(
                strategy_name=strategy,
                commodity=commodity,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                final_balance=self.current_balance,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                max_drawdown=max_drawdown,
                sharpe_ratio=0,
                profit_factor=0,
                avg_trade_duration=0
            )
        
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        
        win_rate = (winning_trades / total_trades) * 100
        total_pnl = sum(t.pnl for t in self.trades)
        
        # Profit Factor
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe Ratio (vereinfacht)
        returns = [t.pnl / initial_balance for t in self.trades]
        if len(returns) > 1:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_return = variance ** 0.5
            sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Average Trade Duration
        durations = []
        for t in self.trades:
            if t.exit_time and t.entry_time:
                duration = (t.exit_time - t.entry_time).total_seconds() / 3600
                durations.append(duration)
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Trades als Dicts
        trades_list = []
        for t in self.trades:
            trades_list.append({
                'id': t.id,
                'entry_time': t.entry_time.isoformat() if t.entry_time else None,
                'exit_time': t.exit_time.isoformat() if t.exit_time else None,
                'action': t.action,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'status': t.status
            })
        
        result = BacktestResult(
            strategy_name=strategy,
            commodity=commodity,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            final_balance=self.current_balance,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            total_pnl=round(total_pnl, 2),
            max_drawdown=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            profit_factor=round(profit_factor, 2),
            avg_trade_duration=round(avg_duration, 2),
            trades=trades_list,
            equity_curve=self.equity_curve[-100:]  # Letzte 100 Punkte
        )
        
        logger.info(f"✅ Backtest complete: {total_trades} trades, Win Rate: {win_rate:.1f}%, PnL: {total_pnl:.2f}")
        
        return result


# Singleton
backtesting_engine = BacktestingEngine()

__all__ = ['BacktestingEngine', 'backtesting_engine', 'BacktestResult', 'BacktestTrade']
