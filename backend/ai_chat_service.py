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
    """Generate context about current trading state"""
    
    # Extract settings properly (handle both dict and None)
    auto_trading = settings.get('auto_trading', False) if settings else False
    use_ai = settings.get('use_ai_analysis', False) if settings else False
    swing_enabled = settings.get('swing_trading_enabled', True) if settings else True
    day_enabled = settings.get('day_trading_enabled', False) if settings else False
    swing_confidence = settings.get('swing_min_confidence_score', 0.6) if settings else 0.6
    day_confidence = settings.get('day_min_confidence_score', 0.4) if settings else 0.4
    max_balance_per_platform = settings.get('combined_max_balance_percent_per_platform', 20) if settings else 20
    
    context = f"""
Du bist ein intelligenter Trading-Assistent für die Rohstoff-Trading-Plattform mit DUAL TRADING STRATEGY.

AKTUELLE TRADING-EINSTELLUNGEN:
- Auto-Trading: {'✅ AKTIV' if auto_trading else '❌ INAKTIV'}
- AI-Analyse: {'✅ AKTIV' if use_ai else '❌ INAKTIV'}

DUAL TRADING STRATEGY (NEU!):
📈 Swing Trading: {'✅ AKTIV' if swing_enabled else '❌ INAKTIV'} (Langfristig, {swing_confidence*100:.0f}% Min. Confidence)
⚡ Day Trading: {'✅ AKTIV' if day_enabled else '❌ INAKTIV'} (Kurzfristig, {day_confidence*100:.0f}% Min. Confidence, Max 2h Haltezeit)

⚠️ WICHTIG: Beide Strategien zusammen nutzen maximal {max_balance_per_platform:.0f}% der Balance PRO Plattform!

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
    
    # Get Day Trading Settings (User's current settings)
    day_mode = settings.get('day_tp_sl_mode', 'percent') if settings else 'percent'
    if day_mode == 'euro':
        sl_euro = settings.get('day_stop_loss_euro', 7.0) if settings else 7.0
        tp_euro = settings.get('day_take_profit_euro', 7.0) if settings else 7.0
        context += f"\n\n📊 IHRE DAY TRADING EINSTELLUNGEN (EURO-Modus):\n"
        context += f"   Stop Loss: €{sl_euro}\n"
        context += f"   Take Profit: €{tp_euro}\n"
    else:
        sl_percent = settings.get('day_stop_loss_percent', 1.5) if settings else 1.5
        tp_percent = settings.get('day_take_profit_percent', 2.5) if settings else 2.5
        context += f"\n\n📊 IHRE DAY TRADING EINSTELLUNGEN (PROZENT-Modus):\n"
        context += f"   Stop Loss: {sl_percent}%\n"
        context += f"   Take Profit: {tp_percent}%\n"
    
    context += f"\nOFFENE TRADES: {len(open_trades)}"
    if open_trades:
        context += "\n"
        for i, trade in enumerate(open_trades[:10], 1):  # Show up to 10 trades with numbers
            commodity = trade.get('commodity', trade.get('symbol', 'UNKNOWN'))
            trade_type = trade.get('type', 'UNKNOWN')
            quantity = trade.get('quantity', trade.get('volume', 0))
            entry = trade.get('entry_price', trade.get('openPrice', trade.get('price', 0)))
            current = trade.get('price', entry)
            profit = trade.get('profit_loss', trade.get('profit', trade.get('unrealizedProfit', 0)))
            stop_loss = trade.get('stop_loss', trade.get('sl'))
            take_profit = trade.get('take_profit', trade.get('tp'))
            
            # Calculate recommended SL/TP based on Day Trading Settings
            if day_mode == 'euro':
                # EURO-Modus
                if trade_type == 'SELL':
                    recommended_sl = entry + (sl_euro / quantity)
                    recommended_tp = entry - (tp_euro / quantity)
                else:  # BUY
                    recommended_sl = entry - (sl_euro / quantity)
                    recommended_tp = entry + (tp_euro / quantity)
            else:
                # PROZENT-Modus
                if trade_type == 'SELL':
                    recommended_sl = entry * (1 + sl_percent / 100)
                    recommended_tp = entry * (1 - tp_percent / 100)
                else:  # BUY
                    recommended_sl = entry * (1 - sl_percent / 100)
                    recommended_tp = entry * (1 + tp_percent / 100)
            
            # Format SL/TP info with recommendations
            if stop_loss:
                sl_text = f"${stop_loss:.2f}"
            else:
                if day_mode == 'euro':
                    sl_text = f"NICHT GESETZT (Empfohlen: ${recommended_sl:.2f} bei €{sl_euro})"
                else:
                    sl_text = f"NICHT GESETZT (Empfohlen: ${recommended_sl:.2f} bei {sl_percent}%)"
            
            if take_profit:
                tp_text = f"${take_profit:.2f}"
            else:
                if day_mode == 'euro':
                    tp_text = f"NICHT GESETZT (Empfohlen: ${recommended_tp:.2f} bei €{tp_euro})"
                else:
                    tp_text = f"NICHT GESETZT (Empfohlen: ${recommended_tp:.2f} bei {tp_percent}%)"
            
            context += f"{i}. {commodity} {trade_type}\n"
            context += f"   Menge: {quantity}, Entry: ${entry:.2f}, Aktuell: ${current:.2f}\n"
            context += f"   P/L: ${profit:.2f}\n"
            context += f"   Stop Loss: {sl_text}\n"
            context += f"   Take Profit: {tp_text}\n"
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
