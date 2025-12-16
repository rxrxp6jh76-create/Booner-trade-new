import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PriceChart = ({ data, commodityName = 'Commodity', commodityId = null, isOHLCV = false, enableLiveTicker = false }) => {
  const [chartData, setChartData] = useState(data || []);
  const [livePrice, setLivePrice] = useState(null);
  
  // Debug: Log data to console
  console.log(`PriceChart für ${commodityName}:`, {
    dataPoints: data?.length,
    isOHLCV,
    enableLiveTicker,
    commodityId,
    firstItem: data?.[0],
    lastItem: data?.[data.length - 1]
  });
  
  // Update chart data when props change
  useEffect(() => {
    if (data && data.length > 0) {
      setChartData(data);
    }
  }, [data]);
  
  // Live ticker - ECHTZEIT Updates für Trading (alle 5 Sekunden)
  // Rolling Window: Nur die letzten 150 Datenpunkte behalten
  useEffect(() => {
    if (!enableLiveTicker || !commodityId) return;
    
    const fetchLivePrice = async () => {
      try {
        const response = await axios.get(`${API}/market/live-ticks`);
        const livePrices = response.data.live_prices || {};
        
        if (livePrices[commodityId]) {
          const tick = livePrices[commodityId];
          setLivePrice(tick.price);
          
          // Update last candle with live price
          if (chartData.length > 0) {
            setChartData(prevData => {
              // ROLLING WINDOW: Max 150 Punkte für KI-Analyse (ca. 12.5 Stunden bei 5min Candles)
              // Das reicht für alle technischen Indikatoren (MA50, BB20, RSI14, MACD)
              const limitedData = prevData.length > 150 ? prevData.slice(-150) : prevData;
              const updatedData = [...limitedData];
              const lastCandle = updatedData[updatedData.length - 1];
              
              // Update close price and high/low
              lastCandle.close = tick.price;
              lastCandle.price = tick.price;
              
              // Update high/low
              if (tick.price > lastCandle.high) lastCandle.high = tick.price;
              if (tick.price < lastCandle.low) lastCandle.low = tick.price;
              
              return updatedData;
            });
          }
        }
      } catch (error) {
        console.error('Error fetching live tick:', error);
      }
    };
    
    // Initial fetch
    fetchLivePrice();
    
    // ECHTZEIT: Alle 5 Sekunden aktualisieren (essentiell für Trading!)
    const interval = setInterval(fetchLivePrice, 5000);
    
    return () => clearInterval(interval);
  }, [enableLiveTicker, commodityId]);

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-slate-500">
        <p>Keine Daten verfügbar</p>
      </div>
    );
  }

  // Format time based on timespan (detect if intraday or multi-day)
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    
    // Calculate timespan between first and last data point
    if (data.length < 2) {
      return date.toLocaleString('de-DE', { 
        day: '2-digit', 
        month: 'short', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
    
    const firstDate = new Date(data[0].timestamp);
    const lastDate = new Date(data[data.length - 1].timestamp);
    const timespanHours = (lastDate - firstDate) / (1000 * 60 * 60);
    
    // For very short periods (< 12 hours): Show only time
    if (timespanHours < 12) {
      return date.toLocaleTimeString('de-DE', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
    // For intraday (< 3 days): Show date + time
    else if (timespanHours < 72) {
      return date.toLocaleString('de-DE', { 
        day: '2-digit', 
        month: 'short', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
    // For longer periods: Show only date
    else {
      return date.toLocaleDateString('de-DE', { 
        day: '2-digit', 
        month: 'short' 
      });
    }
  };

  const formattedChartData = chartData.map(item => {
    // Handle both old format (item.price) and new OHLCV format (item.close)
    const price = isOHLCV ? item.close : (item.price || item.close);
    
    return {
      time: formatTime(item.timestamp),
      price: Number(price) || 0,
      high: Number(item.high) || 0,
      low: Number(item.low) || 0,
      open: Number(item.open) || 0,
      sma: item.sma_20 ? Number(item.sma_20) : null,
      ema: item.ema_20 ? Number(item.ema_20) : null
    };
  });

  // Calculate Y-axis domain for better scaling
  const allPrices = formattedChartData.map(d => d.price).filter(p => p > 0);
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const padding = (maxPrice - minPrice) * 0.05; // 5% padding
  const yDomain = [
    Math.floor(minPrice - padding),
    Math.ceil(maxPrice + padding)
  ];

  console.log('Chart Debug:', {
    dataPoints: formattedChartData.length,
    sample: formattedChartData.slice(0, 2),
    yDomain,
    priceRange: { min: minPrice, max: maxPrice }
  });

  return (
    <div className="relative">
      {enableLiveTicker && livePrice && (
        <div className="absolute top-2 right-2 z-10 bg-emerald-900/90 border border-emerald-500/50 px-3 py-1 rounded-lg flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold text-emerald-300">LIVE: ${livePrice.toFixed(2)}</span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={formattedChartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
        <XAxis 
          dataKey="time" 
          stroke="#94a3b8" 
          style={{ fontSize: '12px' }}
          tick={{ fill: '#94a3b8' }}
        />
        <YAxis 
          stroke="#94a3b8" 
          style={{ fontSize: '12px' }}
          tick={{ fill: '#94a3b8' }}
          domain={yDomain}
          tickFormatter={(value) => `$${value.toFixed(0)}`}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1e293b', 
            border: '1px solid #475569',
            borderRadius: '8px',
            color: '#e4e8f0'
          }}
          labelStyle={{ color: '#94a3b8' }}
          formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Preis']}
        />
        {/* Legend entfernt - nur Preis wird angezeigt */}
        <Area 
          type="monotone" 
          dataKey="price" 
          stroke="#2dd4bf" 
          strokeWidth={3}
          fill="url(#priceGradient)" 
          name={`${commodityName} Preis`}
        />
        {/* SMA und EMA Linien entfernt - nur Preis wird angezeigt */}
      </AreaChart>
    </ResponsiveContainer>
    </div>
  );
};

export default PriceChart;