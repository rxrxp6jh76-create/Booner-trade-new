"""
🔧 FIX: Aktualisiere alle bestehenden Trade Settings mit korrekten SL/TP Werten
Dieses Script korrigiert die SL/TP für ALLE offenen Trades basierend auf ihren Entry Prices
"""

import asyncio
import logging
import database as db_module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_trade_sltp():
    """Korrigiere SL/TP für alle Trades"""
    try:
        db = await db_module.get_db()
        if not db:
            logger.error("Could not connect to database")
            return
        
        # Hole alle trade_settings
        cursor = await db.trade_settings.find({})
        all_settings = await cursor.to_list(10000)
        
        logger.info(f"📊 Gefunden: {len(all_settings)} trade_settings")
        
        updated_count = 0
        
        for setting in all_settings:
            trade_id = setting.get('trade_id')
            strategy = setting.get('strategy', 'day')
            entry_price = setting.get('entry_price', 0)
            trade_type = setting.get('trade_type', 'BUY')
            
            if not entry_price or entry_price == 0:
                logger.warning(f"⚠️ {trade_id}: Kein entry_price, überspringe")
                continue
            
            # Bestimme SL/TP % basierend auf Strategie
            if strategy == 'scalping':
                sl_percent = 0.08  # 0.08%
                tp_percent = 0.15  # 0.15%
            elif strategy == 'day':
                sl_percent = 2.0   # 2%
                tp_percent = 2.5   # 2.5%
            elif strategy == 'swing':
                sl_percent = 2.0   # 2%
                tp_percent = 4.0   # 4%
            elif strategy == 'mean_reversion':
                sl_percent = 1.5   # 1.5%
                tp_percent = 2.0   # 2.0%
            elif strategy == 'momentum':
                sl_percent = 2.5   # 2.5%
                tp_percent = 5.0   # 5.0%
            elif strategy == 'breakout':
                sl_percent = 2.0   # 2.0%
                tp_percent = 4.0   # 4.0%
            elif strategy == 'grid':
                sl_percent = 3.0   # 3.0%
                tp_percent = 1.0   # 1.0% per level
            else:
                sl_percent = 2.0   # Default
                tp_percent = 2.5   # Default
            
            # Berechne neue SL/TP
            if trade_type == 'BUY':
                new_sl = entry_price * (1 - sl_percent / 100)
                new_tp = entry_price * (1 + tp_percent / 100)
            else:  # SELL
                new_sl = entry_price * (1 + sl_percent / 100)
                new_tp = entry_price * (1 - tp_percent / 100)
            
            # Alte Werte
            old_sl = setting.get('stop_loss')
            old_tp = setting.get('take_profit')
            
            # Prüfe ob Update nötig (wenn Werte sich ändern)
            if old_sl != new_sl or old_tp != new_tp:
                # Update in DB
                await db.trade_settings.update_one(
                    {"trade_id": trade_id},
                    {"$set": {
                        "stop_loss": new_sl,
                        "take_profit": new_tp,
                        "stop_loss_percent": sl_percent,
                        "take_profit_percent": tp_percent
                    }}
                )
                
                logger.info(f"✅ {trade_id} ({strategy}): SL {old_sl:.2f} → {new_sl:.2f}, TP {old_tp:.2f} → {new_tp:.2f}")
                updated_count += 1
            else:
                logger.debug(f"✔️  {trade_id}: SL/TP bereits korrekt")
        
        logger.info(f"🎉 {updated_count} trade_settings aktualisiert!")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(fix_trade_sltp())
