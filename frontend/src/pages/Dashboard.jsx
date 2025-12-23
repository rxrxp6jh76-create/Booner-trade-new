import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, BarChart3, Settings, RefreshCw, Play, Pause, Zap, ZapOff, AlertCircle, ChevronLeft, ChevronRight, LineChart, X, Clock } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import PriceChart from '../components/PriceChart';
import TradesTable from '../components/TradesTable';
import IndicatorsPanel from '../components/IndicatorsPanel';
import AIChat from '../components/AIChat';
import SettingsDialog from '../components/SettingsDialog';
import BacktestingPanel from '../components/BacktestingPanel';
import RiskDashboard from '../components/RiskDashboard';
import NewsPanel from '../components/NewsPanel';
import { Newspaper } from 'lucide-react';

// Get backend URL - prioritize Electron API, fallback to env var for web
const getBackendUrl = async () => {
  // V2.3.34 FIX: Ultimativer Fallback für Electron auf Mac
  const ELECTRON_FALLBACK_URL = 'http://localhost:8000';
  
  // Check if running in Electron
  if (window.electronAPI) {
    try {
      // V2.3.34: Prüfen ob getBackendUrl existiert
      if (typeof window.electronAPI.getBackendUrl === 'function') {
        const url = await window.electronAPI.getBackendUrl();
        if (url && url.length > 0) {
          console.log('✅ Backend URL from Electron:', url);
          return url;
        }
      }
      // Fallback wenn getBackendUrl nicht existiert oder leer zurückgibt
      console.log('⚠️ Electron detected, using fallback URL:', ELECTRON_FALLBACK_URL);
      return ELECTRON_FALLBACK_URL;
    } catch (error) {
      console.error('❌ Failed to get backend URL from Electron:', error);
      console.log('⚠️ Using fallback URL:', ELECTRON_FALLBACK_URL);
      return ELECTRON_FALLBACK_URL;
    }
  }
  
  // Fallback to environment variable (for web builds)
  const envUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (envUrl && envUrl.length > 0) {
    console.log('🌐 Backend URL from env:', envUrl);
    return envUrl;
  }
  
  // V2.3.34: Letzter Fallback - localhost:8000
  console.log('⚠️ No backend URL found, using ultimate fallback:', ELECTRON_FALLBACK_URL);
  return ELECTRON_FALLBACK_URL;
};

// These will be set after getting the backend URL
let BACKEND_URL = '';
let API = '';

// Configure axios defaults with timeout
axios.defaults.timeout = 30000; // 30 second timeout for all requests (increased for large trade lists)

