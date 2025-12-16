import { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, AlertTriangle, TrendingUp, BarChart3, RefreshCw } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

const API = process.env.REACT_APP_BACKEND_URL || '';

export default function RiskDashboard() {
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchRiskStatus();
    const interval = setInterval(fetchRiskStatus, 30000); // Alle 30 Sekunden aktualisieren
    return () => clearInterval(interval);
  }, []);
  
  const fetchRiskStatus = async () => {
    try {
      const response = await axios.get(`${API}/api/risk/status`);
      if (response.data.success) {
        setRiskData(response.data);
      }
    } catch (error) {
      console.error('Error fetching risk status:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const getRiskColor = (percent, max = 20) => {
    const ratio = percent / max;
    if (ratio < 0.5) return 'text-emerald-400';
    if (ratio < 0.75) return 'text-amber-400';
    return 'text-red-400';
  };
  
  const getProgressColor = (percent, max = 20) => {
    const ratio = percent / max;
    if (ratio < 0.5) return 'bg-emerald-500';
    if (ratio < 0.75) return 'bg-amber-500';
    return 'bg-red-500';
  };
  
  if (loading) {
    return (
      <Card className="bg-slate-900/50 border-slate-700 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full" />
        </div>
      </Card>
    );
  }
  
  const limits = riskData?.risk_limits || {};
  const distribution = riskData?.broker_distribution || {};
  const summary = distribution._summary || {};
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-emerald-400" />
          Risk Dashboard v2.3.31
        </h2>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchRiskStatus}
          className="border-slate-600"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Aktualisieren
        </Button>
      </div>
      
      {/* Risk Limits */}
      <Card className="bg-slate-900/50 border-slate-700 p-4">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Risiko-Limits
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-sm text-slate-400">Max Portfolio-Risiko</div>
            <div className="text-2xl font-bold text-emerald-400">
              {limits.max_portfolio_risk_percent || 20}%
            </div>
            <div className="text-xs text-slate-500">pro Broker</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-sm text-slate-400">Max Trade-Risiko</div>
            <div className="text-2xl font-bold text-amber-400">
              {limits.max_single_trade_risk_percent || 2}%
            </div>
            <div className="text-xs text-slate-500">pro Trade</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-sm text-slate-400">Min Freie Margin</div>
            <div className="text-2xl font-bold text-blue-400">
              {limits.min_free_margin_percent || 30}%
            </div>
            <div className="text-xs text-slate-500">behalten</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-sm text-slate-400">Max Drawdown</div>
            <div className="text-2xl font-bold text-red-400">
              {limits.max_drawdown_percent || 15}%
            </div>
            <div className="text-xs text-slate-500">Limit</div>
          </div>
        </div>
      </Card>
      
      {/* Portfolio Summary */}
      <Card className="bg-slate-900/50 border-slate-700 p-4">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-400" />
          Portfolio Übersicht
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-slate-400">Gesamt Balance</div>
            <div className="text-xl font-bold text-white">
              €{summary.total_balance?.toLocaleString('de-DE', { minimumFractionDigits: 2 }) || '0.00'}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-400">Gesamt Equity</div>
            <div className="text-xl font-bold text-white">
              €{summary.total_equity?.toLocaleString('de-DE', { minimumFractionDigits: 2 }) || '0.00'}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-400">Offene Positionen</div>
            <div className="text-xl font-bold text-white">
              {summary.total_positions || 0}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-400">Ø Risiko</div>
            <div className={`text-xl font-bold ${getRiskColor(summary.avg_risk_percent || 0)}`}>
              {(summary.avg_risk_percent || 0).toFixed(1)}%
            </div>
          </div>
        </div>
      </Card>
      
      {/* Broker Distribution */}
      <Card className="bg-slate-900/50 border-slate-700 p-4">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          Broker Verteilung
        </h3>
        <div className="space-y-4">
          {Object.entries(distribution)
            .filter(([key]) => !key.startsWith('_'))
            .map(([broker, data]) => (
              <div key={broker} className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${data.is_available ? 'bg-emerald-400' : 'bg-red-400'}`} />
                    <span className="font-semibold text-white">{broker}</span>
                    {!data.is_available && (
                      <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded">
                        Limit erreicht
                      </span>
                    )}
                  </div>
                  <span className={`font-bold ${getRiskColor(data.risk_percent || 0)}`}>
                    {(data.risk_percent || 0).toFixed(1)}% / {limits.max_portfolio_risk_percent || 20}%
                  </span>
                </div>
                
                {/* Risk Progress Bar */}
                <div className="relative h-3 bg-slate-700 rounded-full overflow-hidden mb-2">
                  <div 
                    className={`absolute left-0 top-0 h-full ${getProgressColor(data.risk_percent || 0)} transition-all`}
                    style={{ width: `${Math.min(100, (data.risk_percent / (limits.max_portfolio_risk_percent || 20)) * 100)}%` }}
                  />
                </div>
                
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Balance:</span>
                    <span className="ml-2 text-white">€{(data.balance || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Equity:</span>
                    <span className="ml-2 text-white">€{(data.equity || 0).toLocaleString('de-DE', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Positionen:</span>
                    <span className="ml-2 text-white">{data.open_positions || 0}</span>
                  </div>
                </div>
              </div>
            ))}
          
          {Object.keys(distribution).filter(k => !k.startsWith('_')).length === 0 && (
            <div className="text-center py-8 text-slate-400">
              Keine Broker verbunden
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
