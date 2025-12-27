import { Card } from './ui/card';
import { TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';

const IndicatorsPanel = ({ marketData }) => {
  if (!marketData) {
    return (
      <div className="text-center text-slate-500 py-8">
        Keine Indikatoren verfügbar
      </div>
    );
  }

  const indicators = [
    {
      label: 'RSI (14)',
      value: marketData.rsi?.toFixed(2) || 'N/A',
      icon: <Activity className="w-5 h-5" />,
      color: marketData.rsi < 30 ? 'text-emerald-400' : marketData.rsi > 70 ? 'text-rose-400' : 'text-cyan-400',
      status: marketData.rsi < 30 ? 'Überverkauft' : marketData.rsi > 70 ? 'Überkauft' : 'Neutral'
    },
    {
      label: 'MACD',
      value: marketData.macd?.toFixed(2) || 'N/A',
      icon: <BarChart3 className="w-5 h-5" />,
      color: marketData.macd > marketData.macd_signal ? 'text-emerald-400' : 'text-rose-400',
      status: marketData.macd > marketData.macd_signal ? 'Bullish' : 'Bearish'
    },
    {
      label: 'SMA (20)',
      value: marketData.sma_20 ? `$${marketData.sma_20.toFixed(2)}` : 'N/A',
      icon: <TrendingUp className="w-5 h-5" />,
      color: 'text-amber-400',
      status: marketData.price > marketData.sma_20 ? 'Über SMA' : 'Unter SMA'
    },
    {
      label: 'EMA (20)',
      value: marketData.ema_20 ? `$${marketData.ema_20.toFixed(2)}` : 'N/A',
      icon: <TrendingDown className="w-5 h-5" />,
      color: 'text-purple-400',
      status: marketData.price > marketData.ema_20 ? 'Über EMA' : 'Unter EMA'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {indicators.map((indicator, index) => (
        <Card key={index} className="bg-slate-900/80 border-slate-700/50 p-6 backdrop-blur-sm" data-testid={`indicator-${indicator.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-slate-400">{indicator.label}</p>
            <span className={indicator.color}>{indicator.icon}</span>
          </div>
          <p className={`text-3xl font-bold mb-1 ${indicator.color}`}>
            {indicator.value}
          </p>
          <p className="text-xs text-slate-500">{indicator.status}</p>
          
          {indicator.label === 'RSI (14)' && marketData.rsi && (
            <div className="mt-3">
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    marketData.rsi < 30 ? 'bg-emerald-500' :
                    marketData.rsi > 70 ? 'bg-rose-500' : 'bg-cyan-500'
                  }`}
                  style={{ width: `${Math.min(marketData.rsi, 100)}%` }}
                />
              </div>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
};

export default IndicatorsPanel;