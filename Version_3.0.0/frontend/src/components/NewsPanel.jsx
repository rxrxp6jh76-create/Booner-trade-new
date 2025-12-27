import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  Newspaper, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  RefreshCw,
  Clock,
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || '';

// Impact Badge Farben
const impactColors = {
  high: 'bg-red-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-green-500 text-white'
};

// Richtungs-Icons
const DirectionIcon = ({ direction }) => {
  switch (direction) {
    case 'bullish':
      return <TrendingUp className="w-4 h-4 text-green-400" />;
    case 'bearish':
      return <TrendingDown className="w-4 h-4 text-red-400" />;
    default:
      return <Minus className="w-4 h-4 text-gray-400" />;
  }
};

// Status Icon
const StatusIcon = ({ status }) => {
  switch (status) {
    case 'OK':
      return <CheckCircle className="w-4 h-4 text-green-400" />;
    case 'ERROR':
      return <XCircle className="w-4 h-4 text-red-400" />;
    case 'WARNING':
      return <AlertCircle className="w-4 h-4 text-yellow-400" />;
    default:
      return <Minus className="w-4 h-4 text-gray-400" />;
  }
};

const NewsPanel = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('news');
  const [news, setNews] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [diagnosis, setDiagnosis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  // News laden
  const fetchNews = async () => {
    try {
      const response = await fetch(`${API}/api/news/current`);
      const data = await response.json();
      if (data.success) {
        setNews(data.news || []);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('News fetch error:', error);
    }
  };

  // Decisions laden
  const fetchDecisions = async () => {
    try {
      const response = await fetch(`${API}/api/news/decisions`);
      const data = await response.json();
      if (data.success) {
        setDecisions(data.decisions || []);
      }
    } catch (error) {
      console.error('Decisions fetch error:', error);
    }
  };

  // System-Diagnose laden
  const fetchDiagnosis = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/system/diagnosis`);
      const data = await response.json();
      setDiagnosis(data);
    } catch (error) {
      console.error('Diagnosis fetch error:', error);
      setDiagnosis({ overall_status: 'ERROR', error: error.message });
    }
    setLoading(false);
  };

  // Initial laden
  useEffect(() => {
    if (isOpen) {
      fetchNews();
      fetchDecisions();
      fetchDiagnosis();
    }
  }, [isOpen]);

  // Auto-Refresh alle 60 Sekunden
  useEffect(() => {
    if (!isOpen) return;
    
    const interval = setInterval(() => {
      fetchNews();
      fetchDecisions();
    }, 60000);
    
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden bg-slate-900 border-slate-700">
        <CardHeader className="border-b border-slate-700 pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl text-cyan-400 flex items-center gap-2">
              <Activity className="w-6 h-6" />
              News & System-Status
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => { fetchNews(); fetchDecisions(); fetchDiagnosis(); }}
                className="text-cyan-400 border-cyan-400/50"
              >
                <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                Aktualisieren
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </Button>
            </div>
          </div>
          
          {/* Tabs */}
          <div className="flex gap-2 mt-4">
            {['news', 'decisions', 'diagnosis'].map((tab) => (
              <Button
                key={tab}
                variant={activeTab === tab ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActiveTab(tab)}
                className={activeTab === tab ? 'bg-cyan-600' : 'border-slate-600'}
              >
                {tab === 'news' && <Newspaper className="w-4 h-4 mr-1" />}
                {tab === 'decisions' && <AlertTriangle className="w-4 h-4 mr-1" />}
                {tab === 'diagnosis' && <Activity className="w-4 h-4 mr-1" />}
                {tab === 'news' && 'News'}
                {tab === 'decisions' && 'Trade-Entscheidungen'}
                {tab === 'diagnosis' && 'System-Diagnose'}
              </Button>
            ))}
          </div>
        </CardHeader>

        <CardContent className="p-4 overflow-y-auto max-h-[60vh]">
          {/* NEWS TAB */}
          {activeTab === 'news' && (
            <div className="space-y-3">
              {news.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <Newspaper className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Keine aktuellen News</p>
                  <p className="text-sm">News werden automatisch geladen wenn API-Keys konfiguriert sind</p>
                </div>
              ) : (
                news.map((item, index) => (
                  <div 
                    key={item.id || index}
                    className="p-3 bg-slate-800 rounded-lg border border-slate-700"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <DirectionIcon direction={item.direction} />
                          <Badge className={impactColors[item.impact] || 'bg-gray-500'}>
                            {item.impact?.toUpperCase()}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {item.asset_category}
                          </Badge>
                          {item.trade_blocked && (
                            <Badge className="bg-red-600">
                              BLOCKIERT
                            </Badge>
                          )}
                        </div>
                        <h4 className="font-medium text-white">{item.title}</h4>
                        <p className="text-sm text-gray-400 mt-1">{item.summary}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                          <span>{item.source}</span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(item.published_at).toLocaleString('de-DE')}
                          </span>
                          {item.related_assets?.length > 0 && (
                            <span>Assets: {item.related_assets.join(', ')}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
              
              {lastUpdate && (
                <p className="text-xs text-gray-500 text-center mt-4">
                  Letzte Aktualisierung: {lastUpdate.toLocaleTimeString('de-DE')}
                </p>
              )}
            </div>
          )}

          {/* DECISIONS TAB */}
          {activeTab === 'decisions' && (
            <div className="space-y-3">
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 mb-4">
                <h4 className="font-medium text-cyan-400 mb-2">📋 Trade-Entscheidungen</h4>
                <p className="text-sm text-gray-400">
                  Hier sehen Sie warum Trades durch News blockiert oder beeinflusst wurden.
                </p>
              </div>
              
              {decisions.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <CheckCircle className="w-12 h-12 mx-auto mb-2 opacity-50 text-green-400" />
                  <p>Keine blockierten Trades</p>
                  <p className="text-sm">Alle Trades wurden ohne News-Einschränkungen verarbeitet</p>
                </div>
              ) : (
                decisions.slice(0, 50).map((decision, index) => (
                  <div 
                    key={index}
                    className={`p-3 rounded-lg border ${
                      decision.allow_trade 
                        ? 'bg-green-900/20 border-green-700/50' 
                        : 'bg-red-900/20 border-red-700/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {decision.allow_trade ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400" />
                        )}
                        <span className="font-medium text-white">
                          {decision.asset} / {decision.strategy}
                        </span>
                        <Badge variant="outline">
                          {decision.signal}
                        </Badge>
                      </div>
                      <span className="text-xs text-gray-400">
                        {new Date(decision.timestamp).toLocaleTimeString('de-DE')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300">{decision.reason}</p>
                    {decision.confidence_adjustment !== 0 && (
                      <p className="text-xs text-yellow-400 mt-1">
                        Konfidenz-Anpassung: {decision.confidence_adjustment > 0 ? '+' : ''}{(decision.confidence_adjustment * 100).toFixed(0)}%
                      </p>
                    )}
                    {decision.news_count > 0 && (
                      <p className="text-xs text-gray-500 mt-1">
                        {decision.news_count} relevante News
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* DIAGNOSIS TAB */}
          {activeTab === 'diagnosis' && (
            <div className="space-y-4">
              {/* Overall Status */}
              <div className={`p-4 rounded-lg border ${
                diagnosis?.overall_status === 'OK' 
                  ? 'bg-green-900/20 border-green-700' 
                  : diagnosis?.overall_status === 'WARNING'
                  ? 'bg-yellow-900/20 border-yellow-700'
                  : 'bg-red-900/20 border-red-700'
              }`}>
                <div className="flex items-center gap-3">
                  <StatusIcon status={diagnosis?.overall_status} />
                  <div>
                    <h3 className="font-bold text-lg">
                      System-Status: {diagnosis?.overall_status || 'Lädt...'}
                    </h3>
                    <p className="text-sm text-gray-400">
                      {diagnosis?.timestamp && new Date(diagnosis.timestamp).toLocaleString('de-DE')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Components */}
              {diagnosis?.components && (
                <div className="grid gap-3">
                  <h4 className="font-medium text-cyan-400">Komponenten-Status:</h4>
                  
                  {Object.entries(diagnosis.components).map(([name, info]) => (
                    <div 
                      key={name}
                      className="p-3 bg-slate-800 rounded-lg border border-slate-700 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <StatusIcon status={info.status} />
                        <div>
                          <span className="font-medium text-white capitalize">
                            {name.replace(/_/g, ' ')}
                          </span>
                          {info.description && (
                            <p className="text-xs text-gray-400">{info.description}</p>
                          )}
                          {info.test_result && (
                            <p className="text-xs text-cyan-400">{info.test_result}</p>
                          )}
                          {info.active && (
                            <p className="text-xs text-green-400">
                              Aktiv: {info.active.join(', ')}
                            </p>
                          )}
                          {info.connected !== undefined && (
                            <p className="text-xs text-gray-400">
                              Verbunden: {info.connected}
                            </p>
                          )}
                        </div>
                      </div>
                      <Badge className={
                        info.status === 'OK' ? 'bg-green-600' :
                        info.status === 'WARNING' ? 'bg-yellow-600' :
                        info.status === 'DISABLED' ? 'bg-gray-600' :
                        'bg-red-600'
                      }>
                        {info.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}

              {/* Issues */}
              {diagnosis?.issues?.length > 0 && (
                <div className="p-3 bg-red-900/20 rounded-lg border border-red-700">
                  <h4 className="font-medium text-red-400 mb-2">⚠️ Probleme:</h4>
                  <ul className="list-disc list-inside text-sm text-gray-300">
                    {diagnosis.issues.map((issue, i) => (
                      <li key={i}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Legend */}
              <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 mt-4">
                <h4 className="font-medium text-gray-400 mb-2">Legende:</h4>
                <div className="flex flex-wrap gap-3 text-sm">
                  <div className="flex items-center gap-1">
                    <CheckCircle className="w-4 h-4 text-green-400" />
                    <span>OK - Funktioniert</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <AlertCircle className="w-4 h-4 text-yellow-400" />
                    <span>Warnung</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <XCircle className="w-4 h-4 text-red-400" />
                    <span>Fehler</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Minus className="w-4 h-4 text-gray-400" />
                    <span>Deaktiviert</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default NewsPanel;
