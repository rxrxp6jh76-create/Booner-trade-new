/**
 * 📡 Booner Trade V3.1.0 - Status Bar Komponente
 * 
 * Zeigt System-Status, Trading-Mode und Quick-Actions an.
 */

import React from 'react';
import { Activity, Play, Pause, Zap, ZapOff, Settings, RefreshCw, Bell, BellOff } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Switch } from './ui/switch';
import { TRADING_MODE_LABELS, TRADING_MODE_COLORS } from '../config/appConfig';

const StatusBar = ({
  autoTrading = false,
  tradingMode = 'standard',
  botRunning = false,
  connected = false,
  onToggleAutoTrading,
  onRefresh,
  onSettingsClick,
  loading = false,
}) => {
  const getModeColor = () => TRADING_MODE_COLORS[tradingMode] || 'text-yellow-400';
  const getModeLabel = () => TRADING_MODE_LABELS[tradingMode] || tradingMode;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Left: Status Indicators */}
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`} />
            <span className="text-sm text-slate-400">
              {connected ? 'Verbunden' : 'Getrennt'}
            </span>
          </div>

          {/* Bot Status */}
          <div className="flex items-center gap-2">
            {botRunning ? (
              <Zap className="w-4 h-4 text-emerald-400" />
            ) : (
              <ZapOff className="w-4 h-4 text-slate-500" />
            )}
            <span className="text-sm text-slate-400">
              Bot: {botRunning ? 'Aktiv' : 'Inaktiv'}
            </span>
          </div>

          {/* Trading Mode */}
          <Badge variant="outline" className={`${getModeColor()} border-current/30`}>
            {getModeLabel()}
          </Badge>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-3">
          {/* Auto Trading Toggle */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">Auto-Trading</span>
            <Switch
              checked={autoTrading}
              onCheckedChange={onToggleAutoTrading}
              disabled={loading}
            />
            {autoTrading ? (
              <Play className="w-4 h-4 text-emerald-400" />
            ) : (
              <Pause className="w-4 h-4 text-slate-500" />
            )}
          </div>

          {/* Refresh Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>

          {/* Settings Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onSettingsClick}
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
