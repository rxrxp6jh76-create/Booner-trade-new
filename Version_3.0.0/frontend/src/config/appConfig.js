/**
 * 🔧 Booner Trade V3.1.0 - Zentrale Konfiguration
 * 
 * Enthält alle konfigurierbaren Werte für Frontend und API-Kommunikation.
 */

// Backend URL Detection
const getBackendUrl = async () => {
  const ELECTRON_FALLBACK_URL = 'http://localhost:8000';
  
  // Check if running in Electron
  if (window.electronAPI) {
    try {
      if (typeof window.electronAPI.getBackendUrl === 'function') {
        const url = await window.electronAPI.getBackendUrl();
        if (url && url.length > 0) {
          console.log('✅ Backend URL from Electron:', url);
          return url;
        }
      }
      console.log('⚠️ Electron detected, using fallback URL:', ELECTRON_FALLBACK_URL);
      return ELECTRON_FALLBACK_URL;
    } catch (error) {
      console.error('❌ Failed to get backend URL from Electron:', error);
      return ELECTRON_FALLBACK_URL;
    }
  }
  
  // Fallback to environment variable (for web builds)
  const envUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (envUrl && envUrl.length > 0) {
    console.log('🌐 Backend URL from env:', envUrl);
    return envUrl;
  }
  
  console.log('⚠️ No backend URL found, using ultimate fallback:', ELECTRON_FALLBACK_URL);
  return ELECTRON_FALLBACK_URL;
};

// API Configuration
export const API_CONFIG = {
  TIMEOUT: 30000,           // 30 seconds default timeout
  RETRY_COUNT: 3,           // Number of retries for failed requests
  RETRY_DELAY: 2000,        // Initial retry delay in ms
  REFRESH_INTERVAL: 30000,  // Market data refresh interval (30s)
  BALANCE_REFRESH: 60000,   // Balance refresh interval (60s)
  TRADE_REFRESH: 15000,     // Trade list refresh interval (15s)
};

// Trading Modes
export const TRADING_MODES = {
  CONSERVATIVE: 'conservative',
  STANDARD: 'standard',
  AGGRESSIVE: 'aggressive',
};

// Trading Mode Labels (German)
export const TRADING_MODE_LABELS = {
  conservative: 'Konservativ',
  standard: 'Standard',
  aggressive: 'Aggressiv',
};

// Trading Mode Colors
export const TRADING_MODE_COLORS = {
  conservative: 'text-blue-400',
  standard: 'text-yellow-400',
  aggressive: 'text-red-400',
};

// Signal Status Colors
export const SIGNAL_COLORS = {
  BUY: 'text-emerald-400',
  SELL: 'text-red-400',
  HOLD: 'text-yellow-400',
  NO_DATA: 'text-slate-500',
};

// Confidence Thresholds
export const CONFIDENCE_THRESHOLDS = {
  HIGH: 70,      // Green signal
  MEDIUM: 50,    // Yellow signal
  LOW: 30,       // Red signal
};

// Asset Categories
export const ASSET_CATEGORIES = {
  METALS: ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'COPPER', 'ZINC'],
  ENERGY: ['WTI_CRUDE', 'BRENT_CRUDE', 'NATURAL_GAS'],
  AGRICULTURE: ['WHEAT', 'CORN', 'SOYBEANS', 'COFFEE', 'SUGAR', 'COCOA'],
  CRYPTO: ['BITCOIN', 'ETHEREUM'],
  FOREX: ['USDJPY'],
  INDICES: ['NASDAQ100'],
};

// Chart Timeframes
export const CHART_TIMEFRAMES = [
  { value: '1m', label: '1 Min' },
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '1h', label: '1 Std' },
  { value: '4h', label: '4 Std' },
  { value: '1d', label: '1 Tag' },
  { value: '1wk', label: '1 Woche' },
];

// Chart Periods
export const CHART_PERIODS = [
  { value: '1d', label: '1 Tag' },
  { value: '5d', label: '5 Tage' },
  { value: '1mo', label: '1 Monat' },
  { value: '3mo', label: '3 Monate' },
  { value: '6mo', label: '6 Monate' },
  { value: '1y', label: '1 Jahr' },
];

// Default Settings
export const DEFAULT_SETTINGS = {
  auto_trading: false,
  trading_mode: 'standard',
  trading_strategy: 'DAY',
  lot_size: 0.01,
  max_portfolio_risk_percent: 20.0,
  max_positions: 5,
};

// Version Info
export const VERSION = {
  number: '3.1.0',
  name: 'Booner Trade',
  features: [
    'spread_adjustment',
    'bayesian_learning',
    '4_pillar_engine',
    'imessage_bridge',
    'ai_managed_sl_tp',
  ],
};

// Export getBackendUrl
export { getBackendUrl };

// Export default config object
export default {
  API_CONFIG,
  TRADING_MODES,
  TRADING_MODE_LABELS,
  TRADING_MODE_COLORS,
  SIGNAL_COLORS,
  CONFIDENCE_THRESHOLDS,
  ASSET_CATEGORIES,
  CHART_TIMEFRAMES,
  CHART_PERIODS,
  DEFAULT_SETTINGS,
  VERSION,
  getBackendUrl,
};
