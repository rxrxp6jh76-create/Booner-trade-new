"""
AI-Powered Position Manager
Überwacht ALLE offenen Positionen (manuell & automatisch) und schließt sie intelligent
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def manage_open_positions(db, current_prices: dict, settings):
    """
    KI-gestützte Positionsverwaltung für ALLE offenen Trades
    Schließt Positionen automatisch bei:
    - Stop Loss erreicht
    - Take Profit erreicht
    - KI-Signal zum Schließen (Trendwende)
    
    WICHTIG: Verwendet strategie-spezifische SL/TP aus trade_settings!
    """
    try:
        if not settings or not settings.get('use_ai_analysis'):
            return
        
        # Hole alle offenen Positionen
        cursor = await db.trades.find({"status": "OPEN"})
        open_trades = await cursor.to_list(1000)
        
        if not open_trades:
            return
        
        logger.info(f"AI Position Manager: Überwache {len(open_trades)} offene Positionen")
        
        closed_count = 0
        
        for trade in open_trades:
            commodity = trade.get('commodity', 'WTI_CRUDE')
            current_price = current_prices.get(commodity)
            
            if not current_price:
                continue
            
            trade_type = trade.get('type')
            entry_price = trade.get('entry_price')
            quantity = trade.get('quantity', 1.0)
            ticket = trade.get('mt5_ticket') or trade.get('ticket')
            
            # Hole Strategie aus trade_settings (oder fallback zu Trade-Objekt)
            trade_settings_doc = await db.trade_settings.find_one({'trade_id': str(ticket)})
            if trade_settings_doc:
                strategy = trade_settings_doc.get('strategy', 'day')
            else:
                strategy = trade.get('strategy', 'day')
            
            # WICHTIG: Berechne SL/TP DYNAMISCH aus AKTUELLEN Settings (nicht gespeichert!)
            # So werden Trades automatisch angepasst wenn User Settings ändert!
            if strategy == "swing":
                tp_sl_mode = settings.get('swing_tp_sl_mode', 'percent')
                if tp_sl_mode == 'euro':
                    tp_euro = settings.get('swing_take_profit_euro', 50.0)
                    sl_euro = settings.get('swing_stop_loss_euro', 20.0)
                    # Euro zu Punkten: Bei 0.01 Lot (z.B. Gold) = 1 oz = 1€ pro Punkt
                    # Bei anderen Lots entsprechend skalieren
                    lot_multiplier = quantity / 0.01  # Anzahl der 0.01 Lots
                    tp_points = tp_euro / lot_multiplier if lot_multiplier > 0 else tp_euro
                    sl_points = sl_euro / lot_multiplier if lot_multiplier > 0 else sl_euro
                else:
                    tp_percent = settings.get('swing_take_profit_percent', 4.0)
                    sl_percent = settings.get('swing_stop_loss_percent', 2.0)
                    tp_points = entry_price * (tp_percent / 100)
                    sl_points = entry_price * (sl_percent / 100)
            else:  # day trading
                tp_sl_mode = settings.get('day_tp_sl_mode', 'euro')
                if tp_sl_mode == 'euro':
                    tp_euro = settings.get('day_take_profit_euro', 10.0)
                    sl_euro = settings.get('day_stop_loss_euro', 15.0)
                    # Euro zu Punkten: Bei 0.01 Lot = 1€ pro Punkt
                    lot_multiplier = quantity / 0.01
                    tp_points = tp_euro / lot_multiplier if lot_multiplier > 0 else tp_euro
                    sl_points = sl_euro / lot_multiplier if lot_multiplier > 0 else sl_euro
                else:
                    tp_percent = settings.get('day_take_profit_percent', 2.5)
                    sl_percent = settings.get('day_stop_loss_percent', 1.5)
                    tp_points = entry_price * (tp_percent / 100)
                    sl_points = entry_price * (sl_percent / 100)
            
            # Berechne SL/TP basierend auf aktueller Entry Price
            if trade_type == 'BUY':
                stop_loss = entry_price - sl_points
                take_profit = entry_price + tp_points
            else:  # SELL
                stop_loss = entry_price + sl_points
                take_profit = entry_price - tp_points
            
            logger.debug(f"📊 Trade #{ticket} ({strategy}): Dynamisch berechnet SL={stop_loss:.2f}, TP={take_profit:.2f}")
            
            should_close = False
            close_reason = None
            
            # BUY Position Management
            if trade_type == 'BUY':
                # Gewinn berechnen
                profit = (current_price - entry_price) * quantity
                profit_percent = ((current_price - entry_price) / entry_price) * 100
                
                # Take Profit erreicht?
                if take_profit and current_price >= take_profit:
                    should_close = True
                    close_reason = f"Take Profit erreicht (+{profit_percent:.2f}%)"
                
                # Stop Loss erreicht?
                elif stop_loss and current_price <= stop_loss:
                    should_close = True
                    close_reason = f"Stop Loss getroffen ({profit_percent:.2f}%)"
                
                # V2.5.1: DEAKTIVIERT - Diese Logik schließt Trades zu früh!
                # KI-Signal Trendwende war zu aggressiv und führte zu sofortigem Schließen
                # elif profit_percent > 1.0:  # Mindestens 1% Gewinn
                #     market_data = await db.market_data.find_one(...)
                #     ... (Trendwende-Logik deaktiviert)
                
                # V2.5.1: DEAKTIVIERT - Gewinnmitnahme bei 5% war zu niedrig
                # elif profit_percent > 5.0:
                #     should_close = True
                #     close_reason = f"Gewinnmitnahme bei +{profit_percent:.2f}%"
            
            # SELL Position Management
            elif trade_type == 'SELL':
                # Gewinn berechnen (bei SELL profitiert man von fallendem Preis)
                profit = (entry_price - current_price) * quantity
                profit_percent = ((entry_price - current_price) / entry_price) * 100
                
                # Take Profit erreicht?
                if take_profit and current_price <= take_profit:
                    should_close = True
                    close_reason = f"Take Profit erreicht (+{profit_percent:.2f}%)"
                
                # Stop Loss erreicht?
                elif stop_loss and current_price >= stop_loss:
                    should_close = True
                    close_reason = f"Stop Loss getroffen ({profit_percent:.2f}%)"
                
                # V2.5.1: DEAKTIVIERT - Diese Logik schließt Trades zu früh!
                # KI-Signal Trendwende war zu aggressiv
                # elif profit_percent > 1.0:
                #     ... (Trendwende-Logik deaktiviert)
                
                # V2.5.1: DEAKTIVIERT - Gewinnmitnahme bei 5% war zu niedrig
                # elif profit_percent > 5.0:
                #     should_close = True
                #     close_reason = f"Gewinnmitnahme bei +{profit_percent:.2f}%"
            
            # Position schließen?
            if should_close:
                profit_loss = (current_price - entry_price) * quantity if trade_type == 'BUY' else (entry_price - current_price) * quantity
                
                await db.trades.update_one(
                    {"id": trade['id']},
                    {
                        "$set": {
                            "status": "CLOSED",
                            "exit_price": current_price,
                            "profit_loss": profit_loss,
                            "closed_at": datetime.now(timezone.utc),
                            "strategy_signal": close_reason
                        }
                    }
                )
                
                closed_count += 1
                logger.info(f"✅ Position geschlossen: {commodity} {trade_type} - {close_reason} (P/L: {profit_loss:.2f})")
        
        if closed_count > 0:
            logger.info(f"AI Position Manager: {closed_count} Positionen geschlossen")
    
    except Exception as e:
        logger.error(f"Error in AI Position Manager: {e}")
