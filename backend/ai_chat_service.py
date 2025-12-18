"""
AI Chat Service for Trading Bot
Supports: GPT-5, Claude, and Ollama (local)
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize chat instance (will be set on first use)
_chat_instance = None

def get_trading_context(settings, latest_market_data, open_trades):
    """
    Generate context about current trading state
    V2.3.34: Alle 7 Trading-Strategien + Trailing Stop Support
    """
    
    # Extract settings properly (handle both dict and None)
    auto_trading = settings.get('auto_trading', False) if settings else False
    use_ai = settings.get('use_ai_analysis', False) if settings else False
    use_trailing_stop = settings.get('use_trailing_stop', True) if settings else True
    trailing_distance = settings.get('trailing_stop_distance', 1.5) if settings else 1.5
    
    # All 7 Trading Strategies
    swing_enabled = settings.get('swing_trading_enabled', True) if settings else True
    day_enabled = settings.get('day_trading_enabled', False) if settings else False
    scalping_enabled = settings.get('scalping_enabled', False) if settings else False
    mean_reversion_enabled = settings.get('mean_reversion_enabled', False) if settings else False
    momentum_enabled = settings.get('momentum_enabled', False) if settings else False
    breakout_enabled = settings.get('breakout_enabled', False) if settings else False
    grid_enabled = settings.get('grid_enabled', False) if settings else False
    
    swing_confidence = settings.get('swing_min_confidence_score', 0.6) if settings else 0.6
    day_confidence = settings.get('day_min_confidence_score', 0.4) if settings else 0.4
    max_balance_per_platform = settings.get('combined_max_balance_percent_per_platform', 20) if settings else 20
    
    context = f"""
Du bist ein intelligenter Trading-Assistent für die Rohstoff-Trading-Plattform mit 7 TRADING-STRATEGIEN.

AKTUELLE TRADING-EINSTELLUNGEN:
- Auto-Trading: {'✅ AKTIV' if auto_trading else '❌ INAKTIV'}
- AI-Analyse: {'✅ AKTIV' if use_ai else '❌ INAKTIV'}
- Trailing Stop: {'✅ AKTIV' if use_trailing_stop else '❌ INAKTIV'} ({trailing_distance}% Distanz)

📊 AKTIVE TRADING-STRATEGIEN:
📈 Swing Trading: {'✅' if swing_enabled else '❌'} (Langfristig, {swing_confidence*100:.0f}% Min.)
⚡ Day Trading: {'✅' if day_enabled else '❌'} (Kurzfristig, {day_confidence*100:.0f}% Min.)
🎯 Scalping: {'✅' if scalping_enabled else '❌'} (Ultra-schnell)
🔄 Mean Reversion: {'✅' if mean_reversion_enabled else '❌'} (Rückkehr zum Mittelwert)
📈 Momentum: {'✅' if momentum_enabled else '❌'} (Trend-Following)
💥 Breakout: {'✅' if breakout_enabled else '❌'} (Ausbrüche)
📐 Grid: {'✅' if grid_enabled else '❌'} (Seitwärtsmärkte)

⚠️ WICHTIG: Alle Strategien zusammen nutzen maximal {max_balance_per_platform:.0f}% der Balance PRO Plattform!

