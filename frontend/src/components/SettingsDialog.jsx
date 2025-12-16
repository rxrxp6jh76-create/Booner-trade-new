import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Zap, TrendingUp, Activity, Shield, Cloud } from 'lucide-react';

const SettingsDialog = ({ open, onOpenChange, settings, onSave }) => {
  const [formData, setFormData] = useState(() => {
    const defaults = {
      // Auto-Trading
      auto_trading: false,
      
      // AI Settings
      use_ai_analysis: true,
      ai_provider: 'emergent',
      ai_model: 'gpt-5',
      ollama_base_url: 'http://127.0.0.1:11434',
      ollama_model: 'llama3:latest',
      use_llm_confirmation: false,
      
      // Trading Strategies
      swing_trading_enabled: true,
      swing_min_confidence_score: 0.6,
      swing_stop_loss_percent: 2.0,
      swing_take_profit_percent: 4.0,
      swing_max_positions: 5,
      swing_risk_per_trade_percent: 2.0,
      swing_position_hold_time_hours: 168, // 7 Tage
      
      day_trading_enabled: true,
      day_min_confidence_score: 0.4,
      day_stop_loss_percent: 1.5,
      day_take_profit_percent: 2.5,
      day_max_positions: 10,
      day_risk_per_trade_percent: 1.0,
      day_position_hold_time_hours: 2,
      
      // Scalping Strategy - 🐛 FIX: Alle Settings hinzugefügt
      scalping_enabled: false,
      scalping_min_confidence_score: 0.6,
      scalping_max_positions: 3,
      scalping_take_profit_percent: 0.15,
      scalping_stop_loss_percent: 0.08,
      scalping_max_hold_time_minutes: 5,
      scalping_risk_per_trade_percent: 0.5,
      
      // Risk Management
      max_trades_per_hour: 10,
      combined_max_balance_percent_per_platform: 20.0,
      
      // Technical Indicators
      rsi_oversold_threshold: 30,
      rsi_overbought_threshold: 70,
      macd_signal_threshold: 0,
      
      // Active Platforms
      active_platforms: []
    };
    
    if (settings) {
      return { ...defaults, ...settings };
    }
    return defaults;
  });
  
  // Sync formData when settings prop changes (e.g., after backend load)
  // CRITICAL FIX V2.3.4: Only sync when dialog OPENS, not on every settings update!
  useEffect(() => {
    // Only sync when dialog OPENS (not on every settings change)
    if (!open || !settings) return;
    
    const defaults = {
      id: 'trading_settings',
      auto_trading: false,
      use_ai_analysis: true,
      use_llm_confirmation: false,  // CRITICAL FIX V2.3.5: Fehlte im Frontend!
      ai_provider: 'emergent',
      ai_model: 'gpt-5',
      stop_loss_percent: 2.0,
      take_profit_percent: 4.0,
      use_trailing_stop: false,
      trailing_stop_distance: 1.5,
      max_trades_per_hour: 10,
      combined_max_balance_percent_per_platform: 20.0,
      rsi_oversold_threshold: 30,
      rsi_overbought_threshold: 70,
      macd_signal_threshold: 0,
      // CRITICAL FIX: Don't default active_platforms to []! This was causing checkboxes to disappear.
      // active_platforms: [],  // REMOVED - let backend settings take precedence
      // MetaAPI Account IDs
      mt5_libertex_account_id: '5cc9abd1-671a-447e-ab93-5abbfe0ed941',
      mt5_icmarkets_account_id: 'd2605e89-7bc2-4144-9f7c-951edd596c39',
      mt5_libertex_real_account_id: '',
      // Scalping defaults
      scalping_enabled: false,
      scalping_min_confidence_score: 0.6,
      scalping_max_positions: 3
    };
    // IMPORTANT: Settings from backend override defaults
    setFormData({ ...defaults, ...settings });
    console.log('📋 SettingsDialog synced - active_platforms:', settings.active_platforms);
  }, [open]);  // ONLY trigger when dialog opens, NOT on every settings change!

  const handleSubmit = (e) => {
    e.preventDefault();
    // WICHTIG: Behalte active_platforms aus den ursprünglichen Settings!
    // Der Dialog kennt diese nicht, darf sie aber nicht überschreiben
    const settingsToSave = {
      ...formData,
      active_platforms: settings?.active_platforms || formData.active_platforms || []
    };
    
    // 🔍 DEBUG: Log SL/TP values BEFORE sending to backend
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔍 FRONTEND: Sending settings to backend...');
    console.log('Day Trading:');
    console.log('  - day_stop_loss_percent:', settingsToSave.day_stop_loss_percent);
    console.log('  - day_take_profit_percent:', settingsToSave.day_take_profit_percent);
    console.log('Swing Trading:');
    console.log('  - swing_stop_loss_percent:', settingsToSave.swing_stop_loss_percent);
    console.log('  - swing_take_profit_percent:', settingsToSave.swing_take_profit_percent);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    onSave(settingsToSave);
  };

  const aiProviderModels = {
    emergent: ['gpt-5', 'gpt-4-turbo'],
    openai: ['gpt-5', 'gpt-4-turbo'],
    gemini: ['gemini-2.0-flash-exp', 'gemini-1.5-pro'],
    anthropic: ['claude-3-5-sonnet-20241022'],
    ollama: ['llama4', 'llama3.2', 'llama3.1', 'mistral', 'codellama'],  // 🐛 FIX: llama4 hinzugefügt
  };

  const currentProvider = formData.ai_provider || 'emergent';
  const availableModels = aiProviderModels[currentProvider] || ['gpt-5'];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">⚙️ Trading Bot Einstellungen</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-5 bg-slate-800">
              <TabsTrigger value="general" className="data-[state=active]:bg-cyan-600">
                <Zap className="w-4 h-4 mr-2" />
                Allgemein
              </TabsTrigger>
              <TabsTrigger value="platforms" className="data-[state=active]:bg-cyan-600">
                <Cloud className="w-4 h-4 mr-2" />
                Plattformen
              </TabsTrigger>
              <TabsTrigger value="aibot" className="data-[state=active]:bg-cyan-600">
                <Activity className="w-4 h-4 mr-2" />
                AI Bot
              </TabsTrigger>
              <TabsTrigger value="strategies" className="data-[state=active]:bg-cyan-600">
                <TrendingUp className="w-4 h-4 mr-2" />
                Trading Strategien
              </TabsTrigger>
              <TabsTrigger value="risk" className="data-[state=active]:bg-cyan-600">
                <Shield className="w-4 h-4 mr-2" />
                Risiko Management
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: Allgemein */}
            <TabsContent value="general" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Auto-Trading</h3>
                
                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="auto_trading" className="text-base font-medium">
                      Automatisches Trading aktivieren
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">
                      Bot öffnet und schließt Trades automatisch
                    </p>
                  </div>
                  <Switch
                    id="auto_trading"
                    checked={formData.auto_trading || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, auto_trading: checked })}
                  />
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Handelszeiten</h3>
                
                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="respect_market_hours" className="text-base font-medium">
                      Markt-Öffnungszeiten beachten
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">
                      Bot handelt nur während Marktöffnungszeiten
                    </p>
                  </div>
                  <Switch
                    id="respect_market_hours"
                    checked={formData.respect_market_hours !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, respect_market_hours: checked })}
                  />
                </div>

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="allow_weekend_trading" className="text-base font-medium">
                      Wochenend-Trading erlauben
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">
                      Bot kann auch am Wochenende handeln
                    </p>
                  </div>
                  <Switch
                    id="allow_weekend_trading"
                    checked={formData.allow_weekend_trading || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, allow_weekend_trading: checked })}
                  />
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Asset-spezifische Handelszeiten</h3>
                <p className="text-sm text-slate-400 mb-4">
                  Definieren Sie für jedes Asset individuelle Handelszeiten (UTC)
                </p>
                
                {['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM', 'WTI_CRUDE', 'BRENT_CRUDE', 'NATURAL_GAS', 'COPPER', 'WHEAT', 'CORN', 'SOYBEANS', 'COFFEE', 'SUGAR', 'COCOA', 'EURUSD', 'BITCOIN'].map(asset => (
                  <div key={asset} className="p-4 bg-slate-700 rounded-lg space-y-3">
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-base font-medium text-cyan-300">{asset}</Label>
                      <div className="flex items-center gap-2">
                        <Label htmlFor={`${asset}_weekend`} className="text-xs text-slate-400">Wochenend-Trading</Label>
                        <Switch
                          id={`${asset}_weekend`}
                          checked={formData[`${asset.toLowerCase()}_allow_weekend`] || false}
                          onCheckedChange={(checked) => setFormData({...formData, [`${asset.toLowerCase()}_allow_weekend`]: checked})}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor={`${asset}_open`} className="text-xs">Öffnung (UTC)</Label>
                        <Input
                          id={`${asset}_open`}
                          type="time"
                          defaultValue={formData[`${asset.toLowerCase()}_market_open`] || "00:00"}
                          onChange={(e) => setFormData({...formData, [`${asset.toLowerCase()}_market_open`]: e.target.value})}
                          className="bg-slate-600 border-slate-500"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor={`${asset}_close`} className="text-xs">Schließung (UTC)</Label>
                        <Input
                          id={`${asset}_close`}
                          type="time"
                          defaultValue={formData[`${asset.toLowerCase()}_market_close`] || "23:59"}
                          onChange={(e) => setFormData({...formData, [`${asset.toLowerCase()}_market_close`]: e.target.value})}
                          className="bg-slate-600 border-slate-500"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            {/* TAB 2: Plattformen & MetaAPI IDs */}
            <TabsContent value="platforms" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-cyan-400">MetaAPI Account IDs</h3>
                  <Button
                    type="button"
                    onClick={async () => {
                      try {
                        const API_URL = process.env.REACT_APP_BACKEND_URL || '';
                        const response = await fetch(`${API_URL}/api/metaapi/update-ids`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            libertex_demo_id: formData.mt5_libertex_account_id || '',
                            icmarkets_demo_id: formData.mt5_icmarkets_account_id || '',
                            libertex_real_id: formData.mt5_libertex_real_account_id || ''
                          })
                        });
                        
                        if (response.ok) {
                          alert('✅ MetaAPI IDs erfolgreich aktualisiert! Backend wird neu gestartet...');
                          window.location.reload();
                        } else {
                          const error = await response.json();
                          alert(`❌ Fehler: ${error.detail || 'Unbekannter Fehler'}`);
                        }
                      } catch (error) {
                        alert(`❌ Fehler: ${error.message}`);
                      }
                    }}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    🔄 IDs übernehmen & neu verbinden
                  </Button>
                </div>

                <div className="p-4 bg-blue-900/20 border border-blue-700 rounded-lg mb-4">
                  <p className="text-sm text-blue-200">
                    <strong>ℹ️ Hinweis:</strong> Tragen Sie hier Ihre MetaAPI Account IDs ein. 
                    Nach dem Klick auf "IDs übernehmen" werden diese in beiden .env Dateien gespeichert 
                    und die Verbindungen neu aufgebaut.
                  </p>
                </div>

                {/* MT5 Libertex Demo */}
                <div className="space-y-2 p-4 bg-slate-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="libertex_demo_id" className="text-base font-medium text-cyan-300">
                      🔷 MT5 Libertex Demo (MT5-510038543)
                    </Label>
                    <span className="text-xs text-slate-400">DEMO</span>
                  </div>
                  <Input
                    id="libertex_demo_id"
                    type="text"
                    placeholder="5cc9abd1-671a-447e-ab93-5abbfe0ed941"
                    value={formData.mt5_libertex_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_libertex_account_id: e.target.value })}
                    className="bg-slate-600 border-slate-500 font-mono text-sm"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Default: 5cc9abd1-671a-447e-ab93-5abbfe0ed941
                  </p>
                </div>

                {/* MT5 ICMarkets Demo */}
                <div className="space-y-2 p-4 bg-slate-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="icmarkets_demo_id" className="text-base font-medium text-purple-300">
                      🟣 MT5 ICMarkets Demo (MT5-52565616)
                    </Label>
                    <span className="text-xs text-slate-400">DEMO</span>
                  </div>
                  <Input
                    id="icmarkets_demo_id"
                    type="text"
                    placeholder="d2605e89-7bc2-4144-9f7c-951edd596c39"
                    value={formData.mt5_icmarkets_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_icmarkets_account_id: e.target.value })}
                    className="bg-slate-600 border-slate-500 font-mono text-sm"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Default: d2605e89-7bc2-4144-9f7c-951edd596c39
                  </p>
                </div>

                {/* MT5 Libertex REAL */}
                <div className="space-y-2 p-4 bg-amber-900/30 border border-amber-700 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Label htmlFor="libertex_real_id" className="text-base font-medium text-amber-300">
                      💰 MT5 Libertex REAL (MT5-560031700)
                    </Label>
                    <span className="text-xs text-amber-400 font-bold">ECHTES GELD!</span>
                  </div>
                  <Input
                    id="libertex_real_id"
                    type="text"
                    placeholder="Noch nicht konfiguriert"
                    value={formData.mt5_libertex_real_account_id || ''}
                    onChange={(e) => setFormData({ ...formData, mt5_libertex_real_account_id: e.target.value })}
                    className="bg-slate-600 border-amber-500 font-mono text-sm"
                  />
                  <p className="text-xs text-amber-300 mt-1">
                    ⚠️ Achtung: Dies ist ein ECHTGELD-Account! Nur aktivieren wenn Sie bereit für Live-Trading sind.
                  </p>
                </div>

                <div className="p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg mt-4">
                  <p className="text-sm text-yellow-200">
                    <strong>📖 Anleitung:</strong><br />
                    1. Gehen Sie zu <a href="https://app.metaapi.cloud" target="_blank" rel="noopener noreferrer" className="underline">metaapi.cloud</a><br />
                    2. Wählen Sie Ihren Account aus<br />
                    3. Kopieren Sie die Account ID (lange UUID)<br />
                    4. Fügen Sie sie hier ein<br />
                    5. Klicken Sie auf "IDs übernehmen & neu verbinden"
                  </p>
                </div>
              </div>
            </TabsContent>


            {/* TAB 2: AI Bot */}
            <TabsContent value="aibot" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">KI-Analyse</h3>
                
                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <Label htmlFor="use_ai_analysis" className="text-base">KI-Analyse verwenden</Label>
                  <Switch
                    id="use_ai_analysis"
                    checked={formData.use_ai_analysis !== false}
                    onCheckedChange={(checked) => setFormData({ ...formData, use_ai_analysis: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ai_provider">AI Provider</Label>
                    <select
                      id="ai_provider"
                      value={currentProvider}
                      onChange={(e) => {
                        const newProvider = e.target.value;
                        const newModel = aiProviderModels[newProvider][0];
                        setFormData({ ...formData, ai_provider: newProvider, ai_model: newModel });
                      }}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100"
                    >
                      {Object.keys(aiProviderModels).map(provider => (
                        <option key={provider} value={provider}>{provider}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="ai_model">AI Model</Label>
                    <select
                      id="ai_model"
                      value={formData.ai_model || availableModels[0]}
                      onChange={(e) => setFormData({ ...formData, ai_model: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-slate-100"
                    >
                      {availableModels.map(model => (
                        <option key={model} value={model}>{model}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Ollama URL - nur wenn Ollama Provider ausgewählt ist */}
                {currentProvider === 'ollama' && (
                  <div className="space-y-2">
                    <Label htmlFor="ollama_base_url">Ollama Server URL</Label>
                    <Input
                      id="ollama_base_url"
                      type="text"
                      placeholder="http://localhost:11434"
                      value={formData.ollama_base_url || 'http://localhost:11434'}
                      onChange={(e) => setFormData({ ...formData, ollama_base_url: e.target.value })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-400">
                      URL des lokalen Ollama Servers (Standard: http://localhost:11434)
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                  <div>
                    <Label htmlFor="use_llm_confirmation" className="text-base">
                      LLM Final Confirmation
                    </Label>
                    <p className="text-sm text-slate-400 mt-1">
                      LLM prüft jedes Signal vor Trade-Ausführung
                    </p>
                  </div>
                  <Switch
                    id="use_llm_confirmation"
                    checked={formData.use_llm_confirmation || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, use_llm_confirmation: checked })}
                  />
                </div>
              </div>

              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Technische Indikatoren</h3>
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rsi_oversold">RSI Überverkauft</Label>
                    <Input
                      id="rsi_oversold"
                      type="number"
                      value={formData.rsi_oversold_threshold || 30}
                      onChange={(e) => setFormData({ ...formData, rsi_oversold_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="rsi_overbought">RSI Überkauft</Label>
                    <Input
                      id="rsi_overbought"
                      type="number"
                      value={formData.rsi_overbought_threshold || 70}
                      onChange={(e) => setFormData({ ...formData, rsi_overbought_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="macd_threshold">MACD Schwelle</Label>
                    <Input
                      id="macd_threshold"
                      type="number"
                      step="0.01"
                      value={formData.macd_signal_threshold || 0}
                      onChange={(e) => setFormData({ ...formData, macd_signal_threshold: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* TAB 3: Trading Strategien */}
            <TabsContent value="strategies" className="space-y-6 mt-6">
              {/* Swing Trading */}
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-cyan-400">Swing Trading</h3>
                  <Switch
                    id="swing_enabled"
                    checked={formData.swing_trading_enabled || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, swing_trading_enabled: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="swing_confidence">Min. Konfidenz (%)</Label>
                    <Input
                      id="swing_confidence"
                      type="number"
                      step="0.01"
                      value={(formData.swing_min_confidence_score || 0.6) * 100}
                      onChange={(e) => setFormData({ ...formData, swing_min_confidence_score: parseFloat(e.target.value) / 100 })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="swing_max_pos">Max. Positionen</Label>
                    <Input
                      id="swing_max_pos"
                      type="number"
                      value={formData.swing_max_positions || 5}
                      onChange={(e) => setFormData({ ...formData, swing_max_positions: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="swing_sl">Stop Loss (%)</Label>
                    <Input
                      id="swing_sl"
                      type="number"
                      step="0.1"
                      value={formData.swing_stop_loss_percent || 2.0}
                      onChange={(e) => setFormData({ ...formData, swing_stop_loss_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="swing_tp">Take Profit (%)</Label>
                    <Input
                      id="swing_tp"
                      type="number"
                      step="0.1"
                      value={formData.swing_take_profit_percent || 4.0}
                      onChange={(e) => setFormData({ ...formData, swing_take_profit_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="swing_risk">Risiko pro Trade (%)</Label>
                    <Input
                      id="swing_risk"
                      type="number"
                      step="0.1"
                      value={formData.swing_risk_per_trade_percent || 2.0}
                      onChange={(e) => setFormData({ ...formData, swing_risk_per_trade_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="swing_hold">Max. Haltezeit (Stunden)</Label>
                    <Input
                      id="swing_hold"
                      type="number"
                      value={formData.swing_position_hold_time_hours || 168}
                      onChange={(e) => setFormData({ ...formData, swing_position_hold_time_hours: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>
              </div>

              {/* Scalping Strategy - 🐛 FIX: Alle Settings einstellbar gemacht! */}
              <div className="space-y-4 p-6 bg-purple-900/20 rounded-lg border-2 border-purple-500">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-purple-400">⚡🎯 Scalping (Ultra-Schnell)</h3>
                    <p className="text-xs text-slate-400 mt-1">30s-5min Trades, enge TP/SL</p>
                  </div>
                  <Switch
                    id="scalping_enabled"
                    checked={formData.scalping_enabled || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, scalping_enabled: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="scalping_confidence">Min. Konfidenz (%)</Label>
                    <Input
                      id="scalping_confidence"
                      type="number"
                      step="0.01"
                      value={(formData.scalping_min_confidence_score || 0.6) * 100}
                      onChange={(e) => setFormData({ ...formData, scalping_min_confidence_score: parseFloat(e.target.value) / 100 })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 60%</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="scalping_max_pos">Max. Positionen</Label>
                    <Input
                      id="scalping_max_pos"
                      type="number"
                      value={formData.scalping_max_positions || 3}
                      onChange={(e) => setFormData({ ...formData, scalping_max_positions: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 3</p>
                  </div>

                  {/* NEU: Take Profit % */}
                  <div className="space-y-2">
                    <Label htmlFor="scalping_tp">Take Profit (%)</Label>
                    <Input
                      id="scalping_tp"
                      type="number"
                      step="0.01"
                      value={formData.scalping_take_profit_percent || 0.15}
                      onChange={(e) => setFormData({ ...formData, scalping_take_profit_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 0.15% (15 Pips)</p>
                  </div>

                  {/* NEU: Stop Loss % */}
                  <div className="space-y-2">
                    <Label htmlFor="scalping_sl">Stop Loss (%)</Label>
                    <Input
                      id="scalping_sl"
                      type="number"
                      step="0.01"
                      value={formData.scalping_stop_loss_percent || 0.08}
                      onChange={(e) => setFormData({ ...formData, scalping_stop_loss_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 0.08% (8 Pips)</p>
                  </div>

                  {/* NEU: Max Haltezeit */}
                  <div className="space-y-2">
                    <Label htmlFor="scalping_hold_time">Max Haltezeit (Min.)</Label>
                    <Input
                      id="scalping_hold_time"
                      type="number"
                      value={formData.scalping_max_hold_time_minutes || 5}
                      onChange={(e) => setFormData({ ...formData, scalping_max_hold_time_minutes: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 5 Minuten</p>
                  </div>

                  {/* NEU: Risiko pro Trade */}
                  <div className="space-y-2">
                    <Label htmlFor="scalping_risk">Risiko/Trade (%)</Label>
                    <Input
                      id="scalping_risk"
                      type="number"
                      step="0.1"
                      value={formData.scalping_risk_per_trade_percent || 0.5}
                      onChange={(e) => setFormData({ ...formData, scalping_risk_per_trade_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                    <p className="text-xs text-slate-500">Default: 0.5%</p>
                  </div>
                </div>

                {/* Warnung */}
                <div className="p-3 bg-amber-900/20 rounded border border-amber-700/50">
                  <p className="text-xs text-amber-400">
                    ⚠️ <strong>Scalping ist für Experten!</strong> Hohe Frequenz, kurze Haltezeiten, intensive Überwachung nötig.
                  </p>
                </div>
              </div>
              {/* Day Trading */}
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-cyan-400">Day Trading</h3>
                  <Switch
                    id="day_enabled"
                    checked={formData.day_trading_enabled || false}
                    onCheckedChange={(checked) => setFormData({ ...formData, day_trading_enabled: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="day_confidence">Min. Konfidenz (%)</Label>
                    <Input
                      id="day_confidence"
                      type="number"
                      step="0.01"
                      value={(formData.day_min_confidence_score || 0.4) * 100}
                      onChange={(e) => setFormData({ ...formData, day_min_confidence_score: parseFloat(e.target.value) / 100 })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="day_max_pos">Max. Positionen</Label>
                    <Input
                      id="day_max_pos"
                      type="number"
                      value={formData.day_max_positions || 10}
                      onChange={(e) => setFormData({ ...formData, day_max_positions: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="day_sl">Stop Loss (%)</Label>
                    <Input
                      id="day_sl"
                      type="number"
                      step="0.1"
                      value={formData.day_stop_loss_percent || 1.5}
                      onChange={(e) => setFormData({ ...formData, day_stop_loss_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="day_tp">Take Profit (%)</Label>
                    <Input
                      id="day_tp"
                      type="number"
                      step="0.1"
                      value={formData.day_take_profit_percent || 2.5}
                      onChange={(e) => setFormData({ ...formData, day_take_profit_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="day_risk">Risiko pro Trade (%)</Label>
                    <Input
                      id="day_risk"
                      type="number"
                      step="0.1"
                      value={formData.day_risk_per_trade_percent || 1.0}
                      onChange={(e) => setFormData({ ...formData, day_risk_per_trade_percent: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="day_hold">Max. Haltezeit (Stunden)</Label>
                    <Input
                      id="day_hold"
                      type="number"
                      value={formData.day_position_hold_time_hours || 2}
                      onChange={(e) => setFormData({ ...formData, day_position_hold_time_hours: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>
              </div>

            </TabsContent>

            {/* TAB 4: Risiko Management */}
            <TabsContent value="risk" className="space-y-6 mt-6">
              <div className="space-y-4 p-6 bg-slate-800 rounded-lg">
                <h3 className="text-lg font-semibold text-cyan-400">Globale Limits</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="max_trades_hour">Max. Trades pro Stunde</Label>
                    <Input
                      id="max_trades_hour"
                      type="number"
                      value={formData.max_trades_per_hour || 10}
                      onChange={(e) => setFormData({ ...formData, max_trades_per_hour: parseInt(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max_balance_percent">Max. Balance-Nutzung pro Plattform (%)</Label>
                    <Input
                      id="max_balance_percent"
                      type="number"
                      step="0.1"
                      value={formData.combined_max_balance_percent_per_platform || 20.0}
                      onChange={(e) => setFormData({ ...formData, combined_max_balance_percent_per_platform: parseFloat(e.target.value) })}
                      className="bg-slate-700 border-slate-600"
                    />
                  </div>
                </div>

                <div className="p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg">
                  <p className="text-sm text-yellow-200">
                    <strong>⚠️ Wichtig:</strong> Diese Limits schützen Ihr Kapital. Der Bot wird keine Trades öffnen, 
                    wenn diese Limits erreicht sind.
                  </p>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex gap-4 justify-end pt-4 border-t border-slate-700">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Abbrechen
            </Button>
            <Button type="submit" className="bg-cyan-600 hover:bg-cyan-700">
              Einstellungen speichern
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default SettingsDialog;
