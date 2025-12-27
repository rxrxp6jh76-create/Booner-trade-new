/**
 * 🧠 AI INTELLIGENCE WIDGET V3.5
 * ================================
 * 
 * Dashboard-Komponente für KI-Transparenz:
 * 1. Weight Drift Chart - Historische Gewichts-Änderungen
 * 2. Pillar Efficiency Radar - Score-zu-Profit Korrelation
 * 3. Auditor Log - Blockierte Trades mit Begründung
 * 
 * @version 3.5.0
 */

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Brain, 
  TrendingUp, 
  Shield, 
  AlertTriangle, 
  RefreshCw,
  Eye,
  Target,
  Activity
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

// ═══════════════════════════════════════════════════════════════════════════
// WEIGHT DRIFT CHART COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const WeightDriftChart = ({ data, asset }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500">
        <p>Keine Weight-History für {asset || 'dieses Asset'} verfügbar</p>
      </div>
    );
  }

  // Berechne max für Skalierung
  const maxWeight = 60;
  
  // Farben für die Säulen
  const colors = {
    base_signal: '#3b82f6',      // Blau
    trend_confluence: '#10b981', // Grün
    volatility: '#f59e0b',       // Orange
    sentiment: '#8b5cf6'         // Lila
  };

  return (
    <div className="space-y-4">
      {/* Chart Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-slate-300">
          Gewichts-Entwicklung (letzte 30 Tage)
        </h4>
        <div className="flex gap-2 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span> Basis
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Trend
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span> Vola
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-violet-500"></span> Sentiment
          </span>
        </div>
      </div>

      {/* Stacked Bar Chart */}
      <div className="flex items-end gap-1 h-40">
        {data.slice(-14).map((entry, idx) => {
          const total = entry.base_signal_weight + entry.trend_confluence_weight + 
                       entry.volatility_weight + entry.sentiment_weight;
          const scale = 100 / total; // Normalisieren auf 100%
          
          return (
            <div 
              key={idx} 
              className="flex-1 flex flex-col-reverse rounded-t overflow-hidden"
              title={`${new Date(entry.timestamp).toLocaleDateString('de-DE')}`}
            >
              <div 
                style={{ height: `${entry.base_signal_weight * scale}%` }}
                className="bg-blue-500 transition-all duration-300"
              />
              <div 
                style={{ height: `${entry.trend_confluence_weight * scale}%` }}
                className="bg-emerald-500 transition-all duration-300"
              />
              <div 
                style={{ height: `${entry.volatility_weight * scale}%` }}
                className="bg-amber-500 transition-all duration-300"
              />
              <div 
                style={{ height: `${entry.sentiment_weight * scale}%` }}
                className="bg-violet-500 transition-all duration-300"
              />
            </div>
          );
        })}
      </div>

      {/* Current Weights */}
      {data.length > 0 && (
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="bg-blue-500/20 rounded p-2 text-center">
            <div className="text-blue-400 font-bold">
              {data[data.length - 1].base_signal_weight.toFixed(1)}%
            </div>
            <div className="text-slate-500">Basis</div>
          </div>
          <div className="bg-emerald-500/20 rounded p-2 text-center">
            <div className="text-emerald-400 font-bold">
              {data[data.length - 1].trend_confluence_weight.toFixed(1)}%
            </div>
            <div className="text-slate-500">Trend</div>
          </div>
          <div className="bg-amber-500/20 rounded p-2 text-center">
            <div className="text-amber-400 font-bold">
              {data[data.length - 1].volatility_weight.toFixed(1)}%
            </div>
            <div className="text-slate-500">Vola</div>
          </div>
          <div className="bg-violet-500/20 rounded p-2 text-center">
            <div className="text-violet-400 font-bold">
              {data[data.length - 1].sentiment_weight.toFixed(1)}%
            </div>
            <div className="text-slate-500">Sentiment</div>
          </div>
        </div>
      )}
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════════
// PILLAR EFFICIENCY RADAR COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const PillarEfficiencyRadar = ({ efficiencyData }) => {
  if (!efficiencyData) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500">
        <p>Effizienz-Daten werden berechnet...</p>
      </div>
    );
  }

  const { base_signal, trend_confluence, volatility, sentiment } = efficiencyData;
  
  // SVG Radar Chart
  const size = 200;
  const center = size / 2;
  const maxRadius = 80;
  
  // Berechne Punkte für das Radar
  const points = [
    { angle: -90, value: base_signal || 50, label: 'Basis', color: '#3b82f6' },
    { angle: 0, value: trend_confluence || 50, label: 'Trend', color: '#10b981' },
    { angle: 90, value: volatility || 50, label: 'Vola', color: '#f59e0b' },
    { angle: 180, value: sentiment || 50, label: 'Sentiment', color: '#8b5cf6' }
  ];

  const getPoint = (angle, value) => {
    const radians = (angle * Math.PI) / 180;
    const radius = (value / 100) * maxRadius;
    return {
      x: center + radius * Math.cos(radians),
      y: center + radius * Math.sin(radians)
    };
  };

  const radarPoints = points.map(p => getPoint(p.angle, p.value));
  const pathData = radarPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="overflow-visible">
        {/* Grid circles */}
        {[25, 50, 75, 100].map(level => (
          <circle
            key={level}
            cx={center}
            cy={center}
            r={(level / 100) * maxRadius}
            fill="none"
            stroke="#334155"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}
        
        {/* Axis lines */}
        {points.map((p, i) => {
          const end = getPoint(p.angle, 100);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={end.x}
              y2={end.y}
              stroke="#475569"
              strokeWidth="1"
            />
          );
        })}
        
        {/* Data polygon */}
        <path
          d={pathData}
          fill="rgba(59, 130, 246, 0.2)"
          stroke="#3b82f6"
          strokeWidth="2"
        />
        
        {/* Data points */}
        {radarPoints.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="5"
            fill={points[i].color}
            stroke="#1e293b"
            strokeWidth="2"
          />
        ))}
        
        {/* Labels */}
        {points.map((p, i) => {
          const labelPos = getPoint(p.angle, 120);
          return (
            <text
              key={i}
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-xs fill-slate-400"
            >
              {p.label}
            </text>
          );
        })}
      </svg>
      
      {/* Efficiency Scores */}
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs w-full">
        {points.map((p, i) => (
          <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded px-2 py-1">
            <span className="text-slate-400">{p.label}:</span>
            <span style={{ color: p.color }} className="font-bold">
              {p.value.toFixed(0)}% Effizienz
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════════
// AUDITOR LOG COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const AuditorLog = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-500">
        <Shield className="w-12 h-12 mb-2 opacity-50" />
        <p>Keine blockierten Trades in den letzten 24h</p>
        <p className="text-xs text-slate-600">Das ist gut! 🎉</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {logs.slice(0, 5).map((log, idx) => (
        <div 
          key={idx} 
          className={`rounded-lg p-3 border ${
            log.blocked 
              ? 'bg-red-500/10 border-red-500/30' 
              : 'bg-amber-500/10 border-amber-500/30'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Badge variant={log.blocked ? "destructive" : "warning"}>
                {log.blocked ? '❌ BLOCKIERT' : '⚠️ WARNUNG'}
              </Badge>
              <span className="text-sm font-medium text-slate-300">
                {log.commodity} {log.signal}
              </span>
            </div>
            <span className="text-xs text-slate-500">
              {new Date(log.timestamp).toLocaleString('de-DE')}
            </span>
          </div>
          
          <div className="grid grid-cols-3 gap-2 text-xs mb-2">
            <div>
              <span className="text-slate-500">Original:</span>
              <span className="ml-1 text-slate-300">{log.original_score?.toFixed(1)}%</span>
            </div>
            <div>
              <span className="text-slate-500">Korrektur:</span>
              <span className={`ml-1 ${log.score_adjustment < 0 ? 'text-red-400' : 'text-green-400'}`}>
                {log.score_adjustment?.toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-slate-500">Final:</span>
              <span className="ml-1 text-slate-300">{log.adjusted_score?.toFixed(1)}%</span>
            </div>
          </div>
          
          {log.red_flags && (
            <div className="flex flex-wrap gap-1 mb-2">
              {JSON.parse(log.red_flags || '[]').map((flag, i) => (
                <Badge key={i} variant="outline" className="text-xs border-red-500/50 text-red-400">
                  🚩 {flag}
                </Badge>
              ))}
            </div>
          )}
          
          {log.auditor_reasoning && (
            <p className="text-xs text-slate-400 italic border-l-2 border-slate-600 pl-2">
              "{log.auditor_reasoning}"
            </p>
          )}
        </div>
      ))}
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════════
// MAIN AI INTELLIGENCE WIDGET
// ═══════════════════════════════════════════════════════════════════════════

const AIIntelligenceWidget = ({ selectedAsset = 'GOLD' }) => {
  const [activeTab, setActiveTab] = useState('weights');
  const [weightHistory, setWeightHistory] = useState([]);
  const [efficiencyData, setEfficiencyData] = useState(null);
  const [auditorLogs, setAuditorLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch all data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      // Parallel fetches
      const [weightsRes, efficiencyRes, logsRes] = await Promise.all([
        axios.get(`${API}/api/ai/weight-history?asset=${selectedAsset}`).catch(() => ({ data: [] })),
        axios.get(`${API}/api/ai/pillar-efficiency?asset=${selectedAsset}`).catch(() => ({ data: null })),
        axios.get(`${API}/api/ai/auditor-log?limit=5`).catch(() => ({ data: [] }))
      ]);

      setWeightHistory(weightsRes.data || []);
      setEfficiencyData(efficiencyRes.data);
      setAuditorLogs(logsRes.data || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch AI Intelligence data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedAsset]);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <Card className="bg-slate-900/50 border-slate-700">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="w-5 h-5 text-cyan-400" />
            <span className="text-slate-200">AI Intelligence</span>
            <Badge variant="outline" className="ml-2 text-xs border-cyan-500/50 text-cyan-400">
              V3.5
            </Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            {lastUpdate && (
              <span className="text-xs text-slate-500">
                Update: {lastUpdate.toLocaleTimeString('de-DE')}
              </span>
            )}
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={fetchData}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-3 bg-slate-800/50 mb-4">
            <TabsTrigger value="weights" className="text-xs">
              <TrendingUp className="w-3 h-3 mr-1" />
              Weight Drift
            </TabsTrigger>
            <TabsTrigger value="efficiency" className="text-xs">
              <Target className="w-3 h-3 mr-1" />
              Effizienz
            </TabsTrigger>
            <TabsTrigger value="auditor" className="text-xs">
              <Shield className="w-3 h-3 mr-1" />
              Auditor Log
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="weights" className="mt-0">
            <WeightDriftChart data={weightHistory} asset={selectedAsset} />
          </TabsContent>
          
          <TabsContent value="efficiency" className="mt-0">
            <PillarEfficiencyRadar efficiencyData={efficiencyData} />
          </TabsContent>
          
          <TabsContent value="auditor" className="mt-0">
            <AuditorLog logs={auditorLogs} />
          </TabsContent>
        </Tabs>
        
        {/* Quick Stats Footer */}
        <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-3 gap-2 text-xs">
          <div className="text-center">
            <div className="text-cyan-400 font-bold">
              {auditorLogs.filter(l => l.blocked).length}
            </div>
            <div className="text-slate-500">Blockiert (24h)</div>
          </div>
          <div className="text-center">
            <div className="text-emerald-400 font-bold">
              {weightHistory.length > 0 
                ? `${weightHistory[weightHistory.length - 1]?.win_rate?.toFixed(0) || 0}%`
                : '-'}
            </div>
            <div className="text-slate-500">Win Rate</div>
          </div>
          <div className="text-center">
            <div className="text-violet-400 font-bold">
              {weightHistory.length}
            </div>
            <div className="text-slate-500">Optimierungen</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default AIIntelligenceWidget;