MARKTDATEN (Live):
"""
    
    # Add market hours info
    from commodity_processor import is_market_open, get_next_market_open
    context += "\n⏰ HANDELSZEITEN (wichtig für Trading-Entscheidungen):\n"
    context += "- Edelmetalle (Gold, Silber, Platin, Palladium): 24/5 (So 22:00 - Fr 21:00 UTC)\n"
    context += "- Energie (WTI, Brent, Gas): 24/5 (So 22:00 - Fr 21:00 UTC)\n"
    context += "- Agrar (Weizen, Mais, Soja, etc.): Mo-Fr 08:30-20:00 UTC\n"
    context += "- Forex (EUR/USD): 24/5 (So 22:00 - Fr 21:00 UTC)\n"
    context += "- Crypto (Bitcoin): 24/7\n\n"
    
    # Add market data for ALL available commodities
    if latest_market_data:
        commodity_count = 0
        for commodity_id, data in latest_market_data.items():
            if isinstance(data, dict) and 'price' in data:
                price = data.get('price', 0)
                signal = data.get('signal', 'HOLD')
                rsi = data.get('rsi', 50)
                market_status = "🟢 OFFEN" if is_market_open(commodity_id) else "🔴 GESCHLOSSEN"
                context += f"\n{commodity_id} {market_status}: ${price:.2f}, Signal: {signal}, RSI: {rsi:.1f}"
                commodity_count += 1
        
        if commodity_count == 0:
            context += "\n(Keine Marktdaten verfügbar)"
    
    # V2.3.34: Show SL/TP Settings for ALL 7 strategies
    context += "\n\n📊 SL/TP EINSTELLUNGEN ALLER STRATEGIEN:\n"
    
    # Day Trading
    if day_enabled:
        day_sl = settings.get('day_stop_loss_percent', 1.5) if settings else 1.5
        day_tp = settings.get('day_take_profit_percent', 2.5) if settings else 2.5
        context += f"⚡ Day Trading: SL {day_sl}% | TP {day_tp}%\n"
    
    # Swing Trading
    if swing_enabled:
        swing_sl = settings.get('swing_stop_loss_percent', 2.0) if settings else 2.0
        swing_tp = settings.get('swing_take_profit_percent', 4.0) if settings else 4.0
        context += f"📈 Swing Trading: SL {swing_sl}% | TP {swing_tp}%\n"
    
    # Scalping
    if scalping_enabled:
        scalp_sl = settings.get('scalping_stop_loss_percent', 0.5) if settings else 0.5
        scalp_tp = settings.get('scalping_take_profit_percent', 1.0) if settings else 1.0
        context += f"🎯 Scalping: SL {scalp_sl}% | TP {scalp_tp}%\n"
    
    # Mean Reversion
    if mean_reversion_enabled:
        mr_sl = settings.get('mean_reversion_stop_loss_percent', 2.0) if settings else 2.0
        mr_tp = settings.get('mean_reversion_take_profit_percent', 0.8) if settings else 0.8
        context += f"🔄 Mean Reversion: SL {mr_sl}% | TP {mr_tp}%\n"
    
    # Momentum
    if momentum_enabled:
        mom_sl = settings.get('momentum_stop_loss_percent', 2.5) if settings else 2.5
        mom_tp = settings.get('momentum_take_profit_percent', 5.0) if settings else 5.0
        context += f"🚀 Momentum: SL {mom_sl}% | TP {mom_tp}%\n"
    
    # Breakout
    if breakout_enabled:
        brk_sl = settings.get('breakout_stop_loss_percent', 2.0) if settings else 2.0
        brk_tp = settings.get('breakout_take_profit_percent', 3.0) if settings else 3.0
        context += f"💥 Breakout: SL {brk_sl}% | TP {brk_tp}%\n"
    
    # Grid
    if grid_enabled:
        grid_sl = settings.get('grid_stop_loss_percent', 1.5) if settings else 1.5
        grid_tp = settings.get('grid_tp_per_level_percent', 1.5) if settings else 1.5
        context += f"📐 Grid: SL {grid_sl}% | TP {grid_tp}%\n"
    
    # Trailing Stop Info
    if use_trailing_stop:
        context += f"\n🎯 TRAILING STOP: Aktiv mit {trailing_distance}% Distanz\n"
        context += "   → Stop Loss wird automatisch nachgezogen wenn der Preis in Gewinnrichtung geht\n"
    
    context += f"\nOFFENE TRADES: {len(open_trades)}"
    if open_trades:
        context += "\n"
        
        # Strategy emoji mapping
        strategy_emoji = {
            'day': '⚡', 'day_trading': '⚡',
            'swing': '📈', 'swing_trading': '📈',
            'scalping': '🎯',
            'mean_reversion': '🔄',
            'momentum': '🚀',
            'breakout': '💥',
            'grid': '📐'
        }
        
        for i, trade in enumerate(open_trades[:10], 1):  # Show up to 10 trades with numbers
            commodity = trade.get('commodity', trade.get('symbol', 'UNKNOWN'))
            trade_type = trade.get('type', 'UNKNOWN')
            quantity = trade.get('quantity', trade.get('volume', 0))
            entry = trade.get('entry_price', trade.get('openPrice', trade.get('price', 0)))
            current = trade.get('price', entry)
            profit = trade.get('profit_loss', trade.get('profit', trade.get('unrealizedProfit', 0)))
            stop_loss = trade.get('stop_loss', trade.get('sl'))
            take_profit = trade.get('take_profit', trade.get('tp'))
            
            # V2.3.34: Get trade strategy
            trade_strategy = trade.get('strategy', trade.get('strategy_type', 'unknown'))
            strategy_icon = strategy_emoji.get(trade_strategy.lower(), '📊')
            
            # Get the correct SL/TP percentages based on the trade's strategy
            strategy_settings = {
                'day': ('day_stop_loss_percent', 'day_take_profit_percent', 1.5, 2.5),
                'day_trading': ('day_stop_loss_percent', 'day_take_profit_percent', 1.5, 2.5),
                'swing': ('swing_stop_loss_percent', 'swing_take_profit_percent', 2.0, 4.0),
                'swing_trading': ('swing_stop_loss_percent', 'swing_take_profit_percent', 2.0, 4.0),
                'scalping': ('scalping_stop_loss_percent', 'scalping_take_profit_percent', 0.5, 1.0),
                'mean_reversion': ('mean_reversion_stop_loss_percent', 'mean_reversion_take_profit_percent', 2.0, 0.8),
                'momentum': ('momentum_stop_loss_percent', 'momentum_take_profit_percent', 2.5, 5.0),
                'breakout': ('breakout_stop_loss_percent', 'breakout_take_profit_percent', 2.0, 3.0),
                'grid': ('grid_stop_loss_percent', 'grid_tp_per_level_percent', 1.5, 1.5),
            }
            
            sl_key, tp_key, default_sl, default_tp = strategy_settings.get(
                trade_strategy.lower(), 
                ('day_stop_loss_percent', 'day_take_profit_percent', 1.5, 2.5)
            )
            
            sl_percent = settings.get(sl_key, default_sl) if settings else default_sl
            tp_percent = settings.get(tp_key, default_tp) if settings else default_tp
            
            # Calculate recommended SL/TP based on strategy
            if entry and entry > 0:
                if trade_type == 'SELL':
                    recommended_sl = entry * (1 + sl_percent / 100)
                    recommended_tp = entry * (1 - tp_percent / 100)
                else:  # BUY
                    recommended_sl = entry * (1 - sl_percent / 100)
                    recommended_tp = entry * (1 + tp_percent / 100)
            else:
                recommended_sl = 0
                recommended_tp = 0
            
            # Format SL/TP info with recommendations
            if stop_loss:
                sl_text = f"${stop_loss:.2f}"
            else:
                sl_text = f"NICHT GESETZT (Empfohlen: ${recommended_sl:.2f} bei {sl_percent}%)"
            
            if take_profit:
                tp_text = f"${take_profit:.2f}"
            else:
                tp_text = f"NICHT GESETZT (Empfohlen: ${recommended_tp:.2f} bei {tp_percent}%)"
            
            # Show trade with strategy info
            context += f"{i}. {strategy_icon} {commodity} {trade_type} [{trade_strategy.upper()}]\n"
            context += f"   Menge: {quantity}, Entry: ${entry:.2f}, Aktuell: ${current:.2f}\n"
            context += f"   P/L: ${profit:.2f}\n"
            context += f"   SL: {sl_text} | TP: {tp_text}\n"
        
        if len(open_trades) > 10:
            context += f"\n   ... und {len(open_trades) - 10} weitere Trades"
    else:
        context += "\n(Keine offenen Trades)"
    
    context += """

