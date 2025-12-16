import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { PlayCircle, TrendingUp, TrendingDown, BarChart3, Calendar, DollarSign, Target, AlertTriangle } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Input } from './ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

const API = process.env.REACT_APP_BACKEND_URL || '';

export default function BacktestingPanel() {
  const [strategies, setStrategies] = useState([]);
  const [commodities, setCommodities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    strategy: 'mean_reversion',
    commodity: 'GOLD',
    start_date: '2024-06-01',
    end_date: '2024-12-01',
    initial_balance: 10000,
    sl_percent: 2.0,
    tp_percent: 4.0,
    lot_size: 0.1
  });
  
  useEffect(() => {
    fetchStrategies();
  }, []);
  
  const fetchStrategies = async () => {
    try {
      const response = await axios.get(`${API}/api/backtest/strategies`);
      setStrategies(response.data.strategies || []);
      setCommodities(response.data.commodities || []);
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };
  
  const runBacktest = async () => {
    setLoading(true);
    setResult(null);
    
    try {
      const response = await axios.post(`${API}/api/backtest/run`, formData, {
        timeout: 120000 // 2 Minuten Timeout für Backtest
      });
      
      if (response.data.success) {
        setResult(response.data.result);
        toast.success('✅ Backtest abgeschlossen!');
      } else {
        toast.error('Backtest fehlgeschlagen');
      }
    } catch (error) {
      console.error('Backtest error:', error);
      toast.error('Fehler beim Backtest: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" />
          Backtesting v2.3.31
        </h2>
      </div>
      
      {/* Config Panel */}
      <Card className="bg-slate-900/50 border-slate-700 p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Strategy */}
          <div className="space-y-2">
            <Label className="text-slate-300">Strategie</Label>
            <Select
              value={formData.strategy}
              onValueChange={(value) => setFormData({...formData, strategy: value})}
            >
              <SelectTrigger className="bg-slate-800 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {strategies.map(s => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Commodity */}
          <div className="space-y-2">
            <Label className="text-slate-300">Asset</Label>
            <Select
              value={formData.commodity}
              onValueChange={(value) => setFormData({...formData, commodity: value})}
            >
              <SelectTrigger className="bg-slate-800 border-slate-600">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {commodities.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Start Date */}
          <div className="space-y-2">
            <Label className="text-slate-300">Start</Label>
            <Input
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({...formData, start_date: e.target.value})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
          
          {/* End Date */}
          <div className="space-y-2">
            <Label className="text-slate-300">Ende</Label>
            <Input
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData({...formData, end_date: e.target.value})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
          
          {/* Initial Balance */}
          <div className="space-y-2">
            <Label className="text-slate-300">Startkapital</Label>
            <Input
              type="number"
              value={formData.initial_balance}
              onChange={(e) => setFormData({...formData, initial_balance: parseFloat(e.target.value)})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
          
          {/* SL */}
          <div className="space-y-2">
            <Label className="text-slate-300">Stop Loss %</Label>
            <Input
              type="number"
              step="0.1"
              value={formData.sl_percent}
              onChange={(e) => setFormData({...formData, sl_percent: parseFloat(e.target.value)})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
          
          {/* TP */}
          <div className="space-y-2">
            <Label className="text-slate-300">Take Profit %</Label>
            <Input
              type="number"
              step="0.1"
              value={formData.tp_percent}
              onChange={(e) => setFormData({...formData, tp_percent: parseFloat(e.target.value)})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
          
          {/* Lot Size */}
          <div className="space-y-2">
            <Label className="text-slate-300">Lot Size</Label>
            <Input
              type="number"
              step="0.01"
              value={formData.lot_size}
              onChange={(e) => setFormData({...formData, lot_size: parseFloat(e.target.value)})}
              className="bg-slate-800 border-slate-600"
            />
          </div>
        </div>
        
        <Button 
          onClick={runBacktest}
          disabled={loading}
          className="mt-4 bg-purple-600 hover:bg-purple-700"
        >
          {loading ? (
            <>
              <div className="animate-spin mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
              Backtest läuft...
            </>
          ) : (
            <>
              <PlayCircle className="w-4 h-4 mr-2" />
              Backtest starten
            </>
          )}
        </Button>
      </Card>
      
      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* PnL */}
            <Card className={`p-4 ${result.total_pnl >= 0 ? 'bg-emerald-900/30 border-emerald-700' : 'bg-red-900/30 border-red-700'}`}>
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <DollarSign className="w-4 h-4" />
                Gesamt P/L
              </div>
              <div className={`text-2xl font-bold ${result.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {result.total_pnl >= 0 ? '+' : ''}{result.total_pnl?.toFixed(2)}€
              </div>
            </Card>
            
            {/* Win Rate */}
            <Card className="bg-slate-900/50 border-slate-700 p-4">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Target className="w-4 h-4" />
                Win Rate
              </div>
              <div className={`text-2xl font-bold ${result.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {result.win_rate?.toFixed(1)}%
              </div>
              <div className="text-xs text-slate-500">
                {result.winning_trades}W / {result.losing_trades}L
              </div>
            </Card>
            
            {/* Total Trades */}
            <Card className="bg-slate-900/50 border-slate-700 p-4">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <BarChart3 className="w-4 h-4" />
                Trades
              </div>
              <div className="text-2xl font-bold text-white">
                {result.total_trades}
              </div>
            </Card>
            
            {/* Max Drawdown */}
            <Card className="bg-slate-900/50 border-slate-700 p-4">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <AlertTriangle className="w-4 h-4" />
                Max Drawdown
              </div>
              <div className={`text-2xl font-bold ${result.max_drawdown <= 10 ? 'text-emerald-400' : result.max_drawdown <= 20 ? 'text-amber-400' : 'text-red-400'}`}>
                {result.max_drawdown?.toFixed(1)}%
              </div>
            </Card>
          </div>
          
          {/* Additional Metrics */}
          <Card className="bg-slate-900/50 border-slate-700 p-4">
            <h3 className="text-lg font-semibold text-white mb-3">Performance Metriken</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-slate-400">Sharpe Ratio</div>
                <div className={`text-lg font-semibold ${result.sharpe_ratio >= 1 ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {result.sharpe_ratio?.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-sm text-slate-400">Profit Factor</div>
                <div className={`text-lg font-semibold ${result.profit_factor >= 1 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {result.profit_factor?.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-sm text-slate-400">Ø Trade Dauer</div>
                <div className="text-lg font-semibold text-slate-300">
                  {result.avg_trade_duration?.toFixed(1)}h
                </div>
              </div>
              <div>
                <div className="text-sm text-slate-400">Endkapital</div>
                <div className={`text-lg font-semibold ${result.final_balance >= result.initial_balance ? 'text-emerald-400' : 'text-red-400'}`}>
                  {result.final_balance?.toFixed(2)}€
                </div>
              </div>
            </div>
          </Card>
          
          {/* Trade List */}
          {result.trades && result.trades.length > 0 && (
            <Card className="bg-slate-900/50 border-slate-700 p-4">
              <h3 className="text-lg font-semibold text-white mb-3">Letzte Trades</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700">
                      <th className="text-left py-2">#</th>
                      <th className="text-left py-2">Typ</th>
                      <th className="text-right py-2">Einstieg</th>
                      <th className="text-right py-2">Ausstieg</th>
                      <th className="text-right py-2">P/L</th>
                      <th className="text-left py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(0, 10).map((trade, idx) => (
                      <tr key={trade.id || idx} className="border-b border-slate-800">
                        <td className="py-2 text-slate-400">{trade.id}</td>
                        <td className={`py-2 ${trade.action === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>
                          {trade.action}
                        </td>
                        <td className="py-2 text-right text-slate-300">{trade.entry_price?.toFixed(2)}</td>
                        <td className="py-2 text-right text-slate-300">{trade.exit_price?.toFixed(2)}</td>
                        <td className={`py-2 text-right font-semibold ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {trade.pnl >= 0 ? '+' : ''}{trade.pnl?.toFixed(2)}
                        </td>
                        <td className="py-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            trade.status === 'CLOSED_TP' ? 'bg-emerald-900 text-emerald-300' :
                            trade.status === 'CLOSED_SL' ? 'bg-red-900 text-red-300' :
                            'bg-slate-700 text-slate-300'
                          }`}>
                            {trade.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
