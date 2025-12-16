import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, BarChart3, Settings, RefreshCw, Play, Pause, Zap, ZapOff, AlertCircle, ChevronLeft, ChevronRight, LineChart, X } from 'lucide-react';
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL}/api`;

// Debug: Log the backend URL being used
console.log('🔧 Backend URL:', BACKEND_URL);
console.log('🔧 API URL:', API);

// Configure axios defaults with timeout
axios.defaults.timeout = 10000; // 10 second timeout for all requests

const Dashboard = () => {
  const [marketData, setMarketData] = useState(null);
  const [allMarkets, setAllMarkets] = useState({});  // All commodity markets
  const [commodities, setCommodities] = useState({}); // Commodity definitions
  const [currentCommodityIndex, setCurrentCommodityIndex] = useState(0); // For carousel
  const [historicalData, setHistoricalData] = useState([]);
  const [selectedCommodity, setSelectedCommodity] = useState(null); // For chart modal
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [settings, setSettings] = useState(null);
  const [balance, setBalance] = useState(10000); // Simulated balance
  const [mt5Account, setMt5Account] = useState(null); // Real MT5 account data (ICMarkets)
  const [mt5Connected, setMt5Connected] = useState(false);
  const [mt5LibertexAccount, setMt5LibertexAccount] = useState(null); // Libertex account
  const [mt5LibertexConnected, setMt5LibertexConnected] = useState(false);
  const [bitpandaAccount, setBitpandaAccount] = useState(null); // Bitpanda account
  const [bitpandaConnected, setBitpandaConnected] = useState(false);
  const [totalExposure, setTotalExposure] = useState(0); // Total exposure for 20% limit
  const [libertexExposure, setLibertexExposure] = useState(0); // Libertex platform exposure
  const [icmarketsExposure, setIcmarketsExposure] = useState(0); // ICMarkets platform exposure
  const [bitpandaExposure, setBitpandaExposure] = useState(0); // Bitpanda platform exposure
  const [gpt5Active, setGpt5Active] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [aiProcessing, setAiProcessing] = useState(false);
  const [chartTimeframe, setChartTimeframe] = useState('1m'); // Default to 1m for live ticker
  const [chartPeriod, setChartPeriod] = useState('2h'); // Default to 2 hours for live ticker
  const [chartModalData, setChartModalData] = useState([]);

  useEffect(() => {
    fetchAllData();
    
    // Live ticker - refresh market data every 10 seconds
    const liveInterval = setInterval(() => {
      if (autoRefresh) {
        fetchAllMarkets(); // Fetch all commodity markets
        refreshMarketData(); // This will trigger backend to fetch new data
        fetchTrades();
        fetchStats();
        updateBalance();
        // Fetch account data for all platforms
        fetchAllPlatformData();
      }
    }, 10000);  // Every 10 seconds

    return () => clearInterval(liveInterval);
  }, [autoRefresh, settings?.active_platforms]);

  // Load account data when settings change or component mounts
  useEffect(() => {
    console.log('🔍 Settings loaded:', settings);
    // Always fetch platform data using the efficient status endpoint
    console.log('🔍 Fetching all platform data from status endpoint');
    fetchAllPlatformData();
  }, [settings?.active_platforms]);

  // Load OHLCV data for selected commodity in modal with timeframe
  useEffect(() => {
    if (chartModalOpen && selectedCommodity) {
      const loadChartData = async () => {
        try {
          console.log('Loading chart data for:', selectedCommodity.id, chartTimeframe, chartPeriod);
          
          // Try normal endpoint first
          try {
            const response = await axios.get(
              `${API}/market/ohlcv/${selectedCommodity.id}?timeframe=${chartTimeframe}&period=${chartPeriod}`
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
            `${API}/market/ohlcv-simple/${selectedCommodity.id}?timeframe=${chartTimeframe}&period=${chartPeriod}`
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
  }, [chartModalOpen, selectedCommodity, chartTimeframe, chartPeriod]);

  const fetchAllData = async () => {
    setLoading(true);
    
    // Set a maximum timeout for loading - force stop after 5 seconds
    const maxLoadingTimeout = setTimeout(() => {
      console.warn('Loading timeout reached, forcing UI to display');
      setLoading(false);
    }, 5000);
    
    try {
      // First fetch settings and wait for it
      await fetchSettings().catch(err => console.error('Settings fetch error:', err));
      
      // Run all fetches with individual error handling
      await Promise.all([
        fetchCommodities().catch(err => console.error('Commodities fetch error:', err)),
        fetchAllMarkets().catch(err => console.error('Markets fetch error:', err)),
        refreshMarketData().catch(err => console.error('Market refresh error:', err)),
        fetchHistoricalData().catch(err => console.error('Historical data fetch error:', err)),
        fetchTrades().catch(err => console.error('Trades fetch error:', err)),
        fetchStats().catch(err => console.error('Stats fetch error:', err))
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
        if (settings.active_platforms.includes('MT5_LIBERTEX')) {
          promises.push(fetchMT5LibertexAccount().catch(err => console.error('MT5 Libertex error:', err)));
        }
        if (settings.active_platforms.includes('MT5_ICMARKETS')) {
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
      // Backend returns array directly, convert to object keyed by id
      const commoditiesArray = response.data || [];
      const commoditiesObject = {};
      commoditiesArray.forEach(commodity => {
        commoditiesObject[commodity.id] = commodity;
      });
      setCommodities(commoditiesObject);
      console.log(`✅ Loaded ${commoditiesArray.length} commodities:`, Object.keys(commoditiesObject));
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
    // Initial fetch
    fetchLiveTicks();
    
    // Set up interval for live updates
    const liveUpdateInterval = setInterval(() => {
      fetchLiveTicks();
    }, 5000); // Update every 5 seconds
    
    // Cleanup on unmount
    return () => clearInterval(liveUpdateInterval);
  }, []);


  
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

  const fetchTrades = async () => {
    try {
      // Der neue /trades/list Endpoint gibt bereits ALLE Trades zurück:
      // - Offene Positionen DIREKT von MT5 (live sync)
      // - Geschlossene Trades aus DB
      // Wir brauchen KEINE separaten /platforms/.../positions Calls mehr!
      
      const response = await axios.get(`${API}/trades/list`);
      const allTrades = response.data.trades || [];
      
      console.log(`✅ Fetched ${allTrades.length} trades from unified endpoint`);
      console.log('📊 Trades data:', allTrades);
      console.log('📊 Open trades:', allTrades.filter(t => t.status === 'OPEN'));
      console.log('📊 Closed trades:', allTrades.filter(t => t.status === 'CLOSED'));
      
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
      
      // Total exposure (all platforms)
      const totalExp = openTrades.reduce((sum, trade) => {
        return sum + (trade.entry_price * trade.quantity);
      }, 0);
      setTotalExposure(totalExp);
      
      // Libertex exposure
      const libertexExp = openTrades
        .filter(t => t.platform === 'MT5_LIBERTEX' || t.mode === 'MT5_LIBERTEX')
        .reduce((sum, trade) => sum + (trade.entry_price * trade.quantity), 0);
      setLibertexExposure(libertexExp);
      
      // ICMarkets exposure
      const icExp = openTrades
        .filter(t => t.platform === 'MT5_ICMARKETS' || (t.mode === 'MT5' && !t.platform))
        .reduce((sum, trade) => sum + (trade.entry_price * trade.quantity), 0);
      setIcmarketsExposure(icExp);
      
      // Bitpanda exposure
      const bitpandaExp = openTrades
        .filter(t => t.platform === 'BITPANDA' || t.mode === 'BITPANDA')
        .reduce((sum, trade) => sum + (trade.entry_price * trade.quantity), 0);
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
        quantity: 0.01,  // Standard-Menge (Backend berechnet automatisch basierend auf Risk Management)
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
      let errorMsg = 'Unbekannter Fehler';
      
      if (error.response?.data?.detail) {
        errorMsg = typeof error.response.data.detail === 'string' 
          ? error.response.data.detail 
          : JSON.stringify(error.response.data.detail);
      } else if (error.response?.data?.message) {
        errorMsg = typeof error.response.data.message === 'string'
          ? error.response.data.message
          : JSON.stringify(error.response.data.message);
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      toast.error('Fehler beim Ausführen: ' + errorMsg);
    }
  };

  const handleCloseTrade = async (trade) => {
    try {
      console.log('Closing trade:', trade);
      
      // Prepare request body
      const requestBody = {
        trade_id: trade.id,
        ticket: trade.mt5_ticket || trade.ticket,
        platform: trade.platform
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
    if (!window.confirm(`Trade "${tradeName}" wirklich löschen?`)) {
      return;
    }
    
    try {
      const response = await axios.delete(`${API}/trades/${tradeId}`);
      if (response.data.success) {
        toast.success('✅ Trade gelöscht!');
        fetchTrades();
        fetchStats();
      }
    } catch (error) {
      console.error('Error deleting trade:', error);
      toast.error(`❌ Fehler: ${error.response?.data?.detail || error.message}`);
    }
  };

  // Carousel navigation
  const enabledCommodities = Object.keys(allMarkets);
  const currentCommodityId = enabledCommodities[currentCommodityIndex];
  const currentMarket = allMarkets[currentCommodityId];
  
  const nextCommodity = () => {
    setCurrentCommodityIndex((prev) => (prev + 1) % enabledCommodities.length);
  };
  
  const prevCommodity = () => {
    setCurrentCommodityIndex((prev) => (prev - 1 + enabledCommodities.length) % enabledCommodities.length);
  };

  // handleCloseTrade is defined above with MT5 support

  const handleUpdateSettings = async (newSettings) => {
    try {
      console.log('Saving settings:', newSettings);
      const response = await axios.post(`${API}/settings`, newSettings);
      console.log('Settings saved:', response.data);
      setSettings(response.data); // Use server response
      setGpt5Active(response.data.use_ai_analysis && response.data.auto_trading);
      toast.success('Einstellungen gespeichert');
      setSettingsOpen(false);
      
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
      console.error('Settings save error:', error);
      toast.error(`Fehler beim Speichern: ${error.response?.data?.detail || error.message}`);
    }
  };
  
  // Fetch all platform data from status endpoint (more efficient)
  const fetchAllPlatformData = async () => {
    try {
      console.log('🔍 Making API call to:', `${API}/platforms/status`);
      const response = await axios.get(`${API}/platforms/status`, { timeout: 30000 }); // 30 second timeout
      console.log('🔍 Platform status response:', response.data);
      
      if (response.data && response.data.platforms) {
        const platforms = response.data.platforms;
        console.log('🔍 Found platforms:', platforms.map(p => `${p.name}: €${p.balance}`));
        
        // Find MT5_LIBERTEX platform
        const libertexPlatform = platforms.find(p => p.name === 'MT5_LIBERTEX');
        if (libertexPlatform) {
          setMt5LibertexAccount(libertexPlatform);
          setMt5LibertexConnected(libertexPlatform.connected);
          console.log('✅ MT5 Libertex account loaded:', libertexPlatform.balance);
        } else {
          console.warn('❌ MT5_LIBERTEX platform not found in response');
        }
        
        // Find MT5_ICMARKETS platform
        const icmarketsPlatform = platforms.find(p => p.name === 'MT5_ICMARKETS');
        if (icmarketsPlatform) {
          setMt5Account(icmarketsPlatform);
          setMt5Connected(icmarketsPlatform.connected);
          console.log('✅ MT5 ICMarkets account loaded:', icmarketsPlatform.balance);
        } else {
          console.warn('❌ MT5_ICMARKETS platform not found in response');
        }
      } else {
        console.warn('❌ No platforms data in response:', response.data);
      }
    } catch (error) {
      console.error('❌ Error fetching platform status:', error.message, error.code);
      setMt5LibertexConnected(false);
      setMt5Connected(false);
    }
  };

  // Legacy individual account fetchers (fallback)
  const fetchMT5LibertexAccount = async () => {
    try {
      const response = await axios.get(`${API}/platforms/MT5_LIBERTEX/account`);
      console.log('🔍 MT5 Libertex response:', response.data);
      if (response.data && response.data.account) {
        setMt5LibertexAccount(response.data.account);
        setMt5LibertexConnected(true);
        console.log('✅ MT5 Libertex account loaded:', response.data.account.balance);
      } else {
        console.warn('❌ MT5 Libertex: No account data in response');
        setMt5LibertexConnected(false);
      }
    } catch (error) {
      console.error('Error fetching MT5 Libertex account:', error);
      setMt5LibertexConnected(false);
    }
  };

  // Fetch MT5 ICMarkets Account  
  const fetchMT5ICMarketsAccount = async () => {
    try {
      const response = await axios.get(`${API}/platforms/MT5_ICMARKETS/account`);
      console.log('🔍 MT5 ICMarkets response:', response.data);
      if (response.data && response.data.account) {
        setMt5Account(response.data.account);
        setMt5Connected(true);
        console.log('✅ MT5 ICMarkets account loaded:', response.data.account.balance);
      } else {
        console.warn('❌ MT5 ICMarkets: No account data in response');
        setMt5Connected(false);
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
                Booner-Trade
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
            <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="border-slate-600 hover:bg-slate-700" data-testid="settings-button">
                  <Settings className="w-4 h-4 mr-2" />
                  Einstellungen
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-2xl">Trading Einstellungen</DialogTitle>
                </DialogHeader>
                <SettingsForm settings={settings} onSave={handleUpdateSettings} commodities={commodities} balance={balance} />
              </DialogContent>
            </Dialog>
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
                    Equity: €{mt5LibertexAccount?.equity?.toFixed(2)} | Margin: €{mt5LibertexAccount?.free_margin?.toFixed(2)}
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Portfolio-Risiko:</span>
                      <span className={
                        (libertexExposure / (mt5LibertexAccount?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                          ? 'text-red-400 font-semibold'
                          : 'text-green-400'
                      }>
                        {((libertexExposure / (mt5LibertexAccount?.balance || 1)) * 100).toFixed(1)}% / {settings?.max_portfolio_risk_percent || 20}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          (libertexExposure / (mt5LibertexAccount?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(((libertexExposure / (mt5LibertexAccount?.balance || 1)) * 100 / (settings?.max_portfolio_risk_percent || 20)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Offene Positionen: €{libertexExposure.toFixed(2)} ({trades.filter(t => t.status === 'OPEN' && (t.platform === 'MT5_LIBERTEX' || t.mode === 'MT5_LIBERTEX')).length})
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
                    Equity: €{mt5Account?.equity?.toFixed(2)} | Margin: €{mt5Account?.free_margin?.toFixed(2)}
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Portfolio-Risiko:</span>
                      <span className={
                        (icmarketsExposure / (mt5Account?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                          ? 'text-red-400 font-semibold'
                          : 'text-green-400'
                      }>
                        {((icmarketsExposure / (mt5Account?.balance || 1)) * 100).toFixed(1)}% / {settings?.max_portfolio_risk_percent || 20}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          (icmarketsExposure / (mt5Account?.balance || 1)) * 100 > (settings?.max_portfolio_risk_percent || 20)
                            ? 'bg-red-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(((icmarketsExposure / (mt5Account?.balance || 1)) * 100 / (settings?.max_portfolio_risk_percent || 20)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Offene Positionen: €{icmarketsExposure.toFixed(2)} ({trades.filter(t => t.status === 'OPEN' && (t.platform === 'MT5_ICMARKETS' || (t.mode === 'MT5' && !t.platform))).length})
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
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="cards">📊 Rohstoffe</TabsTrigger>
            <TabsTrigger value="trades">📈 Trades ({trades.length})</TabsTrigger>
            <TabsTrigger value="charts">📉 Charts</TabsTrigger>
          </TabsList>

          {/* Tab 1: Commodity Cards */}
          <TabsContent value="cards">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
          {Object.entries(allMarkets).map(([commodityId, market]) => {
            const commodity = commodities[commodityId];
            if (!commodity) return null;
            
            return (
              <Card key={commodityId} className="bg-gradient-to-br from-slate-900/90 to-slate-800/90 border-slate-700/50 backdrop-blur-sm p-4 shadow-2xl" data-testid={`commodity-card-${commodityId}`}>
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5 text-cyan-400" />
                      <h3 className="text-lg font-semibold text-slate-200">{commodity.name}</h3>
                    </div>
                    <div className="flex items-center gap-2">
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
                  <p className="text-xs text-slate-500">{commodity.category}</p>
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
                  <TabsTrigger value="closed">
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
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-800/50 border-b border-slate-700">
                          <tr>
                            <th className="px-4 py-3 text-left text-slate-300">Rohstoff</th>
                            <th className="px-4 py-3 text-left text-slate-300">Typ</th>
                            <th className="px-4 py-3 text-right text-slate-300">Einstieg</th>
                            <th className="px-4 py-3 text-right text-slate-300">Aktuell</th>
                            <th className="px-4 py-3 text-right text-slate-300">Menge</th>
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
                          'WTI': 'WTI_CRUDE',
                          'CL': 'BRENT_CRUDE',  // Brent Crude Oil (MT5 Libertex)
                          'BRENT': 'BRENT_CRUDE',
                          'BRN': 'BRENT_CRUDE',
                          'NGASCash': 'NATURAL_GAS',
                          'NGAS': 'NATURAL_GAS',
                          'WHEAT': 'WHEAT',
                          'CORN': 'CORN',
                          'SOYBEAN': 'SOYBEANS',
                          'COFFEE': 'COFFEE',
                          'SUGAR': 'SUGAR',
                          'COTTON': 'COTTON',
                          'COCOA': 'COCOA',
                          'BTCUSD': 'BITCOIN'
                        };
                        
                        const commodityId = symbolToCommodity[trade.commodity] || trade.commodity;
                        const commodity = commodities[commodityId];
                        
                        // For MT5 trades, use the current price from trade data if available, otherwise from market
                        const currentPrice = trade.current_price || trade.price || allMarkets[commodityId]?.price || trade.entry_price;
                        
                        // Calculate P&L - Use MT5's pnl field directly
                        const pl = trade.pnl !== undefined && trade.pnl !== null
                          ? trade.pnl  // Use MT5's calculated P&L (profit field)
                          : trade.profit_loss !== undefined && trade.profit_loss !== null
                            ? trade.profit_loss
                            : (trade.type === 'BUY' ? currentPrice - trade.entry_price : trade.entry_price - currentPrice) * trade.quantity;
                        
                        return (
                          <tr key={trade.id} className="border-b border-slate-800 hover:bg-slate-800/30">
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
                            <td className="px-4 py-3 text-right text-slate-200">${trade.entry_price?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">${currentPrice?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">{trade.quantity}</td>
                            <td className={`px-4 py-3 text-right font-semibold ${pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {pl >= 0 ? '+' : ''}{pl.toFixed(2)} €
                            </td>
                            <td className="px-4 py-3 text-center">
                              {(() => {
                                // Berechne Fortschritt zum Ziel (basierend auf Take Profit)
                                if (trade.status === 'OPEN' && trade.entry_price && settings) {
                                  const currentPrice = trade.price || trade.entry_price;
                                  const entryPrice = trade.entry_price;
                                  const targetPrice = trade.take_profit;
                                  
                                  if (!targetPrice) {
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
                                onClick={() => handleCloseTrade(trade)}
                                className="text-orange-400 hover:text-orange-300 text-xs font-semibold px-2 py-1 bg-orange-900/20 rounded"
                                title="Position schließen"
                              >
                                🔒 Schließen
                              </button>
                              <button
                                onClick={() => handleDeleteTrade(trade.id, `${commodity?.name || trade.commodity} ${trade.type}`)}
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
              )}
            </TabsContent>

            {/* Closed Trades Tab */}
            <TabsContent value="closed">
              {trades.filter(t => t.status === 'CLOSED').length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <p>Keine geschlossenen Trades</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800/50 border-b border-slate-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-300">Rohstoff</th>
                        <th className="px-4 py-3 text-left text-slate-300">Typ</th>
                        <th className="px-4 py-3 text-right text-slate-300">Einstieg</th>
                        <th className="px-4 py-3 text-right text-slate-300">Ausstieg</th>
                        <th className="px-4 py-3 text-right text-slate-300">Menge</th>
                        <th className="px-4 py-3 text-right text-slate-300">P&L</th>
                        <th className="px-4 py-3 text-center text-slate-300">Plattform</th>
                        <th className="px-4 py-3 text-center text-slate-300">Geschlossen</th>
                        <th className="px-4 py-3 text-center text-slate-300">Aktion</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.filter(t => {
                        // Filter: Nur geschlossene Trades OHNE Error Codes
                        if (t.status !== 'CLOSED') return false;
                        
                        // Aussortieren: Trades mit MetaAPI Error Codes
                        const hasErrorCode = t.commodity?.includes('TRADE_RETCODE') || 
                                             t.mt5_ticket?.toString().includes('TRADE_RETCODE');
                        return !hasErrorCode;
                      }).map((trade) => {
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
                        const pl = trade.profit_loss || 0;
                        
                        return (
                          <tr key={trade.id} className="border-b border-slate-800 hover:bg-slate-800/30">
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
                            <td className="px-4 py-3 text-right text-slate-200">${trade.entry_price?.toFixed(2)}</td>
                            <td className="px-4 py-3 text-right text-slate-200">${trade.exit_price?.toFixed(2) || 'N/A'}</td>
                            <td className="px-4 py-3 text-right text-slate-200">{trade.quantity}</td>
                            <td className={`px-4 py-3 text-right font-semibold ${pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {pl >= 0 ? '+' : ''}{pl.toFixed(2)} €
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
                            <td className="px-4 py-3 text-center text-xs text-slate-400">
                              {trade.closed_at ? new Date(trade.closed_at).toLocaleDateString('de-DE') : 'N/A'}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => handleDeleteTrade(trade.id, `${commodity?.name || trade.commodity} ${trade.type}`)}
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
        </Tabs>
        
        {/* Portfolio Exposure Warning */}
        {totalExposure > (balance * 0.2) && (
          <Card className="bg-amber-900/20 border-amber-500/50 p-4 mb-8">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-400" />
              <div className="flex-1">
                <h4 className="font-semibold text-amber-400">Portfolio-Risiko-Warnung</h4>
                <p className="text-sm text-slate-300 mb-2">
                  <strong>Offene Positionen:</strong> €{totalExposure.toFixed(2)} ({((totalExposure / balance) * 100).toFixed(1)}% Ihrer Balance)
                </p>
                <p className="text-xs text-slate-400">
                  • Ihre Balance: €{balance.toFixed(2)}<br/>
                  • Empfohlenes Maximum (20%): €{(balance * 0.2).toFixed(2)}<br/>
                  • Sie sollten Positionen reduzieren, um Risiko zu minimieren
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid="stats-total-trades">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Gesamt Trades</p>
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stats?.total_trades || 0}</p>
            <p className="text-xs text-slate-500 mt-1">
              Offen: {stats?.open_trades || 0} | Geschlossen: {stats?.closed_trades || 0}
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
                                  (trade.current_pl || trade.profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                                }`}>
                                  {(trade.current_pl || trade.profit || 0) >= 0 ? '+' : ''}
                                  {(trade.current_pl || trade.profit || 0)?.toFixed(2)} {trade.currency || 'EUR'}
                                </p>
                              </div>
                            </div>
                            <Button
                              onClick={async () => {
                                try {
                                  await axios.post(`${backendUrl}/api/trades/close`, {
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
                    <p className="text-xl font-bold">{selectedCommodity.marketData?.rsi?.toFixed(2) || 'N/A'}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedCommodity.marketData?.rsi > 70 ? 'Überkauft' :
                       selectedCommodity.marketData?.rsi < 30 ? 'Überverkauft' : 'Neutral'}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">MACD</p>
                    <p className="text-xl font-bold">{selectedCommodity.marketData?.macd?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">SMA 20</p>
                    <p className="text-xl font-bold">${selectedCommodity.marketData?.sma_20?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-400 mb-1">EMA 20</p>
                    <p className="text-xl font-bold">${selectedCommodity.marketData?.ema_20?.toFixed(2) || 'N/A'}</p>
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
      day_max_positions: 10
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
      const response = await axios.post(`${backendUrl}/api/settings/reset`);
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
                  Stellen Sie sicher, dass das Modell mit 'ollama pull {formData.ollama_model || 'llama2'}' installiert ist
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Dual Trading Strategy Section */}
        <div className="space-y-4 pb-4 border-b border-slate-700">
          <h4 className="font-semibold text-lg flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-400" />
            Trading Strategien
          </h4>
          <p className="text-sm text-amber-400 bg-amber-900/20 p-3 rounded border border-amber-700/30">
            ⚠️ Beide Strategien zusammen nutzen maximal 20% der Balance <strong>PRO Plattform</strong>
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
                <div>
                  <Label className="text-xs text-slate-400">Stop Loss %</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="5"
                    value={formData.day_stop_loss_percent || 0.5}
                    onChange={(e) => setFormData({ ...formData, day_stop_loss_percent: parseFloat(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 0.5%</p>
                </div>
                <div>
                  <Label className="text-xs text-slate-400">Take Profit %</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0.1"
                    max="5"
                    value={formData.day_take_profit_percent || 0.8}
                    onChange={(e) => setFormData({ ...formData, day_take_profit_percent: parseFloat(e.target.value) })}
                    className="bg-slate-800 border-slate-700 text-sm"
                  />
                  <p className="text-xs text-slate-500 mt-1">Default: 0.8%</p>
                </div>
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
      </div>

      <Button type="submit" className="w-full bg-cyan-600 hover:bg-cyan-500" data-testid="save-settings-button">
        Einstellungen speichern
      </Button>
    </form>
  );
};

export default Dashboard;