DEINE ROLLE & ANWEISUNGEN:
- Antworte KURZ und PRÄZISE (max 3-4 Sätze, außer bei detaillierten Analysen)
- Bei Fragen zu offenen Trades: Zeige KONKRET welche Trades offen sind (Rohstoff, Typ, Menge, Entry, P/L)
- Wenn Stop Loss/Take Profit "NICHT GESETZT" ist: SAGE DAS KLAR! Der Trade hat KEINE automatischen Exit-Limits
- Bei Fragen "Wann steigt Trade aus?": Wenn SL/TP nicht gesetzt → Sage: "KEIN automatischer Exit gesetzt"
- Wenn der Benutzer "Ja" oder "OK" sagt, führe die vorher vorgeschlagene Aktion aus
- Erkenne Kontext aus vorherigen Nachrichten
- KEINE vagen Antworten! Nutze die konkreten Daten aus dem Kontext oben
- Bei "Wie viele Trades" → Gib die EXAKTE Zahl und liste sie auf
- Bei Fragen wie "Wann tradest du?" → Erkläre KURZ die Entry-Bedingungen basierend auf aktuellen Signalen
- Nutze die AKTUELLEN Settings (siehe oben) - nicht raten!
- Wenn Auto-Trading AKTIV ist, sage das klar
- Antworte auf DEUTSCH

