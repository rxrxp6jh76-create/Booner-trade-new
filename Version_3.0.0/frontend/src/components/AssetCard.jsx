/**
 * 📊 Booner Trade V3.1.0 - Asset Card Komponente
 * 
 * Zeigt ein einzelnes Asset mit Preis, Signal und Confidence an.
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity, LineChart } from 'lucide-react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { getConfidenceColor, formatCurrency, formatPercent } from '../utils/apiUtils';

const AssetCard = ({
  asset,
  marketData,
  signalData,
  onClick,
  onChartClick,
  compact = false,
}) => {
  if (!asset) return null;

  const name = asset.name || asset.id;
  const price = marketData?.price || signalData?.price || 0;
  const confidence = signalData?.confidence || 0;
  const signal = signalData?.signal || 'HOLD';
  const rsi = marketData?.rsi || signalData?.indicators?.rsi || 50;
  const priceChange = marketData?.change_percent || 0;

  // Signal Icon
  const getSignalIcon = () => {
    switch (signal) {
      case 'BUY':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />;
      case 'SELL':
        return <TrendingDown className="w-4 h-4 text-red-400" />;
      default:
        return <Minus className="w-4 h-4 text-yellow-400" />;
    }
  };

  // Signal Badge Color
  const getSignalBadgeColor = () => {
    switch (signal) {
      case 'BUY':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'SELL':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    }
  };

  // Confidence Bar Color
  const getConfidenceBarColor = () => {
    if (confidence >= 70) return 'bg-emerald-500';
    if (confidence >= 50) return 'bg-yellow-500';
    if (confidence >= 30) return 'bg-orange-500';
    return 'bg-red-500';
  };

  if (compact) {
    return (
      <div 
        className="flex items-center justify-between p-2 bg-slate-800/30 rounded-lg cursor-pointer hover:bg-slate-800/50 transition-colors"
        onClick={() => onClick?.(asset)}
      >
        <div className="flex items-center gap-2">
          {getSignalIcon()}
          <span className="text-sm font-medium text-slate-200">{name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-300">${price.toFixed(2)}</span>
          <Badge variant="outline" className={`text-xs ${getSignalBadgeColor()}`}>
            {confidence}%
          </Badge>
        </div>
      </div>
    );
  }

  return (
    <Card 
      className="bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-all cursor-pointer group"
      onClick={() => onClick?.(asset)}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h3 className="font-semibold text-slate-200 text-sm">{name}</h3>
          </div>
          <Badge variant="outline" className={`${getSignalBadgeColor()}`}>
            {signal}
          </Badge>
        </div>

        {/* Price */}
        <div className="mb-3">
          <div className="text-2xl font-bold text-white">
            {formatCurrency(price, 'USD', 'en-US')}
          </div>
          <div className={`text-sm ${priceChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {formatPercent(priceChange)}
          </div>
        </div>

        {/* Confidence Bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Confidence</span>
            <span className={getConfidenceColor(confidence)}>{confidence}%</span>
          </div>
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getConfidenceBarColor()} transition-all duration-500`}
              style={{ width: `${confidence}%` }}
            />
          </div>
        </div>

        {/* Indicators */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="bg-slate-900/50 rounded p-2">
            <div className="text-slate-500">RSI</div>
            <div className={`font-medium ${
              rsi > 70 ? 'text-red-400' : rsi < 30 ? 'text-emerald-400' : 'text-slate-300'
            }`}>
              {rsi?.toFixed(1) || '-'}
            </div>
          </div>
          <div className="bg-slate-900/50 rounded p-2">
            <div className="text-slate-500">Signal</div>
            <div className="flex items-center gap-1">
              {getSignalIcon()}
              <span className="text-slate-300">{signal}</span>
            </div>
          </div>
        </div>

        {/* Chart Button */}
        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-3 text-slate-400 hover:text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => {
            e.stopPropagation();
            onChartClick?.(asset);
          }}
        >
          <LineChart className="w-4 h-4 mr-2" />
          Chart anzeigen
        </Button>
      </div>
    </Card>
  );
};

export default AssetCard;
