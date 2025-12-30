/**
 * 💰 Booner Trade V3.1.0 - Balance Card Komponente
 * 
 * Zeigt Kontostand und Account-Informationen für einen Broker an.
 */

import React from 'react';
import { DollarSign, TrendingUp, TrendingDown, AlertCircle, CheckCircle } from 'lucide-react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { formatCurrency, getProfitColor } from '../utils/apiUtils';

const BalanceCard = ({
  title = 'Account',
  account,
  connected = false,
  loading = false,
  variant = 'default', // 'default', 'primary', 'secondary'
}) => {
  if (loading) {
    return (
      <Card className="bg-slate-800/50 border-slate-700 p-4 animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-1/2 mb-3" />
        <div className="h-8 bg-slate-700 rounded w-3/4 mb-2" />
        <div className="h-3 bg-slate-700 rounded w-1/3" />
      </Card>
    );
  }

  const balance = account?.balance || 0;
  const equity = account?.equity || balance;
  const profit = account?.profit || 0;
  const freeMargin = account?.free_margin || account?.freeMargin || 0;
  const broker = account?.broker || title;
  const currency = account?.currency || 'EUR';

  // Variant styles
  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return 'bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-cyan-500/30';
      case 'secondary':
        return 'bg-gradient-to-br from-violet-500/20 to-purple-500/20 border-violet-500/30';
      default:
        return 'bg-slate-800/50 border-slate-700';
    }
  };

  return (
    <Card className={`${getVariantStyles()} p-4`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-cyan-400" />
          <h3 className="font-semibold text-slate-200">{title}</h3>
        </div>
        <Badge 
          variant="outline" 
          className={connected 
            ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' 
            : 'text-red-400 border-red-500/30 bg-red-500/10'
          }
        >
          {connected ? (
            <>
              <CheckCircle className="w-3 h-3 mr-1" />
              Verbunden
            </>
          ) : (
            <>
              <AlertCircle className="w-3 h-3 mr-1" />
              Offline
            </>
          )}
        </Badge>
      </div>

      {/* Balance */}
      <div className="mb-4">
        <div className="text-3xl font-bold text-white">
          {formatCurrency(balance, currency)}
        </div>
        <div className="text-sm text-slate-400">
          {broker}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-slate-900/50 rounded-lg p-2">
          <div className="text-slate-500 mb-1">Equity</div>
          <div className="text-slate-200 font-medium">
            {formatCurrency(equity, currency)}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2">
          <div className="text-slate-500 mb-1">Profit</div>
          <div className={`font-medium flex items-center gap-1 ${getProfitColor(profit)}`}>
            {profit >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {formatCurrency(profit, currency)}
          </div>
        </div>
        <div className="bg-slate-900/50 rounded-lg p-2">
          <div className="text-slate-500 mb-1">Frei</div>
          <div className="text-slate-200 font-medium">
            {formatCurrency(freeMargin, currency)}
          </div>
        </div>
      </div>

      {/* Additional Info */}
      {account?.leverage && (
        <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-400">
          <span>Hebel: 1:{account.leverage}</span>
          {account?.server && (
            <span className="truncate max-w-[150px]">{account.server}</span>
          )}
        </div>
      )}
    </Card>
  );
};

export default BalanceCard;