Du kannst:
1. Marktanalysen geben (basierend auf RSI, Signalen)
2. Erklären, warum Trades ausgeführt/nicht ausgeführt wurden
3. Trading-Empfehlungen geben
4. Settings überprüfen und erklären
"""
    
    return context



# AI Trading Tools - Echte Funktionen die die KI aufrufen kann
async def execute_trade_tool(symbol: str, direction: str, quantity: float = 0.01, db=None):
    """
    Führt einen Trade aus
    
    Args:
        symbol: Rohstoff (z.B. "WTI_CRUDE", "GOLD")
        direction: "BUY" oder "SELL"
        quantity: Menge in Lots (default 0.01)
    """
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES, is_market_open
        
        # Prüfe ob Markt offen
        if not is_market_open(symbol):
            return {"success": False, "message": f"Markt für {symbol} ist aktuell geschlossen"}
        
        # Hole Settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        default_platform = settings.get('default_platform', 'MT5_LIBERTEX') if settings else 'MT5_LIBERTEX'
        
        # Get commodity info
        commodity = COMMODITIES.get(symbol)
        if not commodity:
            return {"success": False, "message": f"Unbekanntes Symbol: {symbol}"}
        
        # Get MT5 symbol
        if default_platform == 'MT5_LIBERTEX':
            mt5_symbol = commodity.get('mt5_libertex_symbol')
        else:
            mt5_symbol = commodity.get('mt5_icmarkets_symbol')
        
        if not mt5_symbol:
            return {"success": False, "message": f"{symbol} nicht verfügbar auf {default_platform}"}
        
        # Connect to platform
        await multi_platform.connect_platform(default_platform)
        
        if default_platform not in multi_platform.platforms:
            return {"success": False, "message": f"{default_platform} nicht verbunden"}
        
        connector = multi_platform.platforms[default_platform].get('connector')
        if not connector:
            return {"success": False, "message": "Connector nicht verfügbar"}
        
        # Execute trade (OHNE SL/TP - KI überwacht)
        result = await connector.create_market_order(
            symbol=mt5_symbol,
            order_type=direction.upper(),
            volume=quantity,
            sl=None,
            tp=None
        )
        
        if result and (result.get('success') or result.get('orderId') or result.get('positionId')):
            ticket = result.get('orderId') or result.get('positionId')
            return {
                "success": True, 
                "message": f"✅ Trade ausgeführt: {direction} {symbol} @ {quantity} Lots, Ticket #{ticket}",
                "ticket": ticket
            }
        else:
            return {"success": False, "message": "Trade fehlgeschlagen"}
            
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        return {"success": False, "message": str(e)}

async def close_trade_tool(ticket: str, db=None):
    """Schließt einen Trade per Ticket-Nummer"""
    try:
        from multi_platform_connector import multi_platform
        
        # Try both platforms
        for platform_name in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
            if platform_name in multi_platform.platforms:
                connector = multi_platform.platforms[platform_name].get('connector')
                if connector:
                    success = await connector.close_position(ticket)
                    if success:
                        return {"success": True, "message": f"✅ Trade #{ticket} geschlossen"}
        
        return {"success": False, "message": f"Trade #{ticket} nicht gefunden"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

async def close_all_trades_tool(db=None):
    """Schließt ALLE offenen Trades"""
    try:
        from multi_platform_connector import multi_platform
        
        closed_count = 0
        for platform_name in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
            if platform_name in multi_platform.platforms:
                connector = multi_platform.platforms[platform_name].get('connector')
                if connector:
                    positions = await connector.get_positions()
                    for pos in positions:
                        ticket = pos.get('positionId') or pos.get('ticket')
                        success = await connector.close_position(str(ticket))
                        if success:
                            closed_count += 1
        
        return {"success": True, "message": f"✅ {closed_count} Trades geschlossen"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

async def close_trades_by_symbol_tool(symbol: str, db=None):
    """Schließt alle Trades eines bestimmten Symbols"""
    try:
        from multi_platform_connector import multi_platform
        from commodity_processor import COMMODITIES
        
        commodity = COMMODITIES.get(symbol)
        if not commodity:
            return {"success": False, "message": f"Unbekanntes Symbol: {symbol}"}
        
        closed_count = 0
        for platform_name in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
            if platform_name in multi_platform.platforms:
                connector = multi_platform.platforms[platform_name].get('connector')
                if connector:
                    positions = await connector.get_positions()
                    
                    # Get MT5 symbols for this commodity
                    mt5_symbols = [
                        commodity.get('mt5_libertex_symbol'),
                        commodity.get('mt5_icmarkets_symbol')
                    ]
                    
                    for pos in positions:
                        pos_symbol = pos.get('symbol')
                        if pos_symbol in mt5_symbols:
                            ticket = pos.get('positionId') or pos.get('ticket')
                            success = await connector.close_position(str(ticket))
                            if success:
                                closed_count += 1
        
        return {"success": True, "message": f"✅ {closed_count} {symbol} Trades geschlossen"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

async def get_open_positions_tool(db=None):
    """Zeigt alle offenen Positionen"""
    try:
        from multi_platform_connector import multi_platform
        
        all_positions = []
        for platform_name in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
            if platform_name in multi_platform.platforms:
                connector = multi_platform.platforms[platform_name].get('connector')
                if connector:
                    positions = await connector.get_positions()
                    for pos in positions:
                        all_positions.append({
                            "ticket": pos.get('positionId') or pos.get('ticket'),
                            "symbol": pos.get('symbol'),
                            "type": pos.get('type'),
                            "volume": pos.get('volume'),
                            "openPrice": pos.get('openPrice'),
                            "currentPrice": pos.get('currentPrice'),
                            "profit": pos.get('profit'),
                            "platform": platform_name
                        })
        
        if not all_positions:
            return {"success": True, "message": "Keine offenen Positionen", "positions": []}
        
        # Format message
        msg = f"📊 {len(all_positions)} offene Position(en):\n"
        for pos in all_positions:
            msg += f"- {pos['symbol']} {pos['type']} #{pos['ticket']}: {pos['volume']} @ {pos['openPrice']}, P/L: ${pos['profit']:.2f}\n"
        
        return {"success": True, "message": msg, "positions": all_positions}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


async def toggle_strategy_tool(strategy: str, enabled: bool, db=None):
    """
    V2.3.34: Aktiviert/Deaktiviert eine Trading-Strategie
    
    Args:
        strategy: Name der Strategie (day, swing, scalping, mean_reversion, momentum, breakout, grid)
        enabled: True zum Aktivieren, False zum Deaktivieren
    """
    try:
        strategy_keys = {
            'day': 'day_trading_enabled',
            'day_trading': 'day_trading_enabled',
            'swing': 'swing_trading_enabled',
            'swing_trading': 'swing_trading_enabled',
            'scalping': 'scalping_enabled',
            'mean_reversion': 'mean_reversion_enabled',
            'momentum': 'momentum_enabled',
            'breakout': 'breakout_enabled',
            'grid': 'grid_enabled'
        }
        
        key = strategy_keys.get(strategy.lower())
        if not key:
            return {"success": False, "message": f"Unbekannte Strategie: {strategy}"}
        
        # Update settings in database
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {key: enabled}}
        )
        
        action = "aktiviert ✅" if enabled else "deaktiviert ❌"
        return {"success": True, "message": f"Strategie '{strategy.upper()}' wurde {action}"}
        
    except Exception as e:
        logger.error(f"Error toggling strategy: {e}")
        return {"success": False, "message": str(e)}


async def toggle_auto_trading_tool(enabled: bool, db=None):
    """
    V2.3.34: Aktiviert/Deaktiviert Auto-Trading
    """
    try:
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"auto_trading": enabled}}
        )
        
        if enabled:
            return {"success": True, "message": "🤖 Auto-Trading wurde AKTIVIERT!\n\nDer Bot wird jetzt automatisch Trades basierend auf den aktiven Strategien eröffnen."}
        else:
            return {"success": True, "message": "⏸️ Auto-Trading wurde DEAKTIVIERT.\n\nKeine neuen automatischen Trades werden eröffnet. Bestehende Trades bleiben offen."}
        
    except Exception as e:
        logger.error(f"Error toggling auto trading: {e}")
        return {"success": False, "message": str(e)}


async def update_sl_tp_tool(strategy: str, sl_percent: float = None, tp_percent: float = None, db=None):
    """
    V2.3.34: Aktualisiert SL/TP Prozente für eine Strategie
    
    Args:
        strategy: Name der Strategie
        sl_percent: Neuer Stop Loss Prozent (optional)
        tp_percent: Neuer Take Profit Prozent (optional)
    """
    try:
        strategy_keys = {
            'day': ('day_stop_loss_percent', 'day_take_profit_percent'),
            'day_trading': ('day_stop_loss_percent', 'day_take_profit_percent'),
            'swing': ('swing_stop_loss_percent', 'swing_take_profit_percent'),
            'swing_trading': ('swing_stop_loss_percent', 'swing_take_profit_percent'),
            'scalping': ('scalping_stop_loss_percent', 'scalping_take_profit_percent'),
            'mean_reversion': ('mean_reversion_stop_loss_percent', 'mean_reversion_take_profit_percent'),
            'momentum': ('momentum_stop_loss_percent', 'momentum_take_profit_percent'),
            'breakout': ('breakout_stop_loss_percent', 'breakout_take_profit_percent'),
            'grid': ('grid_stop_loss_percent', 'grid_tp_per_level_percent'),
        }
        
        keys = strategy_keys.get(strategy.lower())
        if not keys:
            return {"success": False, "message": f"Unbekannte Strategie: {strategy}"}
        
        sl_key, tp_key = keys
        update_data = {}
        
        if sl_percent is not None:
            update_data[sl_key] = sl_percent
        if tp_percent is not None:
            update_data[tp_key] = tp_percent
        
        if not update_data:
            return {"success": False, "message": "Kein SL oder TP Wert angegeben"}
        
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": update_data}
        )
        
        msg = f"✅ {strategy.upper()} Settings aktualisiert:\n"
        if sl_percent is not None:
            msg += f"   Stop Loss: {sl_percent}%\n"
        if tp_percent is not None:
            msg += f"   Take Profit: {tp_percent}%\n"
        
        return {"success": True, "message": msg}
        
    except Exception as e:
        logger.error(f"Error updating SL/TP: {e}")
        return {"success": False, "message": str(e)}


async def get_portfolio_summary_tool(db=None):
    """
    V2.3.34: Zeigt eine Zusammenfassung des Portfolios
    """
    try:
        from multi_platform_connector import multi_platform
        
        summary = "📊 PORTFOLIO ZUSAMMENFASSUNG\n\n"
        total_balance = 0
        total_equity = 0
        total_profit = 0
        total_positions = 0
        
        for platform_name in ['MT5_LIBERTEX', 'MT5_ICMARKETS']:
            if platform_name in multi_platform.platforms:
                connector = multi_platform.platforms[platform_name].get('connector')
                if connector:
                    try:
                        account_info = await connector.get_account_information()
                        positions = await connector.get_positions()
                        
                        balance = account_info.get('balance', 0)
                        equity = account_info.get('equity', 0)
                        profit = equity - balance
                        
                        total_balance += balance
                        total_equity += equity
                        total_profit += profit
                        total_positions += len(positions)
                        
                        summary += f"💰 {platform_name}:\n"
                        summary += f"   Balance: €{balance:.2f}\n"
                        summary += f"   Equity: €{equity:.2f}\n"
                        summary += f"   P/L: €{profit:+.2f}\n"
                        summary += f"   Positionen: {len(positions)}\n\n"
                    except Exception as e:
                        logger.error(f"Error getting info for {platform_name}: {e}")
        
        summary += f"📈 GESAMT:\n"
        summary += f"   Balance: €{total_balance:.2f}\n"
        summary += f"   Equity: €{total_equity:.2f}\n"
        summary += f"   P/L: €{total_profit:+.2f}\n"
        summary += f"   Offene Positionen: {total_positions}"
        
        return {"success": True, "message": summary}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


async def get_ai_chat_instance(settings, ai_provider="openai", model="gpt-5", session_id="default-session"):
    """Get or create AI chat instance with session context"""
    global _chat_instance
    
    try:
        if ai_provider == "ollama":
            # Ollama support for local AI
            import aiohttp
            
            # Get Ollama base URL from settings
            ollama_base_url = settings.get('ollama_base_url', 'http://127.0.0.1:11434')
            
            # 🐛 FIX v2.3.30: Verwende ai_model (vom User gewählt) anstatt ollama_model
            # Das ai_model wird in den Settings vom User ausgewählt (z.B. "llama3.2", "mistral")
            ollama_model = model or settings.get('ai_model') or settings.get('ollama_model', 'llama3:latest')
            
            # Füge ":latest" Tag hinzu falls nicht vorhanden (für Ollama Kompatibilität)
            if ollama_model and ':' not in ollama_model:
                ollama_model = f"{ollama_model}:latest"
            
            logger.info(f"🏠 Initializing Ollama: {ollama_base_url} with model {ollama_model}")
            
            class OllamaChat:
                def __init__(self, base_url, model):
                    self.base_url = base_url
                    self.model = model or "llama3"
                    self.history = []
                
                async def send_message(self, message):
                    self.history.append({"role": "user", "content": message})
                    
                    try:
                        async with aiohttp.ClientSession() as session:
                            payload = {
                                "model": self.model,
                                "messages": self.history,
                                "stream": False
                            }
                            
                            logger.info(f"🔄 Sending request to Ollama: {self.base_url}/api/chat")
                            
                            async with session.post(
                                f"{self.base_url}/api/chat", 
                                json=payload,
                                timeout=aiohttp.ClientTimeout(total=60)
                            ) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    assistant_msg = result.get('message', {}).get('content', '')
                                    self.history.append({"role": "assistant", "content": assistant_msg})
                                    logger.info(f"✅ Ollama response received")
                                    return assistant_msg
                                else:
                                    error_text = await response.text()
                                    logger.error(f"❌ Ollama error: {response.status} - {error_text}")
                                    return f"Fehler: Ollama Server antwortet mit Fehler {response.status}. Bitte prüfen Sie, ob Ollama läuft: `ollama serve`"
                    except aiohttp.ClientConnectorError:
                        logger.error(f"❌ Ollama nicht erreichbar: {self.base_url}")
                        return f"❌ Fehler: Ollama nicht erreichbar unter {self.base_url}.\n\n🔧 Lösungen:\n1. Starten Sie Ollama: `ollama serve`\n2. Prüfen Sie, ob Ollama läuft: `ollama list`\n3. Testen Sie manuell: `curl {self.base_url}/api/tags`"
                    except Exception as e:
                        logger.error(f"❌ Ollama Fehler: {e}")
                        return f"Fehler bei Ollama-Anfrage: {str(e)}"
            
            return OllamaChat(ollama_base_url, ollama_model)
        
        else:
            # Use Emergentintegrations for GPT-5/Claude (with fallback)
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
            except ImportError:
                from llm_fallback import get_llm_chat, get_user_message
                LlmChat = get_llm_chat
                UserMessage = get_user_message
            
            # Get API key based on provider
            # Priority: Settings API Keys > Emergent LLM Key (for emergent provider)
            api_key = None
            
            if ai_provider.lower() == "emergent":
                # Use Emergent LLM Key (universal key)
                api_key = os.getenv('EMERGENT_LLM_KEY')
                if not api_key:
                    raise Exception("EMERGENT_LLM_KEY not found. Please add balance or switch to another provider.")
            elif ai_provider.lower() == "openai":
                # Use OpenAI API key from settings or fallback to emergent
                api_key = settings.get('openai_api_key') or os.getenv('EMERGENT_LLM_KEY')
            elif ai_provider.lower() in ["gemini", "google"]:
                # Use Gemini API key from settings
                api_key = settings.get('gemini_api_key')
                if not api_key:
                    raise Exception("Gemini API Key nicht gefunden! Bitte in Einstellungen eintragen oder zu Emergent wechseln.")
            elif ai_provider.lower() in ["anthropic", "claude"]:
                # Use Anthropic API key from settings or fallback to emergent
                api_key = settings.get('anthropic_api_key') or os.getenv('EMERGENT_LLM_KEY')
            elif ai_provider.lower() == "ollama":
                # Ollama doesn't need API key
                api_key = "ollama-local"
            else:
                # Default to Emergent LLM Key
                api_key = os.getenv('EMERGENT_LLM_KEY')
            
            if not api_key:
                raise Exception(f"Kein API-Key für Provider '{ai_provider}' gefunden. Bitte in Einstellungen eintragen.")
            
            logger.info(f"Using API key for provider: {ai_provider} (from {'settings' if ai_provider != 'emergent' and settings.get(f'{ai_provider}_api_key') else 'environment'})")
            
            # Determine provider and model
            provider_map = {
                "openai": ("openai", model or "gpt-5"),
                "anthropic": ("anthropic", model or "claude-4-sonnet-20250514"),
                "claude": ("anthropic", "claude-4-sonnet-20250514"),
                "gemini": ("gemini", model or "gemini-2.5-pro"),
                "google": ("gemini", model or "gemini-2.5-pro"),
                "emergent": ("openai", model or "gpt-5")  # Emergent uses OpenAI-compatible format
            }
            
            provider, model_name = provider_map.get(ai_provider.lower(), ("openai", "gpt-5"))
            
            # System message - AI Chat kann IMMER Trades ausführen (unabhängig von Auto-Trading Status)
            # Auto-Trading bezieht sich nur auf den autonomen Bot, nicht auf AI Chat
            auto_trading_active = settings.get('auto_trading', False)
            
            system_message = f"""Du bist ein DIREKTER Trading-Assistent. KEINE langen Analysen, NUR Aktionen!