// Retry helper for failed requests
const axiosRetry = async (fn, retries = 3, delay = 2000) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      console.log(`⚠️ Retry ${i + 1}/${retries} nach ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
      delay *= 1.5; // Exponential backoff
    }
  }
};

const Dashboard = () => {
  const [backendReady, setBackendReady] = useState(false);
  const [marketData, setMarketData] = useState(null);
  const [allMarkets, setAllMarkets] = useState({});  // All commodity markets
  const [commodities, setCommodities] = useState({}); // Commodity definitions
  const [currentCommodityIndex, setCurrentCommodityIndex] = useState(0); // For carousel
  const [historicalData, setHistoricalData] = useState([]);
  const [selectedCommodity, setSelectedCommodity] = useState(null); // For chart modal
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState(null); // For trade detail modal
  const [tradeDetailModalOpen, setTradeDetailModalOpen] = useState(false);
  const [tradeSettings, setTradeSettings] = useState({});
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [balance, setBalance] = useState(10000); // Deprecated but kept for backwards compatibility
  const [mt5Account, setMt5Account] = useState(null); // Real MT5 account data (ICMarkets)
  const [mt5Connected, setMt5Connected] = useState(false);
  const [mt5LibertexAccount, setMt5LibertexAccount] = useState(null); // Libertex account
  const [mt5LibertexConnected, setMt5LibertexConnected] = useState(false);
  const [bitpandaAccount, setBitpandaAccount] = useState(null); // Bitpanda account
  const [bitpandaConnected, setBitpandaConnected] = useState(false);
  const [totalExposure, setTotalExposure] = useState(0); // Total exposure for all platforms
  const [libertexExposure, setLibertexExposure] = useState(0); // Libertex platform exposure
  const [icmarketsExposure, setIcmarketsExposure] = useState(0); // ICMarkets platform exposure
  const [bitpandaExposure, setBitpandaExposure] = useState(0); // Bitpanda platform exposure
  const [gpt5Active, setGpt5Active] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [newsPanelOpen, setNewsPanelOpen] = useState(false);  // V2.3.35: News Panel
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [aiProcessing, setAiProcessing] = useState(false);
  const [chartTimeframe, setChartTimeframe] = useState('1m'); // Default to 1m for live ticker
  const [chartPeriod, setChartPeriod] = useState('2h'); // Default to 2 hours for live ticker
  const [chartModalData, setChartModalData] = useState([]);
  
  // V2.3.37: MT5 History State mit Filtern
  const [mt5History, setMt5History] = useState([]);
  const [mt5HistoryLoading, setMt5HistoryLoading] = useState(false);
  // V2.3.40: Standard-Filter auf HEUTE setzen
  const [mt5HistoryFilters, setMt5HistoryFilters] = useState({
    startDate: new Date().toISOString().split('T')[0],  // Heute
    endDate: new Date().toISOString().split('T')[0],    // Heute
    commodity: '',
    strategy: '',
    platform: ''
  });
  const [mt5FilterOptions, setMt5FilterOptions] = useState({
    commodities: [],
    strategies: [],
    platforms: []
  });
  const [mt5Statistics, setMt5Statistics] = useState({
    total_profit: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0
  });
  
  // V2.3.40: Signal Status für Ampelsystem
  const [signalsStatus, setSignalsStatus] = useState({});
  const [signalsSummary, setSignalsSummary] = useState({ green: 0, yellow: 0, red: 0, trade_ready: 0 });

  // Initialize backend URL (MUST run first!)
  useEffect(() => {
    const initBackend = async () => {
      try {
        const url = await getBackendUrl();
        BACKEND_URL = url;
        API = `${url}/api`;
        
        console.log('✅ Backend initialized:', { BACKEND_URL, API });
        
        // Test connectivity
        await axiosRetry(() => axios.get(`${API}/ping`), 5, 1000);
        console.log('✅ Backend connection OK');
        
        setBackendReady(true);
      } catch (error) {
        console.error('❌ Backend initialization failed:', error);
        toast.error('Backend nicht erreichbar. Bitte App neu starten.');
      }
    };
    
    initBackend();
    
    // V2.3.35: Bei App-Beendigung Backend killen (für Electron/Desktop)
    const handleBeforeUnload = async (e) => {
      // Nur für Desktop-Apps (Electron) - im Browser nicht ausführen
      if (window.electron || window.process?.type === 'renderer') {
        try {
          // Fire-and-forget Request
          navigator.sendBeacon(`${API}/system/restart-backend`);
          console.log('🔄 Backend-Kill bei App-Beendigung ausgelöst');
        } catch (err) {
          console.warn('Backend-Kill fehlgeschlagen:', err);
        }
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []); // Run once on mount

  useEffect(() => {
    if (!backendReady) return; // Wait for backend to be ready
    
    fetchAllData();
    
    // Live ticker - ECHTZEIT Updates für Trading (alle 5s)
    let updateCounter = 0;
    const liveInterval = setInterval(() => {
      if (autoRefresh) {
        updateCounter++;
        
        // KRITISCHE ECHTZEIT-DATEN: Alle 5s aktualisieren (SCHNELLER!)
        fetchAllMarkets();      // Live Preise
        fetchTrades();          // Aktuelle Trades
        fetchStats();           // Trade Stats
        
        // V2.3.40: Ampelsystem alle 10s aktualisieren (jeder 2. Zyklus)
        if (updateCounter % 2 === 0) {
          fetchSignalsStatus();
        }
        
        // Account-Updates alle 15s (jeder 3. Zyklus bei 5s = 15s)
        if (updateCounter % 3 === 0) {
          refreshMarketData();
          updateBalance();
          
          if (settings?.active_platforms) {
            if (settings.active_platforms.includes('MT5_LIBERTEX')) {
              fetchMT5LibertexAccount();
            }
            if (settings.active_platforms.includes('MT5_ICMARKETS')) {
              fetchMT5ICMarketsAccount();
            }
            if (settings.active_platforms.includes('BITPANDA')) {
              fetchBitpandaAccount();
            }
          }
        }
        
        // Memory Cleanup: Alte Chart-Daten begrenzen (alle 60s = 12x bei 5s)
        if (updateCounter % 12 === 0) {
          setCommodities(prev => {
            // V2.3.32 FIX: commodities ist ein Objekt, nicht ein Array!
            if (!prev || typeof prev !== 'object') {
              return prev || {};
            }
            // Wenn es ein Array ist (für Kompatibilität)
            if (Array.isArray(prev)) {
              return prev.map(c => ({
                ...c,
                price_history: c.price_history?.slice(-100) || []
              }));
            }
            // Es ist ein Objekt - iteriere über die Keys
            const cleaned = {};
            for (const [key, c] of Object.entries(prev)) {
              cleaned[key] = {
                ...c,
                price_history: c.price_history?.slice(-100) || []
              };
            }
            return cleaned;
          });
        }
      }
    }, 5000);  // ECHTZEIT: Alle 5 Sekunden (SCHNELLER!)

    return () => clearInterval(liveInterval);
  }, [autoRefresh, settings?.active_platforms, backendReady]);

  // V2.3.39: MT5 History einmal beim Start laden (für Strategie-Anzeige)
  const [mt5HistoryInitialized, setMt5HistoryInitialized] = useState(false);
  useEffect(() => {
    if (!backendReady || mt5HistoryInitialized) return;
    
    // Verzögere das Laden um sicherzustellen, dass andere Daten zuerst geladen werden
    const timer = setTimeout(() => {
      console.log('🔄 Loading MT5 History for strategy display...');
      fetchMt5History().catch(err => console.error('MT5 History fetch error:', err));
      setMt5HistoryInitialized(true);
    }, 3000);  // 3 Sekunden Verzögerung
    
    return () => clearTimeout(timer);
  }, [backendReady, mt5HistoryInitialized]);

  // Load account data when settings change or component mounts
  useEffect(() => {
    if (!backendReady) return; // Wait for backend
    if (settings?.active_platforms && settings.active_platforms.length > 0) {
      console.log('Loading account data for platforms:', settings.active_platforms);
      
      if (settings.active_platforms.includes('MT5_LIBERTEX')) {
        fetchMT5LibertexAccount();
      }
      if (settings.active_platforms.includes('MT5_ICMARKETS')) {
        fetchMT5ICMarketsAccount();
      }
      if (settings.active_platforms.includes('BITPANDA')) {
        fetchBitpandaAccount();
      }
    }
  }, [settings?.active_platforms, backendReady]);

  // Load OHLCV data for selected commodity in modal with timeframe
  useEffect(() => {
    if (!backendReady) return; // Wait for backend
    if (chartModalOpen && selectedCommodity) {
      const loadChartData = async () => {
        try {
          // V2.3.35: Auto-adjust period based on timeframe for valid combinations
          let adjustedPeriod = chartPeriod;
          
          // Fix invalid timeframe/period combinations
          if (chartTimeframe === '1d' || chartTimeframe === '1wk' || chartTimeframe === '1mo') {
            // Daily/Weekly/Monthly candles need longer periods
            if (chartPeriod === '2h' || chartPeriod === '1d') {
              adjustedPeriod = '1mo';  // Minimum 1 month for daily candles
            } else if (chartPeriod === '5d' || chartPeriod === '1wk') {
              adjustedPeriod = '3mo';  // 3 months for weekly context
            }
          } else if (chartTimeframe === '4h' || chartTimeframe === '2h') {
            // 2h/4h candles need at least 1 week
            if (chartPeriod === '2h') {
              adjustedPeriod = '1wk';
            }
          }
          
          console.log('Loading chart data for:', selectedCommodity.id, chartTimeframe, adjustedPeriod);
          
          // Try normal endpoint first
          try {
            const response = await axios.get(
              `${API}/market/ohlcv/${selectedCommodity.id}?timeframe=${chartTimeframe}&period=${adjustedPeriod}`
            );
            console.log('Chart data received:', response.data);
            if (response.data.success && response.data.data && response.data.data.length > 0) {
              setChartModalData(response.data.data || []);
              return;
            }
          } catch (err) {
            console.warn('Primary chart endpoint failed, trying fallback...');
          }
          
          // Fallback to simple endpoint (uses live DB data)
          const fallbackResponse = await axios.get(
            `${API}/market/ohlcv-simple/${selectedCommodity.id}?timeframe=${chartTimeframe}&period=${adjustedPeriod}`
          );
          console.log('Fallback chart data received:', fallbackResponse.data);
          if (fallbackResponse.data.success) {
            setChartModalData(fallbackResponse.data.data || []);
          }
        } catch (error) {
          console.error('Error loading chart data:', error);
          setChartModalData([]); // Clear on error
        }
      };
      loadChartData();
    } else {
      // Clear chart data when modal closes
      setChartModalData([]);
    }
  }, [chartModalOpen, selectedCommodity, chartTimeframe, chartPeriod, backendReady]);

  const fetchAllData = async () => {
    setLoading(true);
    
    // Set a maximum timeout for loading - force stop after 20 seconds (increased for slow connections)
    const maxLoadingTimeout = setTimeout(() => {
      console.warn('Loading timeout reached, forcing UI to display');
      setLoading(false);
    }, 20000);
    
    try {
      // Fetch data sequentially to avoid overloading backend
      // 1. Settings first (needed for other calls)
      await fetchSettings().catch(err => console.error('Settings fetch error:', err));
      
      // 2. Critical data (balance, trades)
      await fetchAccountData().catch(err => console.error('Account data fetch error:', err));
      await fetchTrades().catch(err => console.error('Trades fetch error:', err));
      
      // 3. Market data (can be slower)
      await fetchCommodities().catch(err => console.error('Commodities fetch error:', err));
      await fetchAllMarkets().catch(err => console.error('Markets fetch error:', err));
      
      // 4. Non-critical data (stats, historical) - can run in parallel
      await Promise.all([
        refreshMarketData().catch(err => console.error('Market refresh error:', err)),
        fetchHistoricalData().catch(err => console.error('Historical data fetch error:', err)),
        fetchStats().catch(err => console.error('Stats fetch error:', err)),
        fetchSignalsStatus().catch(err => console.error('Signals status fetch error:', err))
      ]);
      
    } catch (error) {
      console.error('Error in fetchAllData:', error);
    } finally {
      // Clear the timeout and stop loading
      clearTimeout(maxLoadingTimeout);
      setLoading(false);
    }
  };

  const fetchAccountData = async () => {
    // Fetch account data for all active platforms
    try {
      if (settings?.active_platforms && settings.active_platforms.length > 0) {
        const promises = [];
        // Check for any Libertex account (MT5_LIBERTEX, MT5_LIBERTEX_DEMO, MT5_LIBERTEX_REAL)
        const hasLibertex = settings.active_platforms.some(p => p.includes('LIBERTEX'));
        if (hasLibertex) {
          promises.push(fetchMT5LibertexAccount().catch(err => console.error('MT5 Libertex error:', err)));
        }
        // Check for any ICMarkets account (MT5_ICMARKETS, MT5_ICMARKETS_DEMO)
        const hasICMarkets = settings.active_platforms.some(p => p.includes('ICMARKETS'));
        if (hasICMarkets) {
          promises.push(fetchMT5ICMarketsAccount().catch(err => console.error('MT5 ICMarkets error:', err)));
        }
        if (settings.active_platforms.includes('BITPANDA')) {
          promises.push(fetchBitpandaAccount().catch(err => console.error('Bitpanda error:', err)));
        }
        await Promise.all(promises);
      }
    } catch (error) {
      console.error('Error fetching account data:', error);
    }
  };


  const fetchCommodities = async () => {
    try {
      const response = await axios.get(`${API}/commodities`);
      setCommodities(response.data.commodities || {});
    } catch (error) {
      console.error('Error fetching commodities:', error);
    }
  };

  const fetchAllMarkets = async () => {
    try {
      const response = await axios.get(`${API}/market/all`);
      setAllMarkets(response.data.markets || {});
    } catch (error) {
      console.error('Error fetching all markets:', error);
    }
  };

  // V2.3.40: Fetch Signal Status für Ampelsystem
  const fetchSignalsStatus = async () => {
    try {
      const response = await axios.get(`${API}/signals/status`);
      if (response.data.success) {
        setSignalsStatus(response.data.signals || {});
        setSignalsSummary(response.data.summary || { green: 0, yellow: 0, red: 0, trade_ready: 0 });
      }
    } catch (error) {
      console.error('Error fetching signals status:', error);
    }
  };

  // NEW: Fetch LIVE tick prices from MetaAPI
  const fetchLiveTicks = async () => {
    try {
      const response = await axios.get(`${API}/market/live-ticks`);
      const livePrices = response.data.live_prices || {};
      
      // Update allMarkets with live prices
      setAllMarkets(prev => {
        const updated = { ...prev };
        Object.keys(livePrices).forEach(commodityId => {
          const tick = livePrices[commodityId];
          if (updated[commodityId]) {
            // Update existing market data with live price
            updated[commodityId] = {
              ...updated[commodityId],
              price: tick.price,
              timestamp: tick.time,
              bid: tick.bid,
              ask: tick.ask,
              source: 'LIVE'
            };
          } else {
            // Create new entry if doesn't exist
            updated[commodityId] = {
              commodity: commodityId,
              price: tick.price,
              timestamp: tick.time,
              bid: tick.bid,
              ask: tick.ask,
              source: 'LIVE'
            };
          }
        });
        return updated;
      });
      
      console.log(`✅ Live ticks updated: ${Object.keys(livePrices).length} commodities`);
    } catch (error) {
      console.error('Error fetching live ticks:', error);
    }
  };

  // Live price updates every 5 seconds - placed AFTER fetchLiveTicks definition
  useEffect(() => {
    if (!backendReady) return; // Wait for backend
    
    // Initial fetch
    fetchLiveTicks();
    
    // Set up interval for live updates
    const liveUpdateInterval = setInterval(() => {
      fetchLiveTicks();
    }, 5000); // Update every 5 seconds
    
    // Cleanup on unmount
    return () => clearInterval(liveUpdateInterval);
  }, [backendReady]);


  
  const calculateTotalExposure = () => {
    // Calculate actual exposure from open trades
    const openTrades = trades.filter(t => t.status === 'OPEN');
    const exposure = openTrades.reduce((sum, trade) => {
      return sum + (trade.entry_price * trade.quantity);
    }, 0);
    setTotalExposure(exposure);
  };

  const fetchMarketData = async () => {
    try {
      const response = await axios.get(`${API}/market/current`);
      setMarketData(response.data);
    } catch (error) {
      console.error('Error fetching market data:', error);
    }
  };

  const refreshMarketData = async () => {
    try {
      setAiProcessing(true);
      // Call refresh endpoint to fetch new data from Yahoo Finance
      await axios.post(`${API}/market/refresh`);
      // Then get the updated data
      const response = await axios.get(`${API}/market/current`);
      setMarketData(response.data);
      // Also refresh historical data
      await fetchHistoricalData();
    } catch (error) {
      console.error('Error refreshing market data:', error);
    } finally {
      setAiProcessing(false);
    }
  };

  const fetchHistoricalData = async () => {
    try {
      const response = await axios.get(`${API}/market/history?limit=50`);
      setHistoricalData(response.data.data || []);
    } catch (error) {
      console.error('Error fetching historical data:', error);
    }
  };

  const fetchTrades = async (includeAll = false) => {
    try {
      // V2.3.34 FIX: Immer ALLE Trades laden (Open + Closed)
      // Das Tab-basierte Laden hat auf manchen Systemen nicht funktioniert
      const endpoint = `${API}/trades/list`;
      const response = await axios.get(endpoint);
      const allTrades = response.data.trades || [];
      
      console.log(`✅ Fetched ${allTrades.length} trades from unified endpoint`);
      if (allTrades.length > 0) {
        console.log('🔍 DEBUG - First trade data:', JSON.stringify(allTrades[0], null, 2));
      }
      
      // ALTE LOGIK ENTFERNT - würde Duplikate erzeugen!
      // Die separaten MT5 Position Calls sind nicht mehr nötig,
      // da /trades/list bereits live MT5-Daten enthält
      
      /* ENTFERNT - verursachte Duplikate:
      if (settings?.active_platforms?.includes('MT5_LIBERTEX')) {
        try {
          const libertexRes = await axios.get(`${API}/platforms/MT5_LIBERTEX/positions`);
          // ... würde die gleichen Positionen nochmal hinzufügen!
      */
      
      // Setze die Trades (bereits komplett vom unified endpoint)
      setTrades(allTrades);
      
      // Calculate exposure PER PLATFORM after loading trades
      const openTrades = allTrades.filter(t => t.status === 'OPEN');
      
      // Total exposure (all platforms) - V2.3.32 FIX: Schutz vor undefined
      const totalExp = openTrades.reduce((sum, trade) => {
        const price = trade.entry_price || trade.price || 0;
        const qty = trade.quantity || trade.volume || 0;
        return sum + (price * qty);
      }, 0);
      setTotalExposure(totalExp);
      
      // V2.3.32 FIX: Sichere Berechnung mit Fallbacks für undefined
      const calcExposure = (trade) => {
        const price = trade.entry_price || trade.price || 0;
        const qty = trade.quantity || trade.volume || 0;
        return price * qty;
      };
      
      // Libertex exposure (includes all Libertex accounts: MT5_LIBERTEX, MT5_LIBERTEX_DEMO, MT5_LIBERTEX_REAL)
      const libertexExp = openTrades
        .filter(t => (t.platform && t.platform.includes('LIBERTEX')) || (t.mode && t.mode.includes('LIBERTEX')))
        .reduce((sum, trade) => sum + calcExposure(trade), 0);
      setLibertexExposure(libertexExp);
      
      // ICMarkets exposure (includes all ICMarkets accounts: MT5_ICMARKETS, MT5_ICMARKETS_DEMO)
      const icExp = openTrades
        .filter(t => (t.platform && t.platform.includes('ICMARKETS')) || (t.mode && t.mode.includes('ICMARKETS')))
        .reduce((sum, trade) => sum + calcExposure(trade), 0);
      setIcmarketsExposure(icExp);
      
      // Bitpanda exposure
      const bitpandaExp = openTrades
        .filter(t => t.platform === 'BITPANDA' || t.mode === 'BITPANDA')
        .reduce((sum, trade) => sum + calcExposure(trade), 0);
      setBitpandaExposure(bitpandaExp);
    } catch (error) {
      console.error('Error fetching trades:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/trades/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // V2.3.32: Separate Funktion für geschlossene Trades (nur bei Tab-Wechsel)
  const fetchAllTrades = async () => {
    try {
      const response = await axios.get(`${API}/trades/list`);
      const allTrades = response.data.trades || [];
      setTrades(allTrades);
      console.log(`✅ Fetched ALL ${allTrades.length} trades (OPEN + CLOSED)`);
    } catch (error) {
      console.error('Error fetching all trades:', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings`);
      setSettings(response.data);
      setGpt5Active(response.data.use_gpt5 && response.data.auto_trading);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const updateBalance = () => {
    // Use real MT5 balance if connected and mode is MT5, otherwise calculate from paper trading
    if (mt5Connected && mt5Account && settings?.mode === 'MT5') {
      setBalance(mt5Account.balance);
    } else if (settings?.mode === 'PAPER') {
      // Calculate balance based on trades P/L for paper trading
      if (stats) {
        const newBalance = 10000 + (stats.total_profit_loss || 0);
        setBalance(newBalance);
      }
    }
  };

  const fetchMT5Account = async () => {
    try {
      const response = await axios.get(`${API}/mt5/account`);
      setMt5Account(response.data);
      setMt5Connected(true);
      // Always update balance immediately when MT5 data is fetched
      setBalance(response.data.balance);
    } catch (error) {
      console.error('Error fetching MT5 account:', error);
      setMt5Connected(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await axios.post(`${API}/market/refresh`);
      await fetchAllData();
      toast.success('Marktdaten aktualisiert');
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
    setRefreshing(false);
  };

  const handleManualTrade = async (type, commodityId = 'WTI_CRUDE') => {
    const market = commodityId ? allMarkets[commodityId] : marketData;
    if (!market) {
      toast.error('Marktdaten nicht verfügbar');
      return;
    }
    
    try {
      console.log('Executing trade:', { trade_type: type, price: market.price, commodity: commodityId });
      
      // Erhöhtes Timeout für SDK-Verbindung (45 Sekunden)
      const response = await axios.post(`${API}/trades/execute`, {
        trade_type: type,
        price: market.price,
        quantity: null,  // Auto-berechnet
        commodity: commodityId
      }, {
        timeout: 45000  // 45 Sekunden Timeout für Trade-Execution
      });
      
      console.log('Trade response:', response.data);
      
      if (response.data.success) {
        const ticket = response.data.ticket;
        toast.success(`✅ ${type} Order für ${commodities[commodityId]?.name || commodityId} ausgeführt! Ticket: #${ticket}`);
        fetchTrades();
        fetchStats();
        fetchAllMarkets();
        fetchAccountData();
      } else {
        throw new Error('Trade nicht erfolgreich');
      }
    } catch (error) {
      console.error('Trade execution error:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unbekannter Fehler';
      toast.error('Fehler beim Ausführen: ' + errorMsg);
    }
  };



  // Trade Detail Modal Handlers
  const handleTradeClick = async (trade) => {
    console.log('🔍 Trade clicked:', trade);
    console.log('🔍 Trade TP/SL values:', { 
      take_profit: trade.take_profit, 
      stop_loss: trade.stop_loss,
      tp_type: typeof trade.take_profit,
      sl_type: typeof trade.stop_loss
    });
    
    try {
      // CRITICAL FIX for Safari: Set state synchronously FIRST
      setSelectedTrade(trade);
      setTradeDetailModalOpen(true); // Open modal immediately
      console.log('✅ Modal opened');
      
      // THEN load additional settings asynchronously
      const ticket = trade.mt5_ticket || trade.id;
      console.log('📋 Loading settings for ticket:', ticket);
      
      try {
        const response = await axios.get(`${API}/trades/${ticket}/settings`);
        console.log('✅ Settings loaded:', response.data);
        setTradeSettings({
          stop_loss: trade.stop_loss || response.data?.stop_loss || null,
          take_profit: trade.take_profit || response.data?.take_profit || null,
          trailing_stop: response.data?.trailing_stop || false,
          // Backend kann 'strategy' oder 'strategy_type' zurückgeben
          strategy_type: response.data?.strategy || response.data?.strategy_type || 'swing'
        });
      } catch (error) {
        console.log('⚠️ No settings found, using trade defaults');
        // Use values from trade object directly
        setTradeSettings({
          stop_loss: trade.stop_loss || null,
          take_profit: trade.take_profit || null,
          trailing_stop: false,
          strategy_type: 'swing'
        });
      }
    } catch (error) {
      console.error('❌ Error loading trade details:', error);
      toast.error('Fehler beim Laden der Trade-Details');
    }
  };

  const handleSaveTradeSettings = async () => {
    try {
      const ticket = selectedTrade.mt5_ticket || selectedTrade.ticket || selectedTrade.id;
      // WICHTIG: API erwartet trade_id im Format "mt5_{ticket}"
      const tradeId = ticket.toString().startsWith('mt5_') ? ticket : `mt5_${ticket}`;
      
      // 🐛 FIX: Konvertiere strategy_type zu strategy für Backend-Kompatibilität
      const settingsToSend = {
        ...tradeSettings,
        strategy: tradeSettings.strategy_type || tradeSettings.strategy || 'swing'
      };
      
      console.log('💾 Saving trade settings:', settingsToSend);
      
      await axios.post(`${API}/trades/${tradeId}/settings`, settingsToSend);
      
      toast.success('✅ Trade-Einstellungen gespeichert. KI überwacht jetzt diese Werte.');
      setTradeDetailModalOpen(false);
      
      // Reload trades um aktualisierte Daten zu sehen
      await fetchTrades();
    } catch (error) {
      console.error('Error saving trade settings:', error);
      toast.error('❌ Fehler beim Speichern der Einstellungen: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleCloseTrade = async (trade) => {
    try {
      console.log('Closing trade:', trade);
      
      // Prepare request body - include trade data for DB storage
      const requestBody = {
        trade_id: trade.id,
        ticket: trade.mt5_ticket || trade.ticket,
        platform: trade.platform,
        // Include trade data as fallback for DB storage
        trade_data: {
          commodity: trade.commodity,
          type: trade.type,
          entry_price: trade.entry_price,
          current_price: trade.price,
          quantity: trade.quantity,
          profit_loss: trade.profit_loss,
          opened_at: trade.timestamp || trade.opened_at
        }
      };
      
      console.log('Request body:', requestBody);
      
      // Use new unified endpoint (API already includes /api prefix)
      const response = await axios.post(`${API}/trades/close`, requestBody, {
        timeout: 45000  // 45 Sekunden Timeout für Trade-Close
      });
      
      console.log('Close response:', response.data);
      
      if (response.data.success) {
        toast.success('✅ Position geschlossen!');
        fetchTrades();
        fetchStats();
        fetchAccountData();
      } else {
        throw new Error(response.data.message || 'Trade konnte nicht geschlossen werden');
      }
    } catch (error) {
      console.error('Close trade error:', error);
      console.error('Error response:', error.response);
      
      let errorMsg = 'Unbekannter Fehler';
      
      if (error.response?.data) {
        // Backend error
        errorMsg = error.response.data.detail || error.response.data.message || JSON.stringify(error.response.data);
      } else if (error.message) {
        // JavaScript error
        errorMsg = error.message;
      }
      
      toast.error('Fehler beim Schließen: ' + errorMsg);
    }
  };

  const handleDeleteTrade = async (tradeId, tradeName) => {
    try {
      const response = await axios.delete(`${API}/trades/${tradeId}`);
      if (response.data.success) {
        toast.success(`✅ Trade "${tradeName}" gelöscht!`);
        fetchTrades();
        fetchStats();
      }
    } catch (error) {
      console.error('Error deleting trade:', error);
      toast.error(`❌ Fehler: ${error.response?.data?.detail || error.message}`);
    }
  };

  // V2.3.37: Fetch MT5 History mit Filtern
  const fetchMt5History = async (filters = mt5HistoryFilters) => {
    try {
      setMt5HistoryLoading(true);
      
      const params = new URLSearchParams();
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.commodity) params.append('commodity', filters.commodity);
      if (filters.strategy) params.append('strategy', filters.strategy);
      if (filters.platform) params.append('platform', filters.platform);
      
      const response = await axios.get(`${API}/trades/mt5-history?${params.toString()}`);
      
      if (response.data.success) {
        const trades = response.data.trades || [];
        console.log('📊 MT5 History received:', trades.length, 'trades');
        console.log('📊 First trade strategy:', trades[0]?.strategy);
        console.log('📊 Sample trades:', trades.slice(0, 3).map(t => ({ ticket: t.positionId, strategy: t.strategy })));
        setMt5History(trades);
        setMt5FilterOptions(response.data.filters || { commodities: [], strategies: [], platforms: [] });
        setMt5Statistics(response.data.statistics || { total_profit: 0, winning_trades: 0, losing_trades: 0, win_rate: 0 });
        console.log(`✅ MT5 History loaded: ${response.data.count} trades`);
      }
    } catch (error) {
      console.error('Error fetching MT5 history:', error);
      toast.error('Fehler beim Laden der MT5-History');
    } finally {
      setMt5HistoryLoading(false);
    }
  };

  // Carousel navigation - V2.3.32 FIX: Schutz vor Division durch 0
  const enabledCommodities = Object.keys(allMarkets);
  const currentCommodityId = enabledCommodities[currentCommodityIndex] || null;
  const currentMarket = currentCommodityId ? allMarkets[currentCommodityId] : null;
  
  const nextCommodity = () => {
    if (enabledCommodities.length === 0) return; // Schutz vor Division durch 0
    setCurrentCommodityIndex((prev) => (prev + 1) % enabledCommodities.length);
  };
  
  const prevCommodity = () => {
    if (enabledCommodities.length === 0) return; // Schutz vor Division durch 0
    setCurrentCommodityIndex((prev) => (prev - 1 + enabledCommodities.length) % enabledCommodities.length);
  };

  // handleCloseTrade is defined above with MT5 support

  const handleUpdateSettings = async (newSettings) => {
    try {
      // V2.3.34 FIX: Sicherstellen dass API URL korrekt initialisiert ist
      // Dies behebt Race Conditions auf dem Mac/Electron
      let apiUrl = API;
      if (!apiUrl || apiUrl === '' || apiUrl === '/api') {
        console.warn('⚠️ API URL nicht initialisiert, hole neu...');
        const backendUrl = await getBackendUrl();
        apiUrl = `${backendUrl}/api`;
        // Update global variables
        BACKEND_URL = backendUrl;
        API = apiUrl;
        console.log('✅ API URL neu gesetzt:', apiUrl);
      }
      
      console.log('💾 Speichere Einstellungen...');
      console.log('  API URL:', `${apiUrl}/settings`);
      console.log('  Settings:', newSettings);
      
      const response = await axios.post(`${apiUrl}/settings`, newSettings, {
        timeout: 60000, // v2.3.33: 60 Sekunden Timeout für Settings (Trade-Updates können dauern)
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log('✅ Einstellungen gespeichert:', response.data);
      console.log('📋 active_platforms in response:', response.data.active_platforms);
      console.log('📋 ALL keys in response:', Object.keys(response.data));
      setSettings(response.data); // Use server response
      setGpt5Active(response.data.use_ai_analysis && response.data.auto_trading);
      toast.success('✅ Einstellungen gespeichert');
      setSettingsOpen(false);
      
      // V2.3.34: Sync Trade-Settings nach Settings-Änderung!
      console.log('🔄 Sync Trade-Settings...');
      toast.info('🔄 Trades werden aktualisiert...');
      try {
        await axios.post(`${apiUrl}/trades/sync-settings`);
        console.log('✅ Trade-Settings synchronisiert');
      } catch (syncError) {
        console.warn('⚠️ Sync fehlgeschlagen:', syncError);
      }
      
      // Reload Trades um neue SL/TP anzuzeigen
      await fetchTrades();
      console.log('✅ Trades aktualisiert');
      
      // Reload balance based on active platforms
      if (response.data.active_platforms?.includes('MT5_LIBERTEX')) {
        await fetchMT5LibertexAccount();
      }
      if (response.data.active_platforms?.includes('MT5_ICMARKETS')) {
        await fetchMT5ICMarketsAccount();
      }
      if (response.data.active_platforms?.includes('BITPANDA')) {
        await fetchBitpandaAccount();
      }
    } catch (error) {
      console.error('❌ Settings save error:', error);
      console.error('   Error type:', error.code);
      console.error('   Error message:', error.message);
      console.error('   Response:', error.response?.data);
      
      let errorMsg = 'Fehler beim Speichern';
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorMsg = '⏱️ Timeout: Backend antwortet nicht. Bitte prüfen Sie die Verbindung.';
      } else if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
        errorMsg = '🌐 Netzwerkfehler: Keine Verbindung zum Backend möglich.';
      } else if (error.response) {
        // V2.3.32 FIX: Bessere Fehlerbehandlung - kein [object Object]
        const detail = error.response.data?.detail;
        const message = error.response.data?.message;
        const statusText = error.response.statusText;
        
        if (typeof detail === 'string') {
          errorMsg = `❌ Server Fehler: ${detail}`;
        } else if (typeof message === 'string') {
          errorMsg = `❌ Server Fehler: ${message}`;
        } else if (typeof statusText === 'string') {
          errorMsg = `❌ Server Fehler: ${statusText}`;
        } else if (error.response.data) {
          errorMsg = `❌ Server Fehler: ${JSON.stringify(error.response.data)}`;
        } else {
          errorMsg = `❌ Server Fehler: HTTP ${error.response.status}`;
        }
      } else {
        errorMsg = `❌ ${error.message}`;
      }
      
      toast.error(errorMsg);
    }
  };
  
  // Fetch MT5 Libertex Account
  const fetchMT5LibertexAccount = async () => {
    try {
      // Find the first active Libertex platform (could be MT5_LIBERTEX, MT5_LIBERTEX_DEMO, or MT5_LIBERTEX_REAL)
      const libertexPlatform = settings?.active_platforms?.find(p => p.includes('LIBERTEX'));
      if (!libertexPlatform) {
        console.warn('No Libertex platform found in active platforms');
        return;
      }
      
      const response = await axios.get(`${API}/platforms/${libertexPlatform}/account`);
      if (response.data.success) {
        setMt5LibertexAccount(response.data.account);
        setMt5LibertexConnected(true);
      }
    } catch (error) {
      console.error('Error fetching MT5 Libertex account:', error);
      setMt5LibertexConnected(false);
    }
  };

  // Fetch MT5 ICMarkets Account  
  const fetchMT5ICMarketsAccount = async () => {
    try {
      // Find the first active ICMarkets platform (could be MT5_ICMARKETS or MT5_ICMARKETS_DEMO)
      const icmarketsPlatform = settings?.active_platforms?.find(p => p.includes('ICMARKETS'));
      if (!icmarketsPlatform) {
        console.warn('No ICMarkets platform found in active platforms');
        return;
      }
      
      const response = await axios.get(`${API}/platforms/${icmarketsPlatform}/account`);
      if (response.data.success) {
        setMt5Account(response.data.account);
        setMt5Connected(true);
      }
    } catch (error) {
      console.error('Error fetching MT5 ICMarkets account:', error);
      setMt5Connected(false);
    }
  };
  
  const fetchBitpandaAccount = async () => {
    try {
      const response = await axios.get(`${API}/platforms/BITPANDA/account`);
      if (response.data.success) {
        setBitpandaAccount(response.data.account);
        setBitpandaConnected(true);
      }
    } catch (error) {
      console.error('Error fetching Bitpanda account:', error);
      setBitpandaConnected(false);
    }
  };

  const getSignalColor = (signal) => {
    if (signal === 'BUY') return 'text-emerald-400';
    if (signal === 'SELL') return 'text-rose-400';
    return 'text-slate-400';
  };

  const getSignalIcon = (signal) => {
    if (signal === 'BUY') return <TrendingUp className="w-5 h-5" />;
    if (signal === 'SELL') return <TrendingDown className="w-5 h-5" />;
    return <Minus className="w-5 h-5" />;
  };

  // V2.3.40: Ampelsystem für Signal-Status
  const getTrafficLight = (commodityId) => {
    const status = signalsStatus[commodityId];
    if (!status) {
      return { color: 'gray', label: '?', confidence: 0, reason: 'Lade...' };
    }
    
    const colorMap = {
      green: { bg: 'bg-emerald-500', border: 'border-emerald-400', glow: 'shadow-emerald-500/50' },
      yellow: { bg: 'bg-yellow-500', border: 'border-yellow-400', glow: 'shadow-yellow-500/50' },
      red: { bg: 'bg-red-500', border: 'border-red-400', glow: 'shadow-red-500/50' }
    };
    
    const colors = colorMap[status.status] || colorMap.red;
    
    return {
      color: status.status,
      colors: colors,
      confidence: status.confidence || 0,
      threshold: status.threshold || 65,
      reason: status.reason || 'Keine Daten',
      activeSignals: status.active_signals_count || 0
    };
  };

  // Removed loading screen - show UI immediately with skeleton states
  // if (loading) {
  //   return (
  //     <div className="flex items-center justify-center min-h-screen">
  //       <div className="text-center">
  //         <RefreshCw className="w-12 h-12 animate-spin mx-auto mb-4 text-cyan-400" />
  //         <p className="text-lg">Lade Marktdaten...</p>
  //       </div>
  //     </div>
  //   );
  // }

  return (
    <div className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="max-w-[1800px] mx-auto mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold" style={{ color: '#2dd4bf' }} data-testid="dashboard-title">
                Booner Trade
              </h1>
              {gpt5Active && (
                <Badge className="bg-gradient-to-r from-purple-600 to-pink-600 text-white flex items-center gap-1 px-3 py-1 animate-pulse" data-testid="gpt5-active-badge">
                  <Zap className="w-4 h-4" />
                  KI AKTIV
                </Badge>
              )}
              {!gpt5Active && settings?.auto_trading && (
                <Badge className="bg-slate-700 text-slate-400 flex items-center gap-1 px-3 py-1">
                  <ZapOff className="w-4 h-4" />
                  KI Inaktiv
                </Badge>
              )}
            </div>
            <p className="text-base md:text-lg text-slate-400">Multi-Commodity Trading mit KI-Analyse</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Label className="text-sm text-slate-400">Live-Ticker</Label>
              <Switch
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              variant="outline"
              className="border-cyan-500/30 hover:bg-cyan-500/10 hover:border-cyan-400"
              data-testid="refresh-button"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Aktualisieren
            </Button>
            <Button 
              variant="outline" 
              className="border-slate-600 hover:bg-slate-700" 
              data-testid="settings-button"
              onClick={() => setSettingsOpen(true)}
            >
              <Settings className="w-4 h-4 mr-2" />
              Einstellungen
            </Button>
            
            <SettingsDialog 
              open={settingsOpen} 
              onOpenChange={setSettingsOpen} 
              settings={settings} 
              onSave={handleUpdateSettings} 
            />
            
            {/* V2.3.35: News & System-Diagnose Button */}
            <Button 
              variant="outline" 
              className="border-cyan-600 hover:bg-cyan-700/20 text-cyan-400" 
              data-testid="news-button"
              onClick={() => setNewsPanelOpen(true)}
            >
              <Newspaper className="w-4 h-4 mr-2" />
              News & Status
            </Button>
            
            {/* V2.3.35: Backend Restart Button */}
            <Button 
              variant="outline" 
              className="border-red-600 hover:bg-red-700/20 text-red-400" 
              data-testid="restart-backend-button"
              onClick={async () => {
                if (!window.confirm('Backend neu starten? Die App wird kurz nicht reagieren.')) return;
                try {
                  toast.info('🔄 Backend wird neu gestartet...');
                  await axios.post(`${API}/system/restart-backend`);
                  toast.success('✅ Backend-Neustart eingeleitet. Seite wird in 5 Sekunden neu geladen...');
                  setTimeout(() => {
                    window.location.reload();
                  }, 5000);
                } catch (error) {
                  console.error('Restart error:', error);
                  toast.error('❌ Fehler beim Neustart: ' + (error.response?.data?.detail || error.message));
                }
              }}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Neustart
            </Button>
            
            {/* V2.3.35: News Panel Modal */}
            <NewsPanel 
              isOpen={newsPanelOpen} 
              onClose={() => setNewsPanelOpen(false)} 
            />
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto">
        {/* AI Status Indicator */}
        {settings?.use_ai_analysis && (
          <Card className={`p-4 mb-6 border-2 transition-all duration-300 ${
            aiProcessing 
              ? 'bg-gradient-to-r from-purple-900/40 to-pink-900/40 border-purple-500/50 animate-pulse' 
              : 'bg-slate-900/60 border-slate-700/30'
          }`} data-testid="ai-status-indicator">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`relative flex h-3 w-3 ${aiProcessing ? '' : 'opacity-40'}`}>
                  {aiProcessing && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                  )}
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${
                    aiProcessing ? 'bg-purple-500' : 'bg-slate-500'
                  }`}></span>
                </div>
                <div>
                  <p className="text-sm font-semibold flex items-center gap-2">
                    <Zap className={`w-4 h-4 ${aiProcessing ? 'text-purple-400' : 'text-slate-500'}`} />
                    KI-Analyse Status
                  </p>
                  <p className="text-xs text-slate-400">
                    {aiProcessing ? (
                      <span className="text-purple-300">🤖 KI analysiert Marktdaten...</span>
                    ) : (
                      <span>Bereit für Analyse | Provider: {settings?.ai_provider || 'emergent'}</span>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <Badge variant="outline" className={`${
                  aiProcessing 
                    ? 'border-purple-500/50 text-purple-300 bg-purple-900/30' 
                    : 'border-slate-600 text-slate-400'
                }`}>
                  {aiProcessing ? 'AKTIV' : 'BEREIT'}
                </Badge>
                {settings?.ai_provider === 'ollama' && (
                  <p className="text-xs text-slate-500 mt-1">🏠 Lokal auf Ihrem Mac</p>
                )}
                {/* V2.3.40: Signal-Zusammenfassung (Ampelsystem) */}
                <div className="flex items-center justify-end gap-2 mt-2">
                  <div className="flex items-center gap-1" title="Trade-bereit">
                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    <span className="text-xs text-emerald-400">{signalsSummary.green}</span>
                  </div>
                  <div className="flex items-center gap-1" title="Signal erkannt">
                    <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                    <span className="text-xs text-yellow-400">{signalsSummary.yellow}</span>
                  </div>
                  <div className="flex items-center gap-1" title="Keine Signale">
                    <div className="w-2 h-2 rounded-full bg-red-500"></div>
                    <span className="text-xs text-red-400">{signalsSummary.red}</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Platform Balance Cards - 3 Platforms */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* MT5 Libertex Balance Card */}
          <Card className="bg-gradient-to-br from-blue-900/20 to-slate-900/90 border-blue-700/50 backdrop-blur-sm p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings?.active_platforms?.includes('MT5_LIBERTEX') || false}
                  onChange={async (e) => {
                    if (!settings) {
                      toast.error('Settings noch nicht geladen');
                      return;
                    }
                    const newPlatforms = e.target.checked
                      ? [...(settings.active_platforms || []), 'MT5_LIBERTEX']
                      : (settings.active_platforms || []).filter(p => p !== 'MT5_LIBERTEX');
                    await handleUpdateSettings({ ...settings, active_platforms: newPlatforms });
                  }}
                  className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                  disabled={!settings}
                />
                <h3 className="text-sm font-bold text-blue-400">🔷 MT5 Libertex</h3>
                {mt5LibertexConnected && settings?.active_platforms?.includes('MT5_LIBERTEX') && (
                  <Badge className="bg-emerald-600 text-white text-xs">Aktiv</Badge>
                )}
              </div>
              <DollarSign className="w-8 h-8 text-blue-400/20" />
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-slate-400">Balance</p>
                <p className="text-xl font-bold text-white">
                  {mt5LibertexConnected ? `€${mt5LibertexAccount?.balance?.toFixed(2) || '0.00'}` : '€0.00'}
                </p>
              </div>
              {mt5LibertexConnected && (
                <>
                  <div className="text-xs text-slate-400">
                    Equity: €{mt5LibertexAccount?.equity?.toFixed(2)} | Freie Margin: €{mt5LibertexAccount?.free_margin?.toFixed(2)}
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Portfolio-Risiko:</span>
                      <span className={
                        (mt5LibertexAccount?.portfolio_risk_percent || 0) > (settings?.max_portfolio_risk_percent || 20)
                          ? 'text-red-400 font-semibold'
                          : 'text-green-400'
                      }>
                        {(mt5LibertexAccount?.portfolio_risk_percent || 0).toFixed(1)}% / {settings?.max_portfolio_risk_percent || 20}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          (mt5LibertexAccount?.portfolio_risk_percent || 0) > (settings?.max_portfolio_risk_percent || 20)
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(((mt5LibertexAccount?.portfolio_risk_percent || 0) / (settings?.max_portfolio_risk_percent || 20)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Offene Positionen: €{(mt5LibertexAccount?.margin || 0).toFixed(2)} ({trades.filter(t => t.status === 'OPEN' && ((t.platform && t.platform.includes('LIBERTEX')) || (t.mode && t.mode.includes('LIBERTEX')))).length})
                  </div>
                </>
              )}
              {!mt5LibertexConnected && (
                <div className="text-xs text-slate-400">
                  Region: London | Status: {settings?.active_platforms?.includes('MT5_LIBERTEX') ? 'Verbindung wird hergestellt...' : 'Inaktiv'}
                </div>
              )}
            </div>
          </Card>

          {/* MT5 ICMarkets Balance Card */}
          <Card className="bg-gradient-to-br from-purple-900/20 to-slate-900/90 border-purple-700/50 backdrop-blur-sm p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings?.active_platforms?.includes('MT5_ICMARKETS') || false}
                  onChange={async (e) => {
                    if (!settings) {
                      toast.error('Settings noch nicht geladen');
                      return;
                    }
                    const newPlatforms = e.target.checked
                      ? [...(settings.active_platforms || []), 'MT5_ICMARKETS']
                      : (settings.active_platforms || []).filter(p => p !== 'MT5_ICMARKETS');
                    await handleUpdateSettings({ ...settings, active_platforms: newPlatforms });
                  }}
                  className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                  disabled={!settings}
                />
                <h3 className="text-sm font-bold text-purple-400">🟣 MT5 ICMarkets</h3>
                {settings?.active_platforms?.includes('MT5_ICMARKETS') && (
                  <Badge className="bg-emerald-600 text-white text-xs">Aktiv</Badge>
                )}
              </div>
              <DollarSign className="w-8 h-8 text-purple-400/20" />
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-slate-400">Balance</p>
                <p className="text-xl font-bold text-white">
                  {mt5Connected ? `€${mt5Account?.balance?.toFixed(2) || '0.00'}` : '€0.00'}
                </p>
              </div>
              {mt5Connected && (
                <>
                  <div className="text-xs text-slate-400">
                    Equity: €{mt5Account?.equity?.toFixed(2)} | Freie Margin: €{mt5Account?.free_margin?.toFixed(2)}
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Portfolio-Risiko:</span>
                      <span className={
                        (mt5Account?.portfolio_risk_percent || 0) > (settings?.max_portfolio_risk_percent || 20)
                          ? 'text-red-400 font-semibold'
                          : 'text-green-400'
                      }>
                        {(mt5Account?.portfolio_risk_percent || 0).toFixed(1)}% / {settings?.max_portfolio_risk_percent || 20}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          (mt5Account?.portfolio_risk_percent || 0) > (settings?.max_portfolio_risk_percent || 20)
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(((mt5Account?.portfolio_risk_percent || 0) / (settings?.max_portfolio_risk_percent || 20)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Offene Positionen: €{(mt5Account?.margin || 0).toFixed(2)} ({trades.filter(t => t.status === 'OPEN' && ((t.platform && t.platform.includes('ICMARKETS')) || (t.mode && t.mode.includes('ICMARKETS')))).length})
                  </div>
                </>
              )}
              {!mt5Connected && (
                <div className="text-xs text-slate-400">
                  Region: London | Status: Verbunden
                </div>
              )}
            </div>
          </Card>

          {/* MT5 Libertex REAL Account Card */}
          <Card className="bg-gradient-to-br from-amber-900/20 to-slate-900/90 border-amber-700/50 backdrop-blur-sm p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings?.active_platforms?.includes('MT5_LIBERTEX_REAL') || false}
                  onChange={async (e) => {
                    if (!settings) {
                      toast.error('Settings noch nicht geladen');
                      return;
                    }
                    const newPlatforms = e.target.checked
                      ? [...(settings.active_platforms || []), 'MT5_LIBERTEX_REAL']
                      : (settings.active_platforms || []).filter(p => p !== 'MT5_LIBERTEX_REAL');
                    await handleUpdateSettings({ ...settings, active_platforms: newPlatforms });
                  }}
                  className="w-4 h-4 rounded border-gray-300 cursor-pointer"
                  disabled={true}
                />
                <h3 className="text-sm font-bold text-amber-400">💰 MT5 Libertex REAL 💰</h3>
                <Badge className="bg-yellow-600 text-white text-xs">ECHTGELD</Badge>
              </div>
              <DollarSign className="w-8 h-8 text-amber-400/20" />
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-xs text-slate-400">Balance</p>
                <p className="text-xl font-bold text-white">€0.00</p>
              </div>
              <div className="text-xs text-amber-400 bg-amber-900/20 p-2 rounded">
                ⚠️ Real Account wird in Kürze hinzugefügt
              </div>
              <div className="text-xs text-slate-400">
                Region: London | Status: Bald verfügbar
              </div>
            </div>
          </Card>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="cards" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-6">
            <TabsTrigger value="cards">📊 Rohstoffe</TabsTrigger>
            <TabsTrigger value="trades">📈 Trades ({trades.length})</TabsTrigger>
            <TabsTrigger value="charts">📉 Charts</TabsTrigger>
            <TabsTrigger value="backtest">🧪 Backtest</TabsTrigger>
            <TabsTrigger value="risk">🛡️ Risiko</TabsTrigger>
          </TabsList>

          {/* Tab 1: Commodity Cards */}
          <TabsContent value="cards">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
          {Object.entries(allMarkets).map(([commodityId, market]) => {
            const commodity = commodities[commodityId];
            if (!commodity) return null;
            
            // V2.3.40: Ampelsystem-Daten abrufen
            const trafficLight = getTrafficLight(commodityId);
            
            return (
              <Card key={commodityId} className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 border-slate-700/50 backdrop-blur-sm p-4 shadow-2xl" data-testid={`commodity-card-${commodityId}`}>
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-cyan-400" />
                      <h3 className="text-lg font-semibold text-slate-200">{commodity.name}</h3>
                    </div>
                    <div className="flex items-center gap-2">
                      {/* V2.3.40: Ampelsystem - Signal-Status */}
                      <div 
                        className="relative group cursor-help"
                        title={`Signal: ${trafficLight.confidence}% / ${trafficLight.threshold}%\n${trafficLight.reason}`}
                      >
                        <div className={`w-4 h-4 rounded-full ${trafficLight.colors?.bg || 'bg-gray-500'} shadow-lg ${trafficLight.colors?.glow || ''}`}>
                          {trafficLight.color === 'green' && (
                            <span className="absolute inset-0 rounded-full animate-ping bg-emerald-400 opacity-50"></span>
                          )}
                        </div>
                        {/* Tooltip */}
                        <div className="absolute right-0 top-6 w-48 p-2 bg-slate-800 border border-slate-600 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-50 text-xs pointer-events-none">
                          <div className="flex justify-between mb-1">
                            <span className="text-slate-400">Confidence:</span>
                            <span className={`font-bold ${trafficLight.color === 'green' ? 'text-emerald-400' : trafficLight.color === 'yellow' ? 'text-yellow-400' : 'text-red-400'}`}>
                              {trafficLight.confidence}%
                            </span>
                          </div>
                          <div className="flex justify-between mb-1">
                            <span className="text-slate-400">Threshold:</span>
                            <span className="text-slate-300">{trafficLight.threshold}%</span>
                          </div>
                          <div className="text-slate-300 text-[10px] mt-1 border-t border-slate-700 pt-1">
                            {trafficLight.reason}
                          </div>
                        </div>
                      </div>
                      {autoRefresh && (
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                      )}
                      <button
                        onClick={() => {
                          setSelectedCommodity({id: commodityId, ...commodity, marketData: allMarkets[commodityId]});
                          setChartModalOpen(true);
                        }}
                        className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
                        title="Chart anzeigen"
                      >
                        <LineChart className="w-5 h-5 text-cyan-400" />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">{commodity.category}</span>
                    {commodity.market_hours && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        <span className="text-slate-400" title="Handelszeiten">{commodity.market_hours}</span>
                      </div>
                    )}
                  </div>
                  {settings?.mode === 'MT5' && !['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'].includes(commodityId) && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded px-2 py-1">
                      <AlertCircle className="w-3 h-3" />
                      <span>✓ Auf Bitpanda handelbar</span>
                    </div>
                  )}
                  {settings?.mode === 'BITPANDA' && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-green-400 bg-green-500/10 border border-green-500/30 rounded px-2 py-1">
                      <AlertCircle className="w-3 h-3" />
                      <span>✓ Handelbar</span>
                    </div>
                  )}
                </div>
                
                <div className="mb-3">
                  <h2 className="text-2xl font-bold mb-0.5" style={{ color: '#2dd4bf' }} data-testid={`price-${commodityId}`}>
                    ${market.price?.toFixed(2) || '0.00'}
                  </h2>
                  <p className="text-xs text-slate-500">{commodity.unit}</p>
                </div>
                
                <div className="flex items-center justify-between mb-3">
                  <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border ${market.signal === 'BUY' ? 'border-emerald-500/50' : market.signal === 'SELL' ? 'border-rose-500/50' : 'border-slate-600/50'}`}>
                    <span className={getSignalColor(market.signal)}>
                      {getSignalIcon(market.signal)}
                    </span>
                    <span className={`text-sm font-bold ${getSignalColor(market.signal)}`}>
                      {market.signal || 'HOLD'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400">
                    {market.trend === 'UP' && <TrendingUp className="w-4 h-4 text-emerald-400 inline" />}
                    {market.trend === 'DOWN' && <TrendingDown className="w-4 h-4 text-rose-400 inline" />}
                    {market.trend === 'NEUTRAL' && <Minus className="w-4 h-4 text-slate-400 inline" />}
                  </div>
                </div>
                
                <div className="mt-3 flex gap-2">
                  <Button
                    onClick={() => handleManualTrade('BUY', commodityId)}
                    size="sm"
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    <TrendingUp className="w-3 h-3 mr-1" />
                    KAUFEN
                  </Button>
                  <Button
                    onClick={() => handleManualTrade('SELL', commodityId)}
                    size="sm"
                    className="flex-1 bg-rose-600 hover:bg-rose-500 text-white"
                  >
                    <TrendingDown className="w-3 h-3 mr-1" />
                    VERKAUFEN
                  </Button>
                </div>
              </Card>
            );
          })}
            </div>
          </TabsContent>

          {/* Tab 2: Trades */}
          <TabsContent value="trades">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">Trade Historie</h3>
              
              {/* Sub-Tabs for Open/Closed Trades */}
              <Tabs defaultValue="open" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="open">
                    📊 Offene Trades ({trades.filter(t => t.status === 'OPEN').length})
                  </TabsTrigger>
                  <TabsTrigger 
                    value="closed"
                    onClick={() => {
                      // V2.3.40: Lade MT5 History mit "Heute" Filter wenn Tab angeklickt wird
                      console.log('📋 Loading closed trades for TODAY...');
                      const todayFilters = {
                        ...mt5HistoryFilters,
                        startDate: new Date().toISOString().split('T')[0],
                        endDate: new Date().toISOString().split('T')[0]
                      };
                      setMt5HistoryFilters(todayFilters);
                      fetchMt5History(todayFilters);
                    }}
                  >
                    📈 Geschlossene Trades ({trades.filter(t => t.status === 'CLOSED').length})
                  </TabsTrigger>
                </TabsList>

                {/* Open Trades Tab */}
                <TabsContent value="open">
                  {trades.filter(t => t.status === 'OPEN').length === 0 ? (
                    <div className="text-center py-12 text-slate-400">
                      <p>Keine offenen Trades</p>
                    </div>
                  ) : (
                    <>
                      <div className="mb-4 flex justify-end">
                        <Button
                          onClick={async () => {
                            if (!window.confirm('Alle offenen Trades zu DAY Trades umwandeln?')) return;
                            try {
                              const openTrades = trades.filter(t => t.status === 'OPEN');
                              console.log('Converting trades:', openTrades.length);
                              let success = 0;
                              for (const trade of openTrades) {
                                try {
                                  await axios.post(`${API}/trades/${trade.id}/update-strategy`, { strategy: 'day' });
                                  success++;
                                } catch (err) {
                                  console.error('Failed:', trade.id, err);
                                }
                              }
                              alert(`✅ ${success}/${openTrades.length} Trades zu DAY umgewandelt`);
                              await fetchTrades();
                            } catch (error) {
                              console.error('Conversion error:', error);
                              alert('❌ Fehler: ' + (error.response?.data?.detail || error.message));
                            }
                          }}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          🔄 Alle zu DAY umwandeln
                        </Button>
                      </div>
                      <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-800/50 border-b border-slate-700">
                          <tr>
                            <th className="px-4 py-3 text-left text-slate-300">Rohstoff</th>
                            <th className="px-4 py-3 text-left text-slate-300">Typ</th>
                            <th className="px-4 py-3 text-center text-slate-300">Strategie</th>
                            <th className="px-4 py-3 text-right text-slate-300">Einstieg</th>
                            <th className="px-4 py-3 text-right text-slate-300">Aktuell</th>
                            <th className="px-4 py-3 text-right text-slate-300">Menge</th>
                            <th className="px-4 py-3 text-right text-amber-400">SL</th>
                            <th className="px-4 py-3 text-right text-cyan-400">TP</th>
                            <th className="px-4 py-3 text-right text-slate-300">P&L</th>
                            <th className="px-4 py-3 text-center text-slate-300">Fortschritt</th>
                            <th className="px-4 py-3 text-center text-slate-300">Plattform</th>
                            <th className="px-4 py-3 text-center text-slate-300">Aktion</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trades.filter(t => {
                            // Filter: Nur offene Trades OHNE Error Codes
                            if (t.status !== 'OPEN') return false;
                            
                            // Aussortieren: Trades mit MetaAPI Error Codes
                            const hasErrorCode = t.commodity?.includes('TRADE_RETCODE') || 
                                                 t.mt5_ticket?.toString().includes('TRADE_RETCODE');
                            return !hasErrorCode;
                          }).map((trade) => {
                        // Map MT5 symbols to commodity IDs
                        const symbolToCommodity = {
                          'XAUUSD': 'GOLD',
                          'XAGUSD': 'SILVER',
                          'XPTUSD': 'PLATINUM',
                          'XPDUSD': 'PALLADIUM',
                          'PL': 'PLATINUM',
                          'PA': 'PALLADIUM',
                          'USOILCash': 'WTI_CRUDE',
                          'CL': 'BRENT_CRUDE',
                          'NGASCash': 'NATURAL_GAS',
                          'WHEAT': 'WHEAT',
                          'CORN': 'CORN',
                          'SOYBEAN': 'SOYBEANS',
                          'COFFEE': 'COFFEE',
                          'SUGAR': 'SUGAR',
                          'COTTON': 'COTTON',
                          'COCOA': 'COCOA'
                        };
                        
                        const commodityId = symbolToCommodity[trade.commodity] || trade.commodity;
                        const commodity = commodities[commodityId];
                        
                        // V2.3.32 FIX: Verwende MT5-Preis (trade.price) ZUERST für konsistente Anzeige
                        // trade.price kommt von MT5 und stimmt mit dem P&L überein
                        // allMarkets kommt von Yahoo Finance und kann abweichen
                        const currentPrice = trade.price || allMarkets[commodityId]?.price || trade.entry_price;
                        
                        // Calculate P&L
                        const pl = trade.status === 'OPEN' 
                          ? (trade.profit_loss !== undefined && trade.profit_loss !== null)
                            ? trade.profit_loss  // Use MT5's calculated P&L if available
                            : (trade.type === 'BUY' ? currentPrice - trade.entry_price : trade.entry_price - currentPrice) * trade.quantity
                          : trade.profit_loss || 0;
                        
                        return (
                          <tr 
                            key={trade.id} 
                            className="border-b border-slate-800 hover:bg-slate-800/30 cursor-pointer transition-colors"
                            onClick={(e) => {
                              // Safari fix: Only handle clicks on the row itself, not on buttons
                              if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                                return; // Let button handlers take over
                              }
                              console.log('🖱️ Row clicked!', trade.commodity);
                              e.preventDefault();
                              e.stopPropagation();
                              handleTradeClick(trade);
                            }}
                          >
                            <td className="px-4 py-3 text-slate-200">
                              {commodity?.name || trade.commodity}
                              {trade.mt5_ticket && (
                                <span className="ml-2 text-xs text-slate-500">#{trade.mt5_ticket}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <Badge className={trade.type === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                                {trade.type}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-center">
                              {/* V2.3.32: Alle Strategien anzeigen */}
                              {trade.strategy === 'swing' || trade.strategy === 'swing_trading' ? (
                                <Badge className="bg-purple-600 text-xs">📈 Swing</Badge>
                              ) : trade.strategy === 'day' || trade.strategy === 'day_trading' ? (
                                <Badge className="bg-blue-600 text-xs">⚡ Day</Badge>
                              ) : trade.strategy === 'mean_reversion' ? (
                                <Badge className="bg-pink-600 text-xs">🔄 Mean Rev</Badge>
                              ) : trade.strategy === 'momentum' ? (
                                <Badge className="bg-orange-600 text-xs">🚀 Momentum</Badge>
                              ) : trade.strategy === 'scalping' ? (
                                <Badge className="bg-yellow-600 text-xs">⚡ Scalping</Badge>
                              ) : trade.strategy === 'breakout' ? (
                                <Badge className="bg-cyan-600 text-xs">💥 Breakout</Badge>
                              ) : trade.strategy === 'grid' ? (
                                <Badge className="bg-indigo-600 text-xs">📊 Grid</Badge>
                              ) : (
                                <Badge className="bg-slate-600 text-xs">? {trade.strategy || 'Manual'}</Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right text-slate-200">${trade.entry_price?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">${currentPrice?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">{trade.quantity}</td>
                            <td className="px-4 py-3 text-right">
                              {(() => {
                                const sl = trade.stop_loss;
                                if (sl !== null && sl !== undefined && !isNaN(Number(sl))) {
                                  return <span className="text-amber-400">${Number(sl).toFixed(2)}</span>;
                                }
                                return <span className="text-slate-600 text-xs">Kein SL</span>;
                              })()}
                            </td>
                            <td className="px-4 py-3 text-right">
                              {(() => {
                                const tp = trade.take_profit;
                                if (tp !== null && tp !== undefined && !isNaN(Number(tp))) {
                                  return <span className="text-cyan-400">${Number(tp).toFixed(2)}</span>;
                                }
                                return <span className="text-slate-600 text-xs">Kein TP</span>;
                              })()}
                            </td>
                            <td className={`px-4 py-3 text-right font-semibold ${pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {pl >= 0 ? '+' : ''}{pl.toFixed(2)} €
                            </td>
                            <td className="px-4 py-3 text-center">
                              {(() => {
                                // Berechne Fortschritt zum Ziel (basierend auf Take Profit)
                                if (trade.status === 'OPEN' && trade.entry_price && settings) {
                                  // V2.3.32 FIX: Verwende MT5-Preis (trade.price) für Fortschritt
                                  // NICHT Marktdaten, da diese von Yahoo kommen und abweichen können
                                  const commodityId = trade.commodity;
                                  const currentPrice = trade.price || allMarkets[commodityId]?.price || trade.entry_price;
                                  const entryPrice = trade.entry_price;
                                  const targetPrice = trade.take_profit;
                                  
                                  // CRITICAL FIX V2.3.4: Check if targetPrice is valid number
                                  if (!targetPrice || targetPrice === null || targetPrice === undefined || isNaN(targetPrice)) {
                                    return <span className="text-xs text-slate-500">Kein TP gesetzt</span>;
                                  }
                                  
                                  // Prüfe ob TP erreicht ist (mit Richtung)
                                  const isTargetReached = trade.type === 'BUY' 
                                    ? currentPrice >= targetPrice 
                                    : currentPrice <= targetPrice;
                                  
                                  if (isTargetReached) {
                                    return (
                                      <div className="text-xs">
                                        <span className="text-green-400 font-semibold">✅ Ziel erreicht!</span>
                                        <p className="text-amber-400 mt-1">⚠️ Trade sollte geschlossen werden</p>
                                      </div>
                                    );
                                  }
                                  
                                  // Berechne Distanz zum Ziel (in richtige Richtung)
                                  const totalDistance = Math.abs(targetPrice - entryPrice);
                                  let currentDistance;
                                  
                                  if (trade.type === 'BUY') {
                                    currentDistance = Math.max(0, currentPrice - entryPrice);
                                  } else {
                                    currentDistance = Math.max(0, entryPrice - currentPrice);
                                  }
                                  
                                  const progressPercent = totalDistance > 0 ? (currentDistance / totalDistance) * 100 : 0;
                                  const remaining = Math.max(0, 100 - progressPercent);
                                  
                                  return (
                                    <div className="text-xs">
                                      {progressPercent > 50 ? (
                                        <span className="text-cyan-400">Noch {remaining.toFixed(0)}% zum Ziel 🎯</span>
                                      ) : progressPercent > 0 ? (
                                        <span className="text-slate-400">Noch {remaining.toFixed(0)}% zum Ziel</span>
                                      ) : (
                                        <span className="text-red-400">Gegenläufig {Math.abs(progressPercent).toFixed(0)}%</span>
                                      )}
                                    </div>
                                  );
                                }
                                return <span className="text-xs text-slate-500">-</span>;
                              })()}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge className={
                                trade.platform === 'MT5_LIBERTEX' ? 'bg-blue-600' :
                                trade.platform === 'MT5_ICMARKETS' ? 'bg-purple-600' :
                                trade.platform === 'BITPANDA' ? 'bg-green-600' :
                                trade.mode === 'MT5' ? 'bg-blue-600' : 'bg-green-600'
                              }>
                                {trade.platform || trade.mode || 'MT5'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-center space-x-2">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  console.log('⚙️ Settings button clicked for:', trade.commodity);
                                  handleTradeClick(trade);
                                }}
                                className="text-blue-400 hover:text-blue-300 text-xs font-semibold px-2 py-1 bg-blue-900/20 rounded"
                                title="SL/TP bearbeiten"
                              >
                                ⚙️
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleCloseTrade(trade);
                                }}
                                className="text-orange-400 hover:text-orange-300 text-xs font-semibold px-2 py-1 bg-orange-900/20 rounded"
                                title="Position schließen"
                              >
                                🔒
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteTrade(trade.id, `${commodity?.name || trade.commodity} ${trade.type}`);
                                }}
                                className="text-red-400 hover:text-red-300 text-xs"
                                title="Trade löschen"
                              >
                                🗑️
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                    </>
              )}
            </TabsContent>

            {/* Closed Trades Tab - V2.3.37: MT5 History mit Filtern */}
            <TabsContent value="closed">
              {/* Filter Section */}
              <div className="mb-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="flex flex-wrap gap-4 items-end">
                  {/* Datum Von */}
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-400">Von</Label>
                    <input
                      type="date"
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm"
                      value={mt5HistoryFilters.startDate}
                      onChange={(e) => setMt5HistoryFilters({...mt5HistoryFilters, startDate: e.target.value})}
                    />
                  </div>
                  
                  {/* Datum Bis */}
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-400">Bis</Label>
                    <input
                      type="date"
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm"
                      value={mt5HistoryFilters.endDate}
                      onChange={(e) => setMt5HistoryFilters({...mt5HistoryFilters, endDate: e.target.value})}
                    />
                  </div>
                  
                  {/* Rohstoff Filter */}
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-400">Rohstoff</Label>
                    <select
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm min-w-[120px]"
                      value={mt5HistoryFilters.commodity}
                      onChange={(e) => setMt5HistoryFilters({...mt5HistoryFilters, commodity: e.target.value})}
                    >
                      <option value="">Alle</option>
                      {mt5FilterOptions.commodities.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Strategie Filter */}
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-400">Strategie</Label>
                    <select
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm min-w-[120px]"
                      value={mt5HistoryFilters.strategy}
                      onChange={(e) => setMt5HistoryFilters({...mt5HistoryFilters, strategy: e.target.value})}
                    >
                      <option value="">Alle</option>
                      {mt5FilterOptions.strategies.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Plattform Filter */}
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-400">Plattform</Label>
                    <select
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm min-w-[150px]"
                      value={mt5HistoryFilters.platform}
                      onChange={(e) => setMt5HistoryFilters({...mt5HistoryFilters, platform: e.target.value})}
                    >
                      <option value="">Alle</option>
                      {mt5FilterOptions.platforms.map(p => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Laden Button */}
                  <Button
                    onClick={() => fetchMt5History(mt5HistoryFilters)}
                    disabled={mt5HistoryLoading}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {mt5HistoryLoading ? '⏳ Lade...' : '🔄 MT5 History laden'}
                  </Button>
                  
                  {/* Filter Reset */}
                  <Button
                    variant="outline"
                    onClick={() => {
                      const resetFilters = {
                        startDate: new Date().toISOString().split('T')[0],  // V2.3.40: Reset auf Heute
                        endDate: new Date().toISOString().split('T')[0],
                        commodity: '',
                        strategy: '',
                        platform: ''
                      };
                      setMt5HistoryFilters(resetFilters);
                      fetchMt5History(resetFilters);
                    }}
                    className="border-slate-600"
                  >
                    ↺ Reset
                  </Button>
                </div>
                
                {/* V2.3.40: Quick-Filter Buttons */}
                <div className="mt-3 flex gap-2">
                  <span className="text-xs text-slate-500 self-center mr-2">Schnellfilter:</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const today = new Date().toISOString().split('T')[0];
                      const filters = { ...mt5HistoryFilters, startDate: today, endDate: today };
                      setMt5HistoryFilters(filters);
                      fetchMt5History(filters);
                    }}
                    className={`text-xs h-7 ${mt5HistoryFilters.startDate === new Date().toISOString().split('T')[0] && mt5HistoryFilters.endDate === new Date().toISOString().split('T')[0] ? 'bg-cyan-600 border-cyan-500' : 'border-slate-600'}`}
                  >
                    📅 Heute
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const filters = {
                        ...mt5HistoryFilters,
                        startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        endDate: new Date().toISOString().split('T')[0]
                      };
                      setMt5HistoryFilters(filters);
                      fetchMt5History(filters);
                    }}
                    className="text-xs h-7 border-slate-600"
                  >
                    📆 7 Tage
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const filters = {
                        ...mt5HistoryFilters,
                        startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        endDate: new Date().toISOString().split('T')[0]
                      };
                      setMt5HistoryFilters(filters);
                      fetchMt5History(filters);
                    }}
                    className="text-xs h-7 border-slate-600"
                  >
                    🗓️ 30 Tage
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const filters = {
                        ...mt5HistoryFilters,
                        startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                        endDate: new Date().toISOString().split('T')[0]
                      };
                      setMt5HistoryFilters(filters);
                      fetchMt5History(filters);
                    }}
                    className="text-xs h-7 border-slate-600"
                  >
                    📊 90 Tage
                  </Button>
                </div>
                
                {/* Statistiken */}
                {mt5History.length > 0 && (
                  <div className="mt-4 flex gap-6 text-sm">
                    <div className="text-slate-400">
                      Trades: <span className="text-white font-semibold">{mt5History.length}</span>
                    </div>
                    <div className="text-slate-400">
                      Gesamt P&L: <span className={`font-semibold ${mt5Statistics.total_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        €{mt5Statistics.total_profit?.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-slate-400">
                      Gewinne: <span className="text-green-400 font-semibold">{mt5Statistics.winning_trades}</span>
                    </div>
                    <div className="text-slate-400">
                      Verluste: <span className="text-red-400 font-semibold">{mt5Statistics.losing_trades}</span>
                    </div>
                    <div className="text-slate-400">
                      Win Rate: <span className="text-cyan-400 font-semibold">{mt5Statistics.win_rate}%</span>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Tabelle */}
              {mt5HistoryLoading ? (
                <div className="text-center py-12 text-slate-400">
                  <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mb-4"></div>
                  <p>Lade MT5 History...</p>
                </div>
              ) : mt5History.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <p>Keine geschlossenen Trades gefunden</p>
                  <p className="text-sm mt-2">Klicken Sie auf MT5 History laden um Trades von MT5 abzurufen</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800/50 border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-300">Rohstoff</th>
                        <th className="px-4 py-3 text-left text-slate-300">Typ</th>
                        <th className="px-4 py-3 text-center text-slate-300">Strategie</th>
                        <th className="px-4 py-3 text-right text-slate-300">Einstieg</th>
                        <th className="px-4 py-3 text-right text-slate-300">Ausstieg</th>
                        <th className="px-4 py-3 text-right text-slate-300">Lot</th>
                        <th className="px-4 py-3 text-right text-slate-300">P&L</th>
                        <th className="px-4 py-3 text-right text-slate-300">Swap</th>
                        <th className="px-4 py-3 text-center text-slate-300">Plattform</th>
                        <th className="px-4 py-3 text-center text-slate-300">Geschlossen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* V2.3.40 DEBUG: Zeige erste 3 Trades zur Diagnose */}
                      {mt5History.slice(0, 3).map((t, i) => console.log(`DEBUG Trade ${i}: strategy=${t.strategy}, positionId=${t.positionId}`))}
                      {mt5History.map((trade, idx) => {
                        const pl = trade.profit || trade.profit_loss || 0;
                        
                        return (
                          <tr key={trade.id || idx} className="border-b border-slate-800 hover:bg-slate-800/30">
                            <td className="px-4 py-3 text-slate-200">
                              {trade.commodity || trade.symbol}
                              {trade.positionId && (
                                <span className="ml-2 text-xs text-slate-500">#{trade.positionId}</span>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <Badge className={trade.direction === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                                {trade.direction || trade.type}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge variant="outline" className={`text-xs ${trade.strategy && trade.strategy !== 'unknown' ? 'border-cyan-500 text-cyan-400' : 'border-slate-600'}`}>
                                {trade.strategy || 'unknown'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-300">
                              {trade.entry_price ? `$${parseFloat(trade.entry_price).toFixed(2)}` : '-'}
                            </td>
                            <td className="px-4 py-3 text-right text-slate-300">
                              ${parseFloat(trade.exit_price || trade.price || 0).toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right text-slate-300">
                              {trade.volume || trade.lot_size || '-'}
                            </td>
                            <td className={`px-4 py-3 text-right font-semibold ${pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              €{parseFloat(pl).toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-right text-slate-400 text-xs">
                              €{parseFloat(trade.swap || 0).toFixed(2)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge className={
                                trade.platform?.includes('LIBERTEX') ? 'bg-blue-600' :
                                trade.platform?.includes('ICMARKETS') ? 'bg-purple-600' :
                                'bg-slate-600'
                              }>
                                {trade.platform_name || trade.platform || 'MT5'}
                              </Badge>
                              {trade.is_real && (
                                <Badge className="ml-1 bg-amber-600 text-xs">REAL</Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-center text-slate-400 text-xs">
                              {trade.closed_at || trade.time ? 
                                new Date(trade.closed_at || trade.time).toLocaleString('de-DE', {
                                  day: '2-digit',
                                  month: '2-digit',
                                  year: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                }) : '-'
                              }
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </Card>
      </TabsContent>

          {/* Tab 3: Charts */}
          <TabsContent value="charts">
            <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm">
              <h3 className="text-xl font-semibold mb-4 text-cyan-400">Markt Charts mit Timeframe-Auswahl</h3>
              
              {/* Chart Timeframe Controls */}
              <div className="mb-6 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Timeframe Selection */}
                  <div className="space-y-3">
                    <Label className="text-sm font-semibold text-slate-300">Zeitrahmen (Interval)</Label>
                    <select
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm"
                      value={chartTimeframe}
                      onChange={(e) => setChartTimeframe(e.target.value)}
                    >
                      <option value="1m">1 Minute (Live-Ticker)</option>
                      <option value="5m">5 Minuten (Empfohlen für Trading)</option>
                      <option value="15m">15 Minuten</option>
                      <option value="30m">30 Minuten</option>
                      <option value="1h">1 Stunde</option>
                      <option value="4h">4 Stunden</option>
                      <option value="1d">1 Tag</option>
                      <option value="1wk">1 Woche</option>
                      <option value="1mo">1 Monat</option>
                    </select>
                    <p className="text-xs text-slate-400">⚡ Live-Trading: 1m/5m für Echtzeit-Daten</p>
                  </div>
                  
                  {/* Period Selection */}
                  <div className="space-y-3">
                    <Label className="text-sm font-semibold text-slate-300">Zeitraum (Periode)</Label>
                    <select
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-md text-white text-sm"
                      value={chartPeriod}
                      onChange={(e) => setChartPeriod(e.target.value)}
                    >
                      <option value="1d">1 Tag</option>
                      <option value="5d">1 Woche</option>
                      <option value="2wk">2 Wochen</option>
                      <option value="1mo">1 Monat</option>
                      <option value="3mo">3 Monate</option>
                      <option value="6mo">6 Monate</option>
                      <option value="1y">1 Jahr</option>
                      <option value="2y">2 Jahre</option>
                      <option value="5y">5 Jahre</option>
                      <option value="max">Maximum</option>
                    </select>
                  </div>
                </div>
                
                <div className="mt-3 text-xs text-slate-400">
                  Aktuelle Auswahl: <span className="text-cyan-400 font-semibold">{chartTimeframe}</span> Interval über <span className="text-cyan-400 font-semibold">{chartPeriod}</span> Zeitraum
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(allMarkets).map(([commodityId, market]) => {
                  const commodity = commodities[commodityId];
                  if (!commodity) return null;
                  
                  return (
                    <Card key={commodityId} className="bg-slate-800/50 border-slate-700 p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-semibold text-slate-200">{commodity.name}</h4>
                        <button
                          onClick={() => {
                            setSelectedCommodity({id: commodityId, ...commodity, marketData: market});
                            setChartModalOpen(true);
                          }}
                          className="text-cyan-400 hover:text-cyan-300 hover:scale-110 transition-transform"
                          title="Chart anzeigen"
                        >
                          <LineChart className="w-5 h-5" />
                        </button>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-cyan-400">
                          ${market.price?.toFixed(2) || '0.00'}
                        </p>
                        <p className="text-sm text-slate-400">{commodity.unit}</p>
                        <div className="mt-2 flex items-center justify-center gap-2">
                          <span className={`text-xs px-2 py-1 rounded ${
                            market.signal === 'BUY' ? 'bg-green-900/30 text-green-400' :
                            market.signal === 'SELL' ? 'bg-red-900/30 text-red-400' :
                            'bg-slate-700/30 text-slate-400'
                          }`}>
                            {market.signal || 'HOLD'}
                          </span>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </Card>
          </TabsContent>
          
          {/* Tab 4: Backtesting */}
          <TabsContent value="backtest">
            <BacktestingPanel />
          </TabsContent>
          
          {/* Tab 5: Risk Dashboard */}
          <TabsContent value="risk">
            <RiskDashboard />
          </TabsContent>
        </Tabs>
        
        {/* Portfolio Exposure Warning */}
        {/* Portfolio-Risiko Warnungen - PER PLATFORM */}
        {mt5LibertexAccount && (mt5LibertexAccount?.portfolio_risk_percent || 0) > (settings?.combined_max_balance_percent_per_platform || 20) && (
          <Card className="bg-amber-900/20 border-amber-500/50 p-4 mb-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-400" />
              <div className="flex-1">
                <h4 className="font-semibold text-amber-400">⚠️ Libertex Portfolio-Risiko zu hoch!</h4>
                <p className="text-sm text-slate-300 mb-2">
                  <strong>Genutzte Margin:</strong> €{(mt5LibertexAccount?.margin || 0).toFixed(2)} 
                  ({(mt5LibertexAccount?.portfolio_risk_percent || 0).toFixed(1)}% Portfolio-Risiko)
                </p>
                <p className="text-xs text-slate-400">
                  • Ihre Libertex Equity: €{mt5LibertexAccount?.equity?.toFixed(2)}<br/>
                  • Empfohlenes Maximum: {settings?.combined_max_balance_percent_per_platform || 20}% Portfolio-Risiko<br/>
                  • 🚫 <strong>AI Bot wird KEINE neuen Trades auf Libertex öffnen bis Risiko unter {settings?.combined_max_balance_percent_per_platform || 20}%</strong>
                </p>
              </div>
            </div>
          </Card>
        )}
        
        {mt5Account && (mt5Account?.portfolio_risk_percent || 0) > (settings?.combined_max_balance_percent_per_platform || 20) && (
          <Card className="bg-amber-900/20 border-amber-500/50 p-4 mb-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-400" />
              <div className="flex-1">
                <h4 className="font-semibold text-amber-400">⚠️ ICMarkets Portfolio-Risiko zu hoch!</h4>
                <p className="text-sm text-slate-300 mb-2">
                  <strong>Genutzte Margin:</strong> €{(mt5Account?.margin || 0).toFixed(2)} 
                  ({(mt5Account?.portfolio_risk_percent || 0).toFixed(1)}% Portfolio-Risiko)
                </p>
                <p className="text-xs text-slate-400">
                  • Ihre ICMarkets Equity: €{mt5Account?.equity?.toFixed(2)}<br/>
                  • Empfohlenes Maximum: {settings?.combined_max_balance_percent_per_platform || 20}% Portfolio-Risiko<br/>
                  • 🚫 <strong>AI Bot wird KEINE neuen Trades auf ICMarkets öffnen bis Risiko unter {settings?.combined_max_balance_percent_per_platform || 20}%</strong>
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Stats Cards */}
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-slate-300">📊 Trading Statistiken</h3>
          <Button
            variant="outline"
            size="sm"
            className="border-red-600 text-red-400 hover:bg-red-600/20"
            onClick={async () => {
              if (!window.confirm('Alle Statistiken zurücksetzen? Dies löscht alle geschlossenen Trades und setzt die Statistiken auf 0.')) return;
              try {
                // Lösche alle geschlossenen Trades
                const response = await axios.post(`${API}/trades/delete-all-closed`);
                if (response.data.success) {
                  toast.success(`✅ ${response.data.deleted_count} Trades gelöscht - Statistiken zurückgesetzt`);
                  await fetchStats();
                  await fetchTrades();
                }
              } catch (error) {
                console.error('Reset error:', error);
                toast.error('❌ Fehler beim Zurücksetzen: ' + (error.response?.data?.detail || error.message));
              }
            }}
          >
            🔄 Statistiken zurücksetzen
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-total-trades">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Gesamt Trades</p>
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stats?.total_trades || 0}</p>
            <p className="text-xs text-slate-500 mt-1">
              Offen: {stats?.open_positions || 0} | Geschlossen: {stats?.closed_positions || 0}
            </p>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-profit-loss">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Gewinn / Verlust</p>
              <DollarSign className="w-5 h-5 text-cyan-400" />
            </div>
            <p className={`text-3xl font-bold ${stats?.total_profit_loss >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              ${stats?.total_profit_loss?.toFixed(2) || '0.00'}
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Win: {stats?.winning_trades || 0} | Loss: {stats?.losing_trades || 0}
            </p>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-win-rate">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Trefferquote</p>
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stats?.win_rate?.toFixed(1) || '0.0'}%</p>
            <div className="w-full bg-slate-700 rounded-full h-2 mt-2">
              <div
                className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${stats?.win_rate || 0}%` }}
              />
            </div>
          </Card>

          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="trading-mode-card">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Trading Modus</p>
              {settings?.auto_trading ? <Play className="w-5 h-5 text-emerald-400" /> : <Pause className="w-5 h-5 text-slate-400" />}
            </div>
            <p className="text-2xl font-bold text-white mb-1">
              {settings?.active_platforms?.length > 0 
                ? settings.active_platforms.join(' + ')
                : 'Keine Platform aktiv'}
            </p>
            <p className={`text-sm ${settings?.auto_trading ? 'text-emerald-400' : 'text-slate-400'}`}>
              {settings?.auto_trading ? 'Auto-Trading Aktiv' : 'Manueller Modus'}
            </p>
            {settings?.auto_trading && (
              <div className="flex gap-2 mt-2">
                {settings?.swing_trading_enabled && (
                  <Badge className="bg-green-600/20 text-green-300 border-green-600/50 text-xs">
                    📈 Swing
                  </Badge>
                )}
                {settings?.day_trading_enabled && (
                  <Badge className="bg-orange-600/20 text-orange-300 border-orange-600/50 text-xs">
                    ⚡ Day
                  </Badge>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Old tabs section removed - now using new 3-tab structure above */}
      </div>

      {/* Chart Modal */}
      <Dialog open={chartModalOpen} onOpenChange={setChartModalOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] bg-slate-900 border-slate-700 overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-cyan-400 flex items-center gap-2">
              <LineChart className="w-6 h-6" />
              {selectedCommodity?.name} - Detaillierte Analyse
            </DialogTitle>
          </DialogHeader>
          
          {selectedCommodity && (
            <div className="space-y-6 mt-4">
              {/* Trade Buttons - ganz oben */}
              <div className="flex gap-4 justify-center pb-4 border-b border-slate-700">
                <Button
                  onClick={() => {
                    setChartModalOpen(false);
                    handleManualTrade('BUY', selectedCommodity.id);
                  }}
                  className="flex-1 max-w-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 text-lg"
                >
                  <TrendingUp className="w-6 h-6 mr-2" />
                  KAUFEN
                </Button>
                <Button
                  onClick={() => {
                    setChartModalOpen(false);
                    handleManualTrade('SELL', selectedCommodity.id);
                  }}
                  className="flex-1 max-w-xs bg-rose-600 hover:bg-rose-500 text-white font-bold py-3 text-lg"
                >
                  <TrendingDown className="w-6 h-6 mr-2" />
                  VERKAUFEN
                </Button>
              </div>

              {/* Open Trades for this Asset */}
              {(() => {
                const assetTrades = trades.filter(trade => 
                  trade.commodity === selectedCommodity.id && 
                  trade.status === 'OPEN'
                );
                
                if (assetTrades.length > 0) {
                  return (
                    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 p-4 rounded-lg border border-blue-500/30">
                      <h4 className="text-sm font-semibold text-blue-300 mb-3 flex items-center gap-2">
                        <Activity className="w-4 h-4" />
                        Offene Positionen für {selectedCommodity.name} ({assetTrades.length})
                      </h4>
                      <div className="space-y-2">
                        {assetTrades.map((trade) => (
                          <div key={trade.ticket || trade.id} className="bg-slate-800/50 p-3 rounded-lg flex items-center justify-between">
                            <div className="flex-1 grid grid-cols-4 gap-3 text-sm">
                              <div>
                                <p className="text-xs text-slate-400">Typ</p>
                                <Badge className={trade.type === 'BUY' ? 'bg-green-600' : 'bg-red-600'}>
                                  {trade.type}
                                </Badge>
                              </div>
                              <div>
                                <p className="text-xs text-slate-400">Menge</p>
                                <p className="font-semibold text-white">{trade.quantity || trade.volume}</p>
                              </div>
                              <div>
                                <p className="text-xs text-slate-400">Einstieg</p>
                                <p className="font-semibold text-white">${(trade.entry_price || trade.price_open)?.toFixed(2)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-slate-400">P&L</p>
                                <p className={`font-bold ${
                                  (trade.profit_loss || trade.pnl || trade.profit || trade.current_pl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                                }`}>
                                  {(trade.profit_loss || trade.pnl || trade.profit || trade.current_pl || 0) >= 0 ? '+' : ''}
                                  ${(trade.profit_loss || trade.pnl || trade.profit || trade.current_pl || 0)?.toFixed(2)}
                                </p>
                              </div>
                            </div>
                            <Button
                              onClick={async () => {
                                try {
                                  await axios.post(`${API}/trades/close`, {
                                    trade_id: trade.id,
                                    ticket: trade.ticket,
                                    platform: trade.platform
                                  });
                                  toast.success('✅ Position erfolgreich geschlossen!');
                                  fetchTrades();
                                  fetchAccountData();
                                } catch (error) {
                                  const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unbekannter Fehler';
                                  console.error('Fehler beim Schließen:', error.response?.data || error);
                                  toast.error('❌ Fehler: ' + errorMsg);
                                }
                              }}
                              size="sm"
                              variant="destructive"
                              className="ml-3"
                            >
                              <X className="w-4 h-4 mr-1" />
                              Schließen
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }
                return null;
              })()}

              {/* Price Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Aktueller Preis</p>
                  <p className="text-2xl font-bold text-white">
                    ${selectedCommodity.marketData?.price?.toFixed(2) || 'N/A'}
                  </p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">24h Änderung</p>
                  <p className={`text-2xl font-bold ${
                    chartModalData.length >= 2 && chartModalData[0]?.close && chartModalData[chartModalData.length - 1]?.close
                      ? ((chartModalData[chartModalData.length - 1].close - chartModalData[0].close) / chartModalData[0].close * 100) >= 0 
                        ? 'text-green-400' 
                        : 'text-red-400'
                      : 'text-slate-400'
                  }`}>
                    {chartModalData.length >= 2 && chartModalData[0]?.close && chartModalData[chartModalData.length - 1]?.close
                      ? `${((chartModalData[chartModalData.length - 1].close - chartModalData[0].close) / chartModalData[0].close * 100) >= 0 ? '+' : ''}${((chartModalData[chartModalData.length - 1].close - chartModalData[0].close) / chartModalData[0].close * 100).toFixed(2)}%`
                      : 'N/A'}
                  </p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Signal</p>
                  <Badge className={
                    selectedCommodity.marketData?.signal === 'BUY' ? 'bg-green-600' :
                    selectedCommodity.marketData?.signal === 'SELL' ? 'bg-red-600' :
                    'bg-slate-600'
                  }>
                    {selectedCommodity.marketData?.signal || 'HOLD'}
                  </Badge>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <p className="text-xs text-slate-400 mb-1">Trend</p>
                  <div className="flex items-center gap-2">
                    {selectedCommodity.marketData?.trend === 'UP' && <TrendingUp className="w-5 h-5 text-green-400" />}
                    {selectedCommodity.marketData?.trend === 'DOWN' && <TrendingDown className="w-5 h-5 text-red-400" />}
                    {selectedCommodity.marketData?.trend === 'NEUTRAL' && <Minus className="w-5 h-5 text-slate-400" />}
                    <span className="font-semibold">{selectedCommodity.marketData?.trend || 'NEUTRAL'}</span>
                  </div>
                </div>
              </div>

              {/* Large Chart */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-cyan-400">
                    {selectedCommodity.name} Chart
                  </h3>
                  <div className="flex gap-3 items-center">
                    <span className="text-xs text-slate-400">Intervall:</span>
                    <select
                      value={chartTimeframe}
                      onChange={(e) => setChartTimeframe(e.target.value)}
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded text-sm text-white hover:border-cyan-500 focus:outline-none focus:border-cyan-500"
                      title="Kerzen-Intervall"
                    >
                      <option value="1m">1 Minute</option>
                      <option value="5m">5 Minuten</option>
                      <option value="15m">15 Minuten</option>
                      <option value="30m">30 Minuten</option>
                      <option value="1h">1 Stunde</option>
                      <option value="2h">2 Stunden</option>
                      <option value="4h">4 Stunden</option>
                      <option value="1d">1 Tag</option>
                      <option value="1wk">1 Woche</option>
                    </select>
                    
                    <span className="text-xs text-slate-400">Zeitraum:</span>
                    <select
                      value={chartPeriod}
                      onChange={(e) => setChartPeriod(e.target.value)}
                      className="px-3 py-2 bg-slate-900 border border-slate-600 rounded text-sm text-white hover:border-cyan-500 focus:outline-none focus:border-cyan-500"
                      title="Gesamt-Zeitraum"
                    >
                      <option value="2h">2 Stunden</option>
                      <option value="1d">1 Tag</option>
                      <option value="5d">5 Tage</option>
                      <option value="1wk">1 Woche</option>
                      <option value="2wk">2 Wochen</option>
                      <option value="1mo">1 Monat</option>
                      <option value="3mo">3 Monate</option>
                      <option value="6mo">6 Monate</option>
                      <option value="1y">1 Jahr</option>
                    </select>
                  </div>
                </div>
                {chartModalData.length > 0 ? (
                  <div className="h-96">
                    <PriceChart 
                      data={chartModalData} 
                      commodityName={selectedCommodity.name} 
                      commodityId={selectedCommodity.id}
                      isOHLCV={true} 
                      enableLiveTicker={true}
                    />
                  </div>
                ) : (
                  <div className="h-96 flex items-center justify-center text-slate-400">
                    <RefreshCw className="w-8 h-8 animate-spin mb-2" />
                    <p>Lade Chart-Daten für {selectedCommodity.name}...</p>
                  </div>
                )}
              </Card>

              {/* Technical Indicators */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400">Technische Indikatoren</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">RSI</p>
                    <p className="text-xl font-bold text-white">{selectedCommodity.marketData?.rsi?.toFixed(2) || 'N/A'}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {selectedCommodity.marketData?.rsi > 70 ? 'Überkauft' :
                       selectedCommodity.marketData?.rsi < 30 ? 'Überverkauft' : 'Neutral'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">MACD</p>
                    <p className="text-xl font-bold text-white">{selectedCommodity.marketData?.macd?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">SMA 20</p>
                    <p className="text-xl font-bold text-white">${selectedCommodity.marketData?.sma_20?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">EMA 20</p>
                    <p className="text-xl font-bold text-white">${selectedCommodity.marketData?.ema_20?.toFixed(2) || 'N/A'}</p>
                  </div>
                </div>
              </Card>

              {/* Commodity Info */}
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <h3 className="text-lg font-semibold mb-4 text-cyan-400">Informationen</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Kategorie</p>
                    <p className="text-base font-semibold">{selectedCommodity.category}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Einheit</p>
                    <p className="text-base font-semibold">{selectedCommodity.unit || selectedCommodity.marketData?.unit || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Verfügbar auf</p>
                    <div className="flex gap-2">
                      {['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM'].includes(selectedCommodity.id) ? (
                        <>
                          <Badge className="bg-blue-600">MT5</Badge>
                          <Badge className="bg-green-600">Bitpanda</Badge>
                        </>
                      ) : (
                        <Badge className="bg-green-600">Bitpanda</Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Letztes Update</p>
                    <p className="text-base font-semibold">
                      {selectedCommodity.marketData?.timestamp ? 
                        new Date(selectedCommodity.marketData.timestamp).toLocaleString('de-DE') : 'N/A'}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Trading Actions entfernt - Buttons sind jetzt ganz oben */}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* AI Chat Component */}
      <AIChat 
        aiProvider={settings?.ai_provider || 'emergent'}
        aiModel={settings?.ai_model || 'gpt-5'}
      />

      {/* Trade Detail Modal - MOVED INSIDE COMPONENT */}
      <Dialog open={tradeDetailModalOpen} onOpenChange={setTradeDetailModalOpen}>
        <DialogContent className="bg-slate-900 text-white border-slate-700 max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-cyan-400">
              📊 Trade Einstellungen
            </DialogTitle>
          </DialogHeader>
          
          {selectedTrade && (
            <div className="space-y-6 py-4">
              {/* Trade Info */}
              <div className="bg-slate-800 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3 text-cyan-400">Trade Details</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Symbol:</span>
                    <span className="ml-2 font-semibold">{selectedTrade.commodity}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Typ:</span>
                    <span className="ml-2 font-semibold">{selectedTrade.type}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Entry:</span>
                    <span className="ml-2 font-semibold">${selectedTrade.entry_price?.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Aktuell:</span>
                    <span className="ml-2 font-semibold">${selectedTrade.price?.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Menge:</span>
                    <span className="ml-2 font-semibold">{selectedTrade.quantity} Lots</span>
                  </div>
                  <div>
                    <span className="text-slate-400">P&L:</span>
                    <span className={`ml-2 font-semibold ${(selectedTrade.profit_loss || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(selectedTrade.profit_loss || 0) >= 0 ? '+' : ''}{(selectedTrade.profit_loss || 0).toFixed(2)}€
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Ticket:</span>
                    <span className="ml-2 font-semibold">#{selectedTrade.mt5_ticket || selectedTrade.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Platform:</span>
                    <span className="ml-2 font-semibold">{selectedTrade.platform}</span>
                  </div>
                </div>
              </div>

              {/* Individual Settings */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-cyan-400">🎯 Individuelle Einstellungen</h3>
                <p className="text-sm text-slate-400">
                  Diese Einstellungen gelten <strong>nur für diesen Trade</strong> und überschreiben die globalen Settings.
                  Die KI überwacht diese Werte automatisch und schließt den Trade bei Erreichen.
                </p>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="trade-sl" className="text-slate-300 text-sm">
                      🛑 Stop Loss (Preis)
                    </Label>
                    <Input
                      id="trade-sl"
                      type="number"
                      step="0.01"
                      value={tradeSettings.stop_loss || ''}
                      onChange={(e) => setTradeSettings({...tradeSettings, stop_loss: parseFloat(e.target.value) || null})}
                      className="bg-slate-800 border-slate-700 text-white mt-1"
                      placeholder={selectedTrade.type === 'BUY' ? 'z.B. 3950.00' : 'z.B. 4150.00'}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedTrade.type === 'BUY' ? 'Unter Entry Preis' : 'Über Entry Preis'}
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="trade-tp" className="text-slate-300 text-sm">
                      🎯 Take Profit (Preis)
                    </Label>
                    <Input
                      id="trade-tp"
                      type="number"
                      step="0.01"
                      value={tradeSettings.take_profit || ''}
                      onChange={(e) => setTradeSettings({...tradeSettings, take_profit: parseFloat(e.target.value) || null})}
                      className="bg-slate-800 border-slate-700 text-white mt-1"
                      placeholder={selectedTrade.type === 'BUY' ? 'z.B. 4150.00' : 'z.B. 3950.00'}
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedTrade.type === 'BUY' ? 'Über Entry Preis' : 'Unter Entry Preis'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-800 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="trailing-stop" className="text-slate-300 cursor-pointer">
                        📈 Trailing Stop
                      </Label>
                      <p className="text-xs text-slate-500 mt-1">
                        Stop Loss folgt dem Gewinn automatisch
                      </p>
                    </div>
                    <Switch
                      id="trailing-stop"
                      checked={tradeSettings.trailing_stop || false}
                      onCheckedChange={(checked) => setTradeSettings({...tradeSettings, trailing_stop: checked})}
                    />
                  </div>

                  {tradeSettings.trailing_stop && (
                    <div className="mt-4">
                      <Label htmlFor="trailing-distance" className="text-slate-300 text-sm">
                        Abstand (Pips)
                      </Label>
                      <Input
                        id="trailing-distance"
                        type="number"
                        value={tradeSettings.trailing_stop_distance || 50}
                        onChange={(e) => setTradeSettings({...tradeSettings, trailing_stop_distance: parseInt(e.target.value) || 50})}
                        className="bg-slate-800 border-slate-700 text-white mt-1"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Empfohlen: 30-100 Pips je nach Volatilität
                      </p>
                    </div>
                  )}
                </div>

                <div>
                  <Label htmlFor="trade-strategy" className="text-slate-300 text-sm">
                    📋 Strategie-Typ
                  </Label>
                  <select
                    id="trade-strategy"
                    value={tradeSettings.strategy_type || 'swing'}
                    onChange={(e) => setTradeSettings({...tradeSettings, strategy_type: e.target.value})}
                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2 mt-1"
                  >
                    <option value="swing">📈 Swing Trading (länger)</option>
                    <option value="day">⚡ Day Trading (kurz)</option>
                    <option value="scalping">⚡🎯 Scalping (ultra-schnell)</option>
                    <option value="mean_reversion">📊 Mean Reversion (Mittelwert)</option>
                    <option value="momentum">🚀 Momentum Trading (Trend)</option>
                    <option value="breakout">💥 Breakout Trading (Ausbruch)</option>
                    <option value="grid">🔹 Grid Trading (Netz)</option>
                  </select>
                </div>

                <div>
                  <Label htmlFor="trade-notes" className="text-slate-300 text-sm">
                    📝 Notizen (optional)
                  </Label>
                  <textarea
                    id="trade-notes"
                    rows="3"
                    value={tradeSettings.notes || ''}
                    onChange={(e) => setTradeSettings({...tradeSettings, notes: e.target.value})}
                    className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-3 mt-1"
                    placeholder="Notizen zu diesem Trade..."
                  />
                </div>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <Button
                  onClick={handleSaveTradeSettings}
                  className="flex-1 bg-cyan-600 hover:bg-cyan-500"
                >
                  💾 Einstellungen speichern
                </Button>
                <Button
                  onClick={() => setTradeDetailModalOpen(false)}
                  variant="outline"
                  className="border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  Abbrechen
                </Button>
              </div>

              <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-3">
                <p className="text-xs text-amber-400 text-center">
                  ⚡ Die KI überwacht diese Einstellungen kontinuierlich und schließt den Trade automatisch bei SL/TP
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SettingsForm = ({ settings, onSave, commodities, balance }) => {
  // Initialize with defaults, then merge with settings only once
  const [formData, setFormData] = useState(() => {
    const defaults = {
      enabled_commodities: ['WTI_CRUDE'],
      rsi_oversold_threshold: 30,
      rsi_overbought_threshold: 70,
      macd_signal_threshold: 0,
      trend_following: true,
      min_confidence_score: 0.6,
      use_volume_confirmation: true,
      risk_per_trade_percent: 2.0,
      stop_loss_percent: 2.0,
      take_profit_percent: 4.0,
      // Dual Trading Strategy Defaults
      swing_trading_enabled: true,
      swing_min_confidence_score: 0.6,
      swing_stop_loss_percent: 2.0,
      swing_take_profit_percent: 4.0,
      swing_max_positions: 5,
      day_trading_enabled: false,
      day_min_confidence_score: 0.4,
      day_stop_loss_percent: 0.5,
      day_take_profit_percent: 0.8,
      day_max_positions: 10,
      scalping_enabled: false,
      scalping_min_confidence_score: 0.6,
      scalping_max_positions: 3
    };
    
    if (settings) {
      return { ...defaults, ...settings };
    }
    return defaults;
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleResetSettings = async () => {
    if (!window.confirm('Möchten Sie wirklich alle Einstellungen auf die Standardwerte zurücksetzen?')) {
      return;
    }

    try {
      const response = await axios.post(`${API}/settings/reset`);
      if (response.data.success) {
        // Update form with reset values
        setFormData(response.data.settings);
        alert('✅ Einstellungen wurden auf Standardwerte zurückgesetzt!');
        
        // Reload page to ensure all components get fresh data
        setTimeout(() => {
          window.location.reload();
        }, 1000);
      }
    } catch (error) {
      console.error('Fehler beim Zurücksetzen der Einstellungen:', error);
      alert('❌ Fehler beim Zurücksetzen der Einstellungen');
    }
  };

  const aiProviderModels = {
    emergent: ['gpt-5', 'gpt-4-turbo', 'gpt-4'],
    openai: ['gpt-5', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
    gemini: ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
    ollama: ['llama2', 'llama3', 'mistral', 'mixtral', 'codellama', 'phi', 'neural-chat', 'starling-lm', 'orca-mini']
  };

  const currentProvider = formData.ai_provider || 'emergent';
  const availableModels = aiProviderModels[currentProvider] || ['gpt-5'];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        {/* AI Analysis Section */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            KI-Analyse Einstellungen
          </h4>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="use_ai_analysis" className="text-base">KI-Analyse verwenden</Label>
            <Switch
              id="use_ai_analysis"
              checked={formData.use_ai_analysis !== false}
              onCheckedChange={(checked) => setFormData({ ...formData, use_ai_analysis: checked })}
              data-testid="ai-analysis-switch"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai_provider">KI Provider</Label>
            <select
              id="ai_provider"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={currentProvider}
              onChange={(e) => setFormData({ 
                ...formData, 
                ai_provider: e.target.value,
                ai_model: aiProviderModels[e.target.value][0] // Reset to first model of new provider
              })}
              data-testid="ai-provider-select"
            >
              <option value="emergent">Emergent LLM Key (Universal)</option>
              <option value="openai">OpenAI API</option>
              <option value="gemini">Google Gemini API</option>
              <option value="anthropic">Anthropic Claude API</option>
              <option value="ollama">Ollama (Lokal)</option>
            </select>
            <p className="text-xs text-slate-500">
              {currentProvider === 'emergent' && '✨ Emergent Universal Key - Funktioniert mit OpenAI, Gemini & Claude'}
              {currentProvider === 'openai' && '🔑 Eigene OpenAI API Key verwenden'}
              {currentProvider === 'gemini' && '🔑 Eigene Google Gemini API Key verwenden'}
              {currentProvider === 'anthropic' && '🔑 Eigene Anthropic API Key verwenden'}
              {currentProvider === 'ollama' && '🏠 Lokales LLM auf Ihrem Mac (Ollama erforderlich)'}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ai_model">KI Model</Label>
            <select
              id="ai_model"
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
              value={formData.ai_model || availableModels[0]}
              onChange={(e) => setFormData({ ...formData, ai_model: e.target.value })}
              data-testid="ai-model-select"
            >
              {availableModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          {/* API Key fields based on provider */}
          {currentProvider === 'openai' && (
            <div className="space-y-2">
              <Label htmlFor="openai_api_key">OpenAI API Key</Label>
              <Input
                id="openai_api_key"
                type="password"
                value={formData.openai_api_key || ''}
                onChange={(e) => setFormData({ ...formData, openai_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="sk-..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf platform.openai.com</p>
            </div>
          )}

          {currentProvider === 'gemini' && (
            <div className="space-y-2">
              <Label htmlFor="gemini_api_key">Google Gemini API Key</Label>
              <Input
                id="gemini_api_key"
                type="password"
                value={formData.gemini_api_key || ''}
                onChange={(e) => setFormData({ ...formData, gemini_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="AIza..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf aistudio.google.com</p>
            </div>
          )}

          {currentProvider === 'anthropic' && (
            <div className="space-y-2">
              <Label htmlFor="anthropic_api_key">Anthropic API Key</Label>
              <Input
                id="anthropic_api_key"
                type="password"
                value={formData.anthropic_api_key || ''}
                onChange={(e) => setFormData({ ...formData, anthropic_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="sk-ant-..."
              />
              <p className="text-xs text-slate-500">Holen Sie sich Ihren API Key auf console.anthropic.com</p>
            </div>
          )}

          {currentProvider === 'ollama' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ollama_base_url">Ollama Server URL</Label>
                <Input
                  id="ollama_base_url"
                  type="text"
                  value={formData.ollama_base_url || 'http://localhost:11434'}
                  onChange={(e) => setFormData({ ...formData, ollama_base_url: e.target.value })}
                  className="bg-slate-800 border-slate-700"
                  placeholder="http://localhost:11434"
                />
                <p className="text-xs text-slate-500">Standard Ollama URL ist http://localhost:11434</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="ollama_model">Ollama Model</Label>
                <select
                  id="ollama_model"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-white"
                  value={formData.ollama_model || 'llama2'}
                  onChange={(e) => {
                    setFormData({ 
                      ...formData, 
                      ollama_model: e.target.value,
                      ai_model: e.target.value 
                    });
                  }}
                  data-testid="ollama-model-select"
                >
                  {aiProviderModels.ollama.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  Stellen Sie sicher, dass das Modell mit &lsquo;ollama pull {formData.ollama_model || 'llama2'}&rsquo; installiert ist
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Triple Trading Strategy Section - NEU: Scalping hinzugefügt! */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-400" />
            Trading Strategien
          </h4>
          <p className="text-sm text-amber-400 bg-amber-900/20 p-3 rounded border border-amber-700/30">
            ⚠️ Alle Strategien zusammen nutzen maximal 20% der Balance <strong>PRO Plattform</strong>
          </p>
          
          {/* Swing Trading */}
          <div className="space-y-3 p-4 bg-green-900/10 rounded-lg border border-green-700/30">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-green-400 font-semibold text-base">📈 Swing Trading (Langfristig)</Label>
                <p className="text-xs text-slate-400 mt-1">Größere Positionen, höhere Confidence</p>
              </div>
              <Switch
                checked={formData.swing_trading_enabled !== false}
                onCheckedChange={(checked) => setFormData({ ...formData, swing_trading_enabled: checked })}
              />
            </div>
            {formData.swing_trading_enabled !== false && (
              <div className="grid grid-cols-2 gap-3 mt-3 pl-4 border-l-2 border-green-700/30">
                <div>
                  <Label className="text-xs text-slate-400">Min. Confidence</Label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={formData.swing_min_confidence_score || 0.6}
                    onChange={(e) => setFormData({ ...formData, swing_min_confidence_score: parseFloat(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 0.6 (60%)</p>
                </div>
                <div>
                  <Label className="text-xs text-slate-400">Max Positionen</Label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={formData.swing_max_positions || 5}
                    onChange={(e) => setFormData({ ...formData, swing_max_positions: parseInt(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 5</p>
                </div>
                {/* TP/SL Modus Toggle */}
                <div className="col-span-2 p-3 bg-slate-800/30 rounded border border-slate-700">
                  <Label className="text-xs text-slate-300 font-semibold mb-2 block">TP/SL Eingabe-Modus:</Label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, swing_tp_sl_mode: 'percent' })}
                      className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                        (formData.swing_tp_sl_mode || 'percent') === 'percent'
                          ? 'bg-purple-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      📊 Prozent (%)
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, swing_tp_sl_mode: 'euro' })}
                      className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                        formData.swing_tp_sl_mode === 'euro'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      💶 Euro (€)
                    </button>
                  </div>
                </div>

                {/* Bedingte Felder basierend auf Modus */}
                {(formData.swing_tp_sl_mode || 'percent') === 'percent' ? (
                  <>
                    <div>
                      <Label className="text-xs text-slate-400">Stop Loss %</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="10"
                        value={formData.swing_stop_loss_percent || 2.0}
                        onChange={(e) => setFormData({ ...formData, swing_stop_loss_percent: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Default: 2.0%</p>
                    </div>
                    <div>
                      <Label className="text-xs text-slate-400">Take Profit %</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="20"
                        value={formData.swing_take_profit_percent || 4.0}
                        onChange={(e) => setFormData({ ...formData, swing_take_profit_percent: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Default: 4.0%</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <Label className="text-xs text-slate-400">Stop Loss €</Label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="500"
                        value={formData.swing_stop_loss_euro || 20.0}
                        onChange={(e) => setFormData({ ...formData, swing_stop_loss_euro: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Schließe bei €20 Verlust</p>
                    </div>
                    <div>
                      <Label className="text-xs text-slate-400">Take Profit €</Label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="1000"
                        value={formData.swing_take_profit_euro || 50.0}
                        onChange={(e) => setFormData({ ...formData, swing_take_profit_euro: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Schließe bei €50 Gewinn</p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Day Trading */}
          <div className="space-y-3 p-4 bg-orange-900/10 rounded-lg border border-orange-700/30">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-orange-400 font-semibold text-base">⚡ Day Trading (Kurzfristig)</Label>
                <p className="text-xs text-slate-400 mt-1">Kleinere Positionen, niedrigere Confidence, Max 2h Haltezeit</p>
              </div>
              <Switch
                checked={formData.day_trading_enabled === true}
                onCheckedChange={(checked) => setFormData({ ...formData, day_trading_enabled: checked })}
              />
            </div>
            {formData.day_trading_enabled === true && (
              <div className="grid grid-cols-2 gap-3 mt-3 pl-4 border-l-2 border-orange-700/30">
                <div>
                  <Label className="text-xs text-slate-400">Min. Confidence</Label>
                  <Input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={formData.day_min_confidence_score || 0.4}
                    onChange={(e) => setFormData({ ...formData, day_min_confidence_score: parseFloat(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 0.4 (40%)</p>
                </div>
                <div>
                  <Label className="text-xs text-slate-400">Max Positionen</Label>
                  <Input
                    type="number"
                    min="1"
                    max="30"
                    value={formData.day_max_positions || 10}
                    onChange={(e) => setFormData({ ...formData, day_max_positions: parseInt(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 10</p>
                </div>
                {/* TP/SL Modus Toggle */}
                <div className="col-span-2 p-3 bg-slate-800/30 rounded border border-slate-700">
                  <Label className="text-xs text-slate-300 font-semibold mb-2 block">TP/SL Eingabe-Modus:</Label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, day_tp_sl_mode: 'percent' })}
                      className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                        (formData.day_tp_sl_mode || 'percent') === 'percent'
                          ? 'bg-orange-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      📊 Prozent (%)
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, day_tp_sl_mode: 'euro' })}
                      className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${
                        formData.day_tp_sl_mode === 'euro'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      💶 Euro (€)
                    </button>
                  </div>
                </div>

                {/* Bedingte Felder basierend auf Modus */}
                {(formData.day_tp_sl_mode || 'percent') === 'percent' ? (
                  <>
                    <div>
                      <Label className="text-xs text-slate-400">Stop Loss %</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="5"
                        value={formData.day_stop_loss_percent || 1.5}
                        onChange={(e) => setFormData({ ...formData, day_stop_loss_percent: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Default: 1.5%</p>
                    </div>
                    <div>
                      <Label className="text-xs text-slate-400">Take Profit %</Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0.1"
                        max="5"
                        value={formData.day_take_profit_percent || 2.5}
                        onChange={(e) => setFormData({ ...formData, day_take_profit_percent: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Default: 2.5%</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <Label className="text-xs text-slate-400">Stop Loss €</Label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="200"
                        value={formData.day_stop_loss_euro || 15.0}
                        onChange={(e) => setFormData({ ...formData, day_stop_loss_euro: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Schließe bei €15 Verlust</p>
                    </div>
                    <div>
                      <Label className="text-xs text-slate-400">Take Profit €</Label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="500"
                        value={formData.day_take_profit_euro || 30.0}
                        onChange={(e) => setFormData({ ...formData, day_take_profit_euro: parseFloat(e.target.value) })}
                        className="bg-slate-800 border-slate-700 text-sm"
                      />
                      <p className="text-xs text-slate-500 mt-1">Schließe bei €30 Gewinn</p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Platform Credentials */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg">Plattform-Zugangsdaten</h4>
          
          {/* MT5 Libertex */}
          <div className="space-y-2 p-3 bg-blue-900/10 rounded-lg border border-blue-700/30">
            <Label className="text-blue-400 font-semibold">🔷 MT5 Libertex</Label>
            <div className="space-y-2">
              <Label htmlFor="mt5_libertex_account_id" className="text-sm">Account ID (MetaAPI)</Label>
              <Input
                id="mt5_libertex_account_id"
                type="text"
                value={formData.mt5_libertex_account_id || ''}
                onChange={(e) => setFormData({ ...formData, mt5_libertex_account_id: e.target.value })}
                className="bg-slate-800 border-slate-700 font-mono text-xs"
                placeholder="142e1085-f20b-437e-93c7-b87a0e639a30"
              />
              <p className="text-xs text-slate-500">MetaAPI Account UUID für Libertex MT5</p>
            </div>
          </div>

          {/* MT5 ICMarkets */}
          <div className="space-y-2 p-3 bg-purple-900/10 rounded-lg border border-purple-700/30">
            <Label className="text-purple-400 font-semibold">🟣 MT5 ICMarkets</Label>
            <div className="space-y-2">
              <Label htmlFor="mt5_icmarkets_account_id" className="text-sm">Account ID (MetaAPI)</Label>
              <Input
                id="mt5_icmarkets_account_id"
                type="text"
                value={formData.mt5_icmarkets_account_id || ''}
                onChange={(e) => setFormData({ ...formData, mt5_icmarkets_account_id: e.target.value })}
                className="bg-slate-800 border-slate-700 font-mono text-xs"
                placeholder="d2605e89-7bc2-4144-9f7c-951edd596c39"
              />
              <p className="text-xs text-slate-500">MetaAPI Account UUID für ICMarkets MT5</p>
            </div>
          </div>

          {/* MT5 Libertex REAL - wenn verfügbar */}
          <div className="space-y-2 p-3 bg-amber-900/10 rounded-lg border border-amber-700/30">
            <Label className="text-amber-400 font-semibold">💰 MT5 Libertex REAL (Echtgeld)</Label>
            <div className="space-y-2">
              <Label htmlFor="mt5_libertex_real_account_id" className="text-sm">Account ID (MetaAPI)</Label>
              <Input
                id="mt5_libertex_real_account_id"
                type="text"
                value={formData.mt5_libertex_real_account_id || ''}
                onChange={(e) => setFormData({ ...formData, mt5_libertex_real_account_id: e.target.value })}
                className="bg-slate-800 border-slate-700 font-mono text-xs"
                placeholder="Nach manuellem Hinzufügen bei MetaAPI"
                disabled={true}
              />
              <p className="text-xs text-amber-400">⚠️ Real Account muss manuell bei MetaAPI hinzugefügt werden</p>
            </div>
          </div>
        </div>

        {/* Trading Settings */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg">Trading Einstellungen</h4>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="auto_trading" className="text-base">Auto-Trading aktivieren</Label>
            <Switch
              id="auto_trading"
              checked={formData.auto_trading || false}
              onCheckedChange={(checked) => setFormData({ ...formData, auto_trading: checked })}
              data-testid="auto-trading-switch"
            />
          </div>

          <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-cyan-700/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="text-3xl">⚡</div>
              <div className="space-y-2 flex-1">
                <h5 className="font-semibold text-cyan-400">Multi-Platform Trading</h5>
                <p className="text-sm text-slate-300">
                  Alle aktivierten Plattformen (mit ✓ Häkchen bei Balance-Cards) erhalten <span className="text-cyan-400 font-bold">gleichzeitig</span> Trades!
                </p>
                <div className="mt-3 p-3 bg-slate-800/50 rounded border border-slate-700">
                  <p className="text-xs text-slate-400 mb-2">📊 Aktuell aktive Plattformen:</p>
                  <div className="flex flex-wrap gap-2">
                    {(formData.active_platforms || []).map(platform => (
                      <span key={platform} className="px-2 py-1 bg-cyan-900/30 text-cyan-300 text-xs rounded border border-cyan-700/50">
                        {platform}
                      </span>
                    ))}
                    {(!formData.active_platforms || formData.active_platforms.length === 0) && (
                      <span className="text-xs text-slate-500 italic">Keine Plattform aktiv</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* DEPRECATED: Alte Stop Loss / Take Profit Felder entfernt - jetzt in Dual Trading Strategy */}

          {/* Trailing Stop Settings */}
          <div className="space-y-4 mt-6">
            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <div className="flex-1">
                <Label htmlFor="trailing_stop" className="text-base font-semibold">Trailing Stop aktivieren</Label>
                <p className="text-sm text-slate-400 mt-1">
                  Stop Loss folgt automatisch dem Preis und sichert Gewinne ab
                </p>
              </div>
              <Switch
                id="trailing_stop"
                checked={formData.use_trailing_stop || false}
                onCheckedChange={(checked) => setFormData({ ...formData, use_trailing_stop: checked })}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>

            {formData.use_trailing_stop && (
              <div className="space-y-2 pl-4">
                <Label htmlFor="trailing_distance">Trailing Stop Distanz (%)</Label>
                <Input
                  id="trailing_distance"
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={formData.trailing_stop_distance ?? 1.5}
                  onChange={(e) => {
                    const val = e.target.value === '' ? 0 : parseFloat(e.target.value);
                    setFormData({ ...formData, trailing_stop_distance: val });
                  }}
                  className="bg-slate-800 border-slate-700"
                  placeholder="z.B. 1.5"
                />
                <p className="text-xs text-slate-500">
                  Stop Loss hält {formData.trailing_stop_distance ?? 1.5}% Abstand zum aktuellen Preis
                </p>
              </div>
            )}
          </div>

          {/* KI Trading Strategie-Einstellungen */}
          <div className="space-y-4 mt-6 p-4 bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-lg border-2 border-purple-500/30">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-purple-300">🤖 KI Trading Strategie</h3>
              <Button
                type="button"
                onClick={handleResetSettings}
                variant="outline"
                size="sm"
                className="border-purple-500 text-purple-300 hover:bg-purple-500/20"
              >
                🔄 Zurücksetzen
              </Button>
            </div>
            <p className="text-sm text-slate-400">
              Passen Sie die KI-Parameter an, um die Trading-Strategie zu optimieren
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="rsi_oversold">RSI Kaufsignal (Oversold)</Label>
                <Input
                  id="rsi_oversold"
                  type="number"
                  step="1"
                  min="0"
                  max="50"
                  value={formData.rsi_oversold_threshold ?? 30}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '') {
                      setFormData({ ...formData, rsi_oversold_threshold: '' });
                    } else {
                      const num = parseFloat(val);
                      setFormData({ ...formData, rsi_oversold_threshold: isNaN(num) ? 30 : num });
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                      setFormData({ ...formData, rsi_oversold_threshold: 30 });
                    }
                  }}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-500">Standard: 30 (niedrigere Werte = konservativer)</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="rsi_overbought">RSI Verkaufssignal (Overbought)</Label>
                <Input
                  id="rsi_overbought"
                  type="number"
                  step="1"
                  min="50"
                  max="100"
                  value={formData.rsi_overbought_threshold ?? 70}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '') {
                      setFormData({ ...formData, rsi_overbought_threshold: '' });
                    } else {
                      const num = parseFloat(val);
                      setFormData({ ...formData, rsi_overbought_threshold: isNaN(num) ? 70 : num });
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                      setFormData({ ...formData, rsi_overbought_threshold: 70 });
                    }
                  }}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-500">Standard: 70 (höhere Werte = konservativer)</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="min_confidence">Minimale Konfidenz für Auto-Trading</Label>
              <Input
                id="min_confidence"
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={formData.min_confidence_score ?? 0.6}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '') {
                    setFormData({ ...formData, min_confidence_score: '' });
                  } else {
                    const num = parseFloat(val);
                    setFormData({ ...formData, min_confidence_score: isNaN(num) ? 0.6 : num });
                  }
                }}
                onBlur={(e) => {
                  if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                    setFormData({ ...formData, min_confidence_score: 0.6 });
                  }
                }}
                className="bg-slate-800 border-slate-700"
              />
              <p className="text-xs text-slate-500">Standard: 0.6 (60% Konfidenz) - Höhere Werte = weniger aber sicherere Trades</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="risk_per_trade">Risiko pro Trade (% der Balance)</Label>
              <Input
                id="risk_per_trade"
                type="number"
                step="0.1"
                min="0.5"
                max="10"
                value={formData.risk_per_trade_percent ?? 2.0}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === '') {
                    setFormData({ ...formData, risk_per_trade_percent: '' });
                  } else {
                    const num = parseFloat(val);
                    setFormData({ ...formData, risk_per_trade_percent: isNaN(num) ? 2.0 : num });
                  }
                }}
                onBlur={(e) => {
                  if (e.target.value === '' || isNaN(parseFloat(e.target.value))) {
                    setFormData({ ...formData, risk_per_trade_percent: 2.0 });
                  }
                }}
                className="bg-slate-800 border-slate-700"
              />
              <p className="text-xs text-slate-500">Standard: 2% - Empfohlen: 1-3% für konservatives Risikomanagement</p>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded border border-slate-700">
              <div>
                <Label htmlFor="trend_following" className="font-semibold">Trend-Following aktivieren</Label>
                <p className="text-xs text-slate-400">Kaufe nur bei Aufwärtstrends, verkaufe bei Abwärtstrends</p>
              </div>
              <Switch
                id="trend_following"
                checked={formData.trend_following ?? true}
                onCheckedChange={(checked) => setFormData({ ...formData, trend_following: checked })}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded border border-slate-700">
              <div>
                <Label htmlFor="volume_confirmation" className="font-semibold">Volumen-Bestätigung</Label>
                <p className="text-xs text-slate-400">Verwende Handelsvolumen zur Signal-Bestätigung</p>
              </div>
              <Switch
                id="volume_confirmation"
                checked={formData.use_volume_confirmation ?? true}
                onCheckedChange={(checked) => setFormData({ ...formData, use_volume_confirmation: checked })}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="max_trades">Max. Trades pro Stunde</Label>
            <Input
              id="max_trades"
              type="number"
              min="1"
              value={formData.max_trades_per_hour ?? 3}
              onChange={(e) => {
                const val = e.target.value;
                setFormData({ ...formData, max_trades_per_hour: val === '' ? '' : parseInt(val) || 3 });
              }}
              onBlur={(e) => {
                // Set default value on blur if empty
                if (e.target.value === '') {
                  setFormData({ ...formData, max_trades_per_hour: 3 });
                }
              }}
              className="bg-slate-800 border-slate-700"
              data-testid="max-trades-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="position_size">Positionsgröße</Label>
            <Input
              id="position_size"
              type="number"
              step="0.1"
              value={formData.position_size || 1.0}
              onChange={(e) => setFormData({ ...formData, position_size: parseFloat(e.target.value) })}
              className="bg-slate-800 border-slate-700"
              data-testid="position-size-input"
            />
          </div>
        </div>

        {/* Commodity Selection */}
        <div className="space-y-4 mt-6">
          <h4 className="font-semibold text-lg">Rohstoff-Auswahl</h4>
          <p className="text-sm text-slate-400">Wählen Sie die Rohstoffe aus, die gehandelt werden sollen:</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(commodities).map(([id, commodity]) => (
              <div key={id} className="flex items-center space-x-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <input
                  type="checkbox"
                  id={`commodity_${id}`}
                  checked={formData.enabled_commodities?.includes(id) || false}
                  onChange={(e) => {
                    const enabled = formData.enabled_commodities || ['WTI_CRUDE'];
                    if (e.target.checked) {
                      setFormData({ ...formData, enabled_commodities: [...enabled, id] });
                    } else {
                      setFormData({ ...formData, enabled_commodities: enabled.filter(c => c !== id) });
                    }
                  }}
                  className="w-4 h-4 text-emerald-600 bg-slate-700 border-slate-600 rounded focus:ring-emerald-500"
                />
                <label htmlFor={`commodity_${id}`} className="flex-1 cursor-pointer">
                  <div className="font-medium text-slate-200">{commodity.name}</div>
                  <div className="text-xs text-slate-500">{commodity.category} • {commodity.unit}</div>
                </label>
              </div>
            ))}
          </div>
          
          <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">Portfolio-Risiko</span>
            </div>
            <p className="text-sm text-slate-400">
              Max. 20% des Gesamtguthabens ({(balance * 0.2).toFixed(2)} EUR) für alle offenen Positionen zusammen
            </p>
          </div>
        </div>

        {/* MT5 Settings */}
        {formData.mode === 'MT5' && (
          <div className="space-y-4 mt-6">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <span className="text-2xl">🔷</span>
              MetaTrader 5 Credentials
            </h4>
            <div className="space-y-2">
              <Label htmlFor="mt5_login">MT5 Login</Label>
              <Input
                id="mt5_login"
                type="text"
                value={formData.mt5_login || ''}
                onChange={(e) => setFormData({ ...formData, mt5_login: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Account Login"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mt5_password">MT5 Passwort</Label>
              <Input
                id="mt5_password"
                type="password"
                value={formData.mt5_password || ''}
                onChange={(e) => setFormData({ ...formData, mt5_password: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Account Passwort"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mt5_server">MT5 Server</Label>
              <Input
                id="mt5_server"
                type="text"
                value={formData.mt5_server || ''}
                onChange={(e) => setFormData({ ...formData, mt5_server: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="MT5 Server Adresse"
              />
            </div>
          </div>
        )}

        {/* Bitpanda Settings */}
        {formData.mode === 'BITPANDA' && (
          <div className="space-y-4 mt-6">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <span className="text-2xl">🟢</span>
              Bitpanda Pro Credentials
            </h4>
            <div className="space-y-2">
              <Label htmlFor="bitpanda_email">Bitpanda Email</Label>
              <Input
                id="bitpanda_email"
                type="email"
                value={formData.bitpanda_email || ''}
                onChange={(e) => setFormData({ ...formData, bitpanda_email: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="ihre.email@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bitpanda_api_key">Bitpanda API Key</Label>
              <Input
                id="bitpanda_api_key"
                type="password"
                value={formData.bitpanda_api_key || ''}
                onChange={(e) => setFormData({ ...formData, bitpanda_api_key: e.target.value })}
                className="bg-slate-800 border-slate-700"
                placeholder="Ihr Bitpanda API Key"
              />
              <p className="text-xs text-slate-500">
                Erstellen Sie einen API Key in Ihrem Bitpanda Pro Account unter Einstellungen → API Keys
              </p>
            </div>
          </div>
        )}

        {/* Market Trading Hours Section - ASSET SPECIFIC */}
        <MarketHoursManager formData={formData} setFormData={setFormData} />
      </div>

      <Button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-500" data-testid="save-settings-button">
        Einstellungen speichern
      </Button>
    </form>
  );
};

// Market Hours Manager Component - Asset-specific trading hours
const MarketHoursManager = ({ formData, setFormData }) => {
  const [marketHours, setMarketHours] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchMarketHours();
  }, []);

  const fetchMarketHours = async () => {
    try {
      const response = await axios.get(`${API}/market/hours/all`);
      if (response.data.success) {
        setMarketHours(response.data.market_hours);
      }
    } catch (error) {
      console.error('Error fetching market hours:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateAssetHours = (assetId, field, value) => {
    setMarketHours(prev => ({
      ...prev,
      [assetId]: {
        ...prev[assetId],
        [field]: value
      }
    }));
  };

  const toggleDay = (assetId, day) => {
    const currentDays = marketHours[assetId]?.days || [];
    const newDays = currentDays.includes(day)
      ? currentDays.filter(d => d !== day)
      : [...currentDays, day].sort();
    
    updateAssetHours(assetId, 'days', newDays);
  };

  const applyPreset = (assetId, preset) => {
    const presets = {
      '24_7': {
        enabled: true,
        days: [0, 1, 2, 3, 4, 5, 6],
        open_time: '00:00',
        close_time: '23:59',
        is_24_7: true,
        is_24_5: false,
        description: '24/7 - Immer geöffnet'
      },
      '24_5': {
        enabled: true,
        days: [0, 1, 2, 3, 4],
        open_time: '22:00',
        close_time: '21:00',
        is_24_5: true,
        is_24_7: false,
        description: '24/5 - Sonntag 22:00 bis Freitag 21:00 UTC'
      },
      'boerse': {
        enabled: true,
        days: [0, 1, 2, 3, 4],
        open_time: '08:30',
        close_time: '20:00',
        is_24_5: false,
        is_24_7: false,
        description: 'Börsenzeiten Mo-Fr 08:30-20:00 UTC'
      }
    };

    setMarketHours(prev => ({
      ...prev,
      [assetId]: {
        ...prev[assetId],
        ...presets[preset]
      }
    }));
  };

  const saveAllMarketHours = async () => {
    setSaving(true);
    try {
      // Save each asset's market hours
      const promises = Object.keys(marketHours).map(assetId =>
        axios.post(`${API}/market/hours/update`, {
          commodity_id: assetId,
          hours_config: marketHours[assetId]
        })
      );
      
      await Promise.all(promises);
      toast.success('Handelszeiten erfolgreich gespeichert!');
    } catch (error) {
      console.error('Error saving market hours:', error);
      toast.error('Fehler beim Speichern der Handelszeiten');
    } finally {
      setSaving(false);
    }
  };

  // Group assets by category
  const groupedAssets = Object.entries(marketHours).reduce((acc, [assetId, config]) => {
    const category = config.commodity_category || 'Andere';
    if (!acc[category]) acc[category] = [];
    acc[category].push({ id: assetId, ...config });
    return acc;
  }, {});

  const dayNames = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  if (loading) {
    return <div className="text-center text-slate-400 py-4">Lade Handelszeiten...</div>;
  }

  return (
    <div className="space-y-4 pb-4 border-b border-slate-700 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <span className="text-cyan-400">Handelszeiten (Asset-spezifisch)</span>
          </h4>
          <p className="text-sm text-slate-400 mt-1">
            Legen Sie für jedes Asset individuelle Handelszeiten fest.
          </p>
        </div>
        <Button 
          onClick={saveAllMarketHours} 
          disabled={saving}
          className="bg-green-600 hover:bg-green-500"
          size="sm"
        >
          {saving ? 'Speichert...' : 'Alle Speichern'}
        </Button>
      </div>

      <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded border border-slate-700">
        <div>
          <Label className="text-sm font-semibold">Handelszeiten-System aktivieren</Label>
          <p className="text-xs text-slate-400 mt-1">
            Bot respektiert die definierten Zeiten für jedes Asset
          </p>
        </div>
        <Switch
          checked={formData.respect_market_hours !== false}
          onCheckedChange={(checked) => setFormData({ ...formData, respect_market_hours: checked })}
        />
      </div>

      {(formData.respect_market_hours !== false) && (
        <div className="space-y-6 mt-4">
          {Object.entries(groupedAssets).map(([category, assets]) => (
            <div key={category} className="space-y-3">
              <h5 className="font-semibold text-md text-cyan-300 flex items-center gap-2 border-b border-slate-700 pb-2">
                <span>{category}</span>
                <span className="text-xs text-slate-500">({assets.length})</span>
              </h5>
              
              {assets.map(asset => (
                <div key={asset.id} className="p-4 bg-slate-800/30 rounded border border-slate-700/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-sm font-semibold text-slate-200">{asset.commodity_name || asset.id}</Label>
                      <p className="text-xs text-slate-400">{asset.id}</p>
                    </div>
                    <Switch
                      checked={asset.enabled !== false}
                      onCheckedChange={(checked) => updateAssetHours(asset.id, 'enabled', checked)}
                    />
                  </div>

                  {asset.enabled !== false && (
                    <>
                      {/* Preset Buttons */}
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, '24_7')}
                          className="px-3 py-1 text-xs rounded bg-purple-600/20 hover:bg-purple-600/40 text-purple-300 border border-purple-600/50"
                        >
                          24/7
                        </button>
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, '24_5')}
                          className="px-3 py-1 text-xs rounded bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-600/50"
                        >
                          24/5
                        </button>
                        <button
                          type="button"
                          onClick={() => applyPreset(asset.id, 'boerse')}
                          className="px-3 py-1 text-xs rounded bg-orange-600/20 hover:bg-orange-600/40 text-orange-300 border border-orange-600/50"
                        >
                          Börse (08:30-20:00)
                        </button>
                      </div>

                      {/* Weekdays */}
                      <div>
                        <Label className="text-xs text-slate-400 mb-2 block">Handelstage:</Label>
                        <div className="flex gap-2">
                          {dayNames.map((day, index) => {
                            const isActive = asset.days?.includes(index);
                            return (
                              <button
                                key={index}
                                type="button"
                                onClick={() => toggleDay(asset.id, index)}
                                className={`px-3 py-1 text-xs rounded transition-colors ${
                                  isActive
                                    ? 'bg-green-600 text-white'
                                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                                }`}
                              >
                                {day}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Time Inputs */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-xs text-slate-400">Öffnungszeit (UTC)</Label>
                          <Input
                            type="time"
                            value={asset.open_time || '00:00'}
                            onChange={(e) => updateAssetHours(asset.id, 'open_time', e.target.value)}
                            className="bg-slate-800 border-slate-700 text-sm"
                          />
                        </div>
                        <div>
                          <Label className="text-xs text-slate-400">Schließzeit (UTC)</Label>
                          <Input
                            type="time"
                            value={asset.close_time || '23:59'}
                            onChange={(e) => updateAssetHours(asset.id, 'close_time', e.target.value)}
                            className="bg-slate-800 border-slate-700 text-sm"
                          />
                        </div>
                      </div>

                      {/* Description */}
                      <div className="text-xs text-slate-500 italic">
                        {asset.description}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <div className="p-3 bg-blue-900/20 border border-blue-700/50 rounded">
        <p className="text-xs text-blue-300 flex items-center gap-2">
          <span>ℹ️</span>
          <span>
            <strong>Hinweis:</strong> Alle Zeiten in UTC. Der AI Bot öffnet keine neuen Trades außerhalb der definierten Zeiten.
            Änderungen werden erst nach "Alle Speichern" aktiv.
          </span>
        </p>
      </div>
    </div>
  );
};

export default Dashboard;