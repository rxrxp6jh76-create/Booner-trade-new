/**
 * 🔧 Booner Trade V3.1.0 - API Utilities
 * 
 * Zentrale API-Hilfsfunktionen für konsistente Fehlerbehandlung und Retries.
 */

import axios from 'axios';
import { API_CONFIG } from '../config/appConfig';

// Configure axios defaults
axios.defaults.timeout = API_CONFIG.TIMEOUT;

/**
 * Retry-Wrapper für API-Aufrufe mit exponential backoff
 */
export const axiosRetry = async (fn, retries = API_CONFIG.RETRY_COUNT, delay = API_CONFIG.RETRY_DELAY) => {
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

/**
 * Erstellt einen API-Client mit der Backend-URL
 */
export const createApiClient = (backendUrl) => {
  const client = axios.create({
    baseURL: backendUrl,
    timeout: API_CONFIG.TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Response interceptor for error handling
  client.interceptors.response.use(
    response => response,
    error => {
      if (error.code === 'ECONNABORTED') {
        console.error('⏱️ Request timeout');
      } else if (error.response) {
        console.error(`❌ API Error: ${error.response.status} - ${error.response.statusText}`);
      } else if (error.request) {
        console.error('❌ No response received from server');
      } else {
        console.error('❌ Request setup error:', error.message);
      }
      return Promise.reject(error);
    }
  );

  return client;
};

/**
 * Formatiert Währungsbeträge
 */
export const formatCurrency = (amount, currency = 'EUR', locale = 'de-DE') => {
  if (amount === null || amount === undefined) return '-';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

/**
 * Formatiert Prozentangaben
 */
export const formatPercent = (value, decimals = 2) => {
  if (value === null || value === undefined) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`;
};

/**
 * Formatiert große Zahlen (z.B. 1.5K, 2.3M)
 */
export const formatCompactNumber = (num) => {
  if (num === null || num === undefined) return '-';
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toFixed(2);
};

/**
 * Formatiert Datum/Zeit
 */
export const formatDateTime = (dateString, locale = 'de-DE') => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Formatiert nur Zeit
 */
export const formatTime = (dateString, locale = 'de-DE') => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleTimeString(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Berechnet Profit/Loss-Farbe
 */
export const getProfitColor = (profit) => {
  if (profit > 0) return 'text-emerald-400';
  if (profit < 0) return 'text-red-400';
  return 'text-slate-400';
};

/**
 * Berechnet Confidence-Farbe
 */
export const getConfidenceColor = (confidence) => {
  if (confidence >= 70) return 'text-emerald-400';
  if (confidence >= 50) return 'text-yellow-400';
  if (confidence >= 30) return 'text-orange-400';
  return 'text-red-400';
};

/**
 * Berechnet Confidence-Badge
 */
export const getConfidenceBadge = (confidence) => {
  if (confidence >= 70) return { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', label: 'Stark' };
  if (confidence >= 50) return { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', label: 'Mittel' };
  if (confidence >= 30) return { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', label: 'Schwach' };
  return { color: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'Gering' };
};

/**
 * Sicheres JSON-Parsing
 */
export const safeJsonParse = (str, fallback = null) => {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
};

/**
 * Debounce-Funktion
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle-Funktion
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
};

export default {
  axiosRetry,
  createApiClient,
  formatCurrency,
  formatPercent,
  formatCompactNumber,
  formatDateTime,
  formatTime,
  getProfitColor,
  getConfidenceColor,
  getConfidenceBadge,
  safeJsonParse,
  debounce,
  throttle,
};