🚨 KRITISCHE REGEL: Bei klaren Befehlen → SOFORT AUSFÜHREN, NICHT ANALYSIEREN!

VERFÜGBARE AKTIONEN:
1. execute_trade - Platziert einen Trade
2. close_trade - Schließt einen Trade per Ticket
3. close_all_trades - Schließt ALLE offenen Trades
4. close_trades_by_symbol - Schließt alle Trades eines Symbols
5. get_open_positions - Zeigt alle offenen Positionen

DIREKTES AUSFÜHREN bei diesen Befehlen:
- "Schließe alle" / "Close all" → SOFORT close_all_trades() ausführen
- "Schließe alle positiven" → SOFORT profitable Trades schließen
- "Schließe alle negativen" → SOFORT verlust-Trades schließen
- "Schließe Gold" → SOFORT close_trades_by_symbol("GOLD")
- "Kaufe Gold" → SOFORT execute_trade("GOLD", "BUY", 0.01)
- "Verkaufe WTI" → SOFORT execute_trade("WTI_CRUDE", "SELL", 0.01)

ANTWORT-FORMAT:
✅ "Aktion ausgeführt" (1 kurzer Satz)
❌ NICHT: Lange Analysen, Erklärungen, Marktbedingungen, RSI-Werte, etc.

