/**
 * 🎣 Booner Trade V3.1.0 - Custom Hooks
 * 
 * Wiederverwendbare React Hooks für API-Aufrufe und State-Management.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { API_CONFIG } from '../config/appConfig';
import { axiosRetry } from '../utils/apiUtils';

/**
 * Hook für API-Aufrufe mit Loading-State und Error-Handling
 */
export const useApi = (url, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { immediate = true, onSuccess, onError } = options;

  const fetchData = useCallback(async () => {
    if (!url) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axiosRetry(() => axios.get(url));
      setData(response.data);
      onSuccess?.(response.data);
    } catch (err) {
      setError(err);
      onError?.(err);
    } finally {
      setLoading(false);
    }
  }, [url, onSuccess, onError]);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
  }, [fetchData, immediate]);

  return { data, loading, error, refetch: fetchData };
};

/**
 * Hook für periodische API-Aufrufe (Polling)
 */
export const usePolling = (url, interval = API_CONFIG.REFRESH_INTERVAL, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const { enabled = true, onSuccess, onError } = options;

  const fetchData = useCallback(async () => {
    if (!url || !enabled) return;
    
    try {
      const response = await axios.get(url, { timeout: API_CONFIG.TIMEOUT });
      setData(response.data);
      setError(null);
      onSuccess?.(response.data);
    } catch (err) {
      setError(err);
      onError?.(err);
    } finally {
      setLoading(false);
    }
  }, [url, enabled, onSuccess, onError]);

  useEffect(() => {
    if (!enabled) return;

    fetchData(); // Initial fetch

    intervalRef.current = setInterval(fetchData, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchData, interval, enabled]);

  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
};

/**
 * Hook für MT5 Account-Daten
 */
export const useMT5Account = (apiUrl, refreshInterval = API_CONFIG.BALANCE_REFRESH) => {
  const [account, setAccount] = useState(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchAccount = useCallback(async () => {
    if (!apiUrl) return;

    try {
      const response = await axios.get(`${apiUrl}/api/mt5/account`);
      if (response.data && response.data.balance !== undefined) {
        setAccount(response.data);
        setConnected(true);
      } else {
        setConnected(false);
      }
    } catch (err) {
      console.error('MT5 account fetch error:', err);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchAccount();
    const interval = setInterval(fetchAccount, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchAccount, refreshInterval]);

  return { account, connected, loading, refetch: fetchAccount };
};

/**
 * Hook für Trading-Settings
 */
export const useSettings = (apiUrl) => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    if (!apiUrl) return;

    try {
      const response = await axios.get(`${apiUrl}/api/settings`);
      setSettings(response.data);
    } catch (err) {
      console.error('Settings fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  const updateSettings = useCallback(async (updates) => {
    if (!apiUrl) return;

    try {
      const response = await axios.post(`${apiUrl}/api/settings`, updates);
      setSettings(response.data);
      return response.data;
    } catch (err) {
      console.error('Settings update error:', err);
      throw err;
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return { settings, loading, refetch: fetchSettings, updateSettings };
};

/**
 * Hook für Marktdaten
 */
export const useMarketData = (apiUrl, refreshInterval = API_CONFIG.REFRESH_INTERVAL) => {
  const [markets, setMarkets] = useState({});
  const [commodities, setCommodities] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchMarketData = useCallback(async () => {
    if (!apiUrl) return;

    try {
      const response = await axios.get(`${apiUrl}/api/market/all`);
      setMarkets(response.data.markets || {});
      setCommodities(response.data.commodities || []);
    } catch (err) {
      console.error('Market data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchMarketData, refreshInterval]);

  return { markets, commodities, loading, refetch: fetchMarketData };
};

/**
 * Hook für Signals-Status
 */
export const useSignals = (apiUrl, refreshInterval = API_CONFIG.REFRESH_INTERVAL) => {
  const [signals, setSignals] = useState({});
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSignals = useCallback(async () => {
    if (!apiUrl) return;

    try {
      const response = await axios.get(`${apiUrl}/api/signals/status`);
      setSignals(response.data.signals || {});
      setSummary(response.data.summary || null);
    } catch (err) {
      console.error('Signals fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchSignals();
    const interval = setInterval(fetchSignals, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchSignals, refreshInterval]);

  return { signals, summary, loading, refetch: fetchSignals };
};

/**
 * Hook für Trades
 */
export const useTrades = (apiUrl, refreshInterval = API_CONFIG.TRADE_REFRESH) => {
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchTrades = useCallback(async () => {
    if (!apiUrl) return;

    try {
      const [tradesRes, statsRes] = await Promise.all([
        axios.get(`${apiUrl}/api/trades/list`),
        axios.get(`${apiUrl}/api/trades/stats`),
      ]);
      setTrades(tradesRes.data.trades || []);
      setStats(statsRes.data || null);
    } catch (err) {
      console.error('Trades fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchTrades();
    const interval = setInterval(fetchTrades, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchTrades, refreshInterval]);

  return { trades, stats, loading, refetch: fetchTrades };
};

/**
 * Hook für Local Storage mit State-Sync
 */
export const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
};

export default {
  useApi,
  usePolling,
  useMT5Account,
  useSettings,
  useMarketData,
  useSignals,
  useTrades,
  useLocalStorage,
};