NUR bei unklaren Fragen → kurze Nachfrage

SYMBOL-MAPPING:
Gold→GOLD, Silber→SILVER, WTI/Öl→WTI_CRUDE, EUR→EURUSD, Platin→PLATINUM, Palladium→PALLADIUM, Brent→BRENT_CRUDE
"""
            
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,  # Use dynamic session_id from parameter
                system_message=system_message
            ).with_model(provider, model_name)
            
            logger.info(f"✅ AI Chat initialized: {provider}/{model_name}")
            return chat
            
    except Exception as e:
        logger.error(f"Error initializing AI chat: {e}")
        raise


async def handle_trading_actions(user_message: str, ai_response: str, db, settings: dict, latest_market_data: dict) -> str:
    """
    Parse user message and AI response for trading actions
    Simple keyword-based detection for MVP
    """
    # Function map for AI tools
    FUNCTION_MAP = {
        'execute_trade': lambda symbol, direction, quantity=0.01: execute_trade_tool(symbol, direction, quantity, db),
        'close_trade': lambda ticket: close_trade_tool(ticket, db),
        'close_all_trades': lambda: close_all_trades_tool(db),
        'close_trades_by_symbol': lambda symbol: close_trades_by_symbol_tool(symbol, db),
        'get_open_positions': lambda: get_open_positions_tool(db)
    }
    
    user_lower = user_message.lower().strip()
    
    try:
        # Check for confirmation words + symbol (e.g. "Ja, Gold kaufen")
        # This handles cases where user confirms with additional context
        is_confirmation = any(keyword in user_lower for keyword in ['ja', 'ok', 'okay', 'yes', 'mach', 'los', 'gut'])
        
        # If it's a confirmation AND there's a trading keyword, treat as command
        if is_confirmation:
            # Check if there's a trading keyword in this confirmation
            has_trade_keyword = any(keyword in user_lower for keyword in ['kauf', 'verkauf', 'buy', 'sell', 'schließ', 'close', 'gold', 'silver', 'wti', 'eur', 'öl'])
            if not has_trade_keyword:
                # Pure confirmation without specific command - let AI handle context from history
                logger.info(f"⚠️ Confirmation detected but no specific command: '{user_message}'")
                # Don't return here - let the command detection below handle any embedded commands
        
        # Close all PROFITABLE positions (positive trades)
        if any(keyword in user_lower for keyword in ['schließe alle positiven', 'close all profitable', 'alle gewinne', 'close profitable']):
            logger.info(f"🎯 Detected close all PROFITABLE trades command")
            # Get open trades with profit
            from multi_platform_connector import multi_platform
            all_positions = []
            for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                try:
                    positions = await multi_platform.get_open_positions(platform_name)
                    all_positions.extend([(pos, platform_name) for pos in positions])
                except Exception as e:
                    logger.error(f"Error fetching positions from {platform_name}: {e}")
            
            closed_count = 0
            for pos, platform in all_positions:
                profit = pos.get('profit', 0)
                if profit > 0:  # Only close profitable trades
                    ticket = pos.get('ticket') or pos.get('id')
                    try:
                        await multi_platform.close_position(platform, ticket)
                        closed_count += 1
                        logger.info(f"✅ Closed profitable trade #{ticket} (Profit: ${profit:.2f})")
                    except Exception as e:
                        logger.error(f"Error closing trade #{ticket}: {e}")
            
            return f"✅ {closed_count} profitable Trades geschlossen"
        
        # Close all LOSING positions (negative trades)
        if any(keyword in user_lower for keyword in ['schließe alle negativen', 'close all losing', 'alle verluste', 'close losing']):
            logger.info(f"🎯 Detected close all LOSING trades command")
            from multi_platform_connector import multi_platform
            all_positions = []
            for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                try:
                    positions = await multi_platform.get_open_positions(platform_name)
                    all_positions.extend([(pos, platform_name) for pos in positions])
                except Exception as e:
                    logger.error(f"Error fetching positions from {platform_name}: {e}")
            
            closed_count = 0
            for pos, platform in all_positions:
                profit = pos.get('profit', 0)
                if profit < 0:  # Only close losing trades
                    ticket = pos.get('ticket') or pos.get('id')
                    try:
                        await multi_platform.close_position(platform, ticket)
                        closed_count += 1
                        logger.info(f"✅ Closed losing trade #{ticket} (Loss: ${profit:.2f})")
                    except Exception as e:
                        logger.error(f"Error closing trade #{ticket}: {e}")
            
            return f"✅ {closed_count} losing Trades geschlossen"
        
        # Close all positions
        if any(keyword in user_lower for keyword in ['schließe alle', 'close all', 'alle positionen schließen']):
            logger.info(f"🎯 Detected close all command")
            result = await close_all_trades_tool(db=db)
            logger.info(f"📊 Close all result: {result}")
            return result.get('message', 'Aktion ausgeführt')
        
        # Close specific symbol
        for symbol in ['gold', 'silver', 'wti', 'brent', 'platin', 'palladium', 'eur', 'euro']:
            if f'schließe {symbol}' in user_lower or f'close {symbol}' in user_lower:
                symbol_map = {
                    'gold': 'GOLD', 'silver': 'SILVER', 
                    'wti': 'WTI_CRUDE', 'brent': 'BRENT_CRUDE',
                    'platin': 'PLATINUM', 'palladium': 'PALLADIUM',
                    'eur': 'EURUSD', 'euro': 'EURUSD'
                }
                logger.info(f"🎯 Detected close command for: {symbol}")
                result = await close_trades_by_symbol_tool(symbol=symbol_map.get(symbol, symbol.upper()), db=db)
                logger.info(f"📊 Close result: {result}")
                return result.get('message', 'Aktion ausgeführt')
        
        # Show positions
        if any(keyword in user_lower for keyword in ['zeige positionen', 'show positions', 'offene trades']):
            logger.info(f"🎯 Detected show positions command")
            result = await get_open_positions_tool(db=db)
            logger.info(f"📊 Positions result: {result}")
            return result.get('message', 'Aktion ausgeführt')
        
        # Buy/Sell detection - erweiterte Symbole
        for direction in ['buy', 'kaufe', 'long', 'sell', 'verkaufe', 'short']:
            if direction in user_lower:
                # Extract symbol - erweiterte Liste mit EUR
                for symbol_key, symbol_value in {
                    'gold': 'GOLD', 'silver': 'SILVER', 'silber': 'SILVER',
                    'wti': 'WTI_CRUDE', 'öl': 'WTI_CRUDE', 'oil': 'WTI_CRUDE',
                    'brent': 'BRENT_CRUDE', 'platin': 'PLATINUM', 'platinum': 'PLATINUM',
                    'palladium': 'PALLADIUM', 'kupfer': 'COPPER', 'copper': 'COPPER',
                    'eur': 'EURUSD', 'euro': 'EURUSD', 'eurusd': 'EURUSD'
                }.items():
                    if symbol_key in user_lower:
                        trade_direction = 'BUY' if direction in ['buy', 'kaufe', 'long'] else 'SELL'
                        logger.info(f"🎯 Detected trade command: {trade_direction} {symbol_value}")
                        result = await execute_trade_tool(
                            symbol=symbol_value,
                            direction=trade_direction,
                            quantity=0.01,
                            db=db
                        )
                        logger.info(f"📊 Trade result: {result}")
                        return result.get('message', 'Trade ausgeführt')
        
        return None
        
    except Exception as e:
        logger.error(f"Error in trading actions: {e}")
        return None


async def send_chat_message(message: str, settings: dict, latest_market_data: dict, open_trades: list, ai_provider: str = "openai", model: str = None, session_id: str = "default-session", db=None):
    """Send a message to the AI and get response with session context and function calling"""
    try:
        # Get AI chat instance with session_id
        chat = await get_ai_chat_instance(settings, ai_provider, model, session_id)
        
        # Only add trading context for non-confirmation messages
        # Short messages like "Ja", "OK", "Nein" are likely confirmations
        is_confirmation = message.strip().lower() in ['ja', 'ok', 'okay', 'yes', 'nein', 'no', 'nope']
        
        # Check if auto-trading is active for function calling
        auto_trading_active = settings.get('auto_trading', False)
        
        if is_confirmation:
            # For confirmations, send message as-is without context
            full_message = message
        else:
            # Add trading context for new questions
            context = get_trading_context(settings, latest_market_data, open_trades)
            full_message = f"{context}\n\nBENUTZER FRAGE: {message}"
        
        # Send message based on provider type
        if ai_provider == "ollama":
            # Ollama
            response = await chat.send_message(full_message)
        else:
            # Emergentintegrations - send_message is async (with fallback)
            try:
                from emergentintegrations.llm.chat import UserMessage
            except ImportError:
                from llm_fallback import get_user_message
                UserMessage = get_user_message
            user_msg = UserMessage(text=full_message)
            
            # send_message returns AssistantMessage - await it!
            response_obj = await chat.send_message(user_msg)
            
            # Extract text from response
            if hasattr(response_obj, 'text'):
                response = response_obj.text
            elif isinstance(response_obj, str):
                response = response_obj
            else:
                response = str(response_obj)
        
        logger.info(f"✅ AI Response generated (length: {len(response)})")
        
        # Function calling: ALWAYS check if user wants to execute trades (AI Chat is independent of Auto-Trading)
        # Auto-Trading controls the autonomous bot, not the AI Chat
        if db is not None:
            logger.info(f"🔍 Checking for trading actions in user message: '{message}'")
            action_result = await handle_trading_actions(message, response, db, settings, latest_market_data)
            if action_result:
                logger.info(f"✅ Trading action executed: {action_result}")
                # Append action result to response
                response = f"{response}\n\n{action_result}"
            else:
                logger.info("ℹ️ No trading action detected in message")
        
        return {
            "success": True,
            "response": response,
            "provider": ai_provider,
            "model": model or "default"
        }
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        return {
            "success": False,
            "response": f"Fehler: {str(e)}",
            "provider": ai_provider
        }
