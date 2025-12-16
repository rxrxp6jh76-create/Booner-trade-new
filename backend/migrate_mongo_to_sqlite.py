#!/usr/bin/env python3
"""
Migration Script: MongoDB → SQLite
Migriert alle Daten von MongoDB zu SQLite
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from database import init_database, _db, trading_settings, trades, trade_settings, market_data, market_data_history
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Hauptmigration"""
    logger.info("="*60)
    logger.info("🚀 MongoDB → SQLite Migration gestartet")
    logger.info("="*60)
    
    # MongoDB Connection
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    mongo_client = AsyncIOMotorClient(mongo_url)
    mongo_db = mongo_client.trading_db
    
    # SQLite Connection
    await init_database()
    
    try:
        # 1. Migrate Trading Settings
        logger.info("\n📊 Migriere Trading Settings...")
        settings_doc = await mongo_db.trading_settings.find_one({"id": "trading_settings"})
        if settings_doc:
            # Remove MongoDB _id
            settings_doc.pop('_id', None)
            await trading_settings.insert_one(settings_doc)
            logger.info(f"✅ Trading Settings migriert")
        else:
            logger.warning("⚠️ Keine Trading Settings gefunden")
        
        # 2. Migrate Trades
        logger.info("\n📊 Migriere Trades...")
        mongo_trades = await mongo_db.trades.find({}).to_list(None)
        migrated_trades = 0
        for trade in mongo_trades:
            try:
                trade.pop('_id', None)
                
                # Convert timestamp strings to datetime if needed
                for key in ['timestamp', 'closed_at', 'opened_at']:
                    if key in trade and isinstance(trade[key], str):
                        try:
                            trade[key] = datetime.fromisoformat(trade[key].replace('Z', '+00:00'))
                        except:
                            pass
                
                await trades.insert_one(trade)
                migrated_trades += 1
            except Exception as e:
                logger.error(f"❌ Fehler bei Trade {trade.get('id')}: {e}")
        
        logger.info(f"✅ {migrated_trades} Trades migriert")
        
        # 3. Migrate Trade Settings
        logger.info("\n📊 Migriere Trade Settings...")
        mongo_trade_settings = await mongo_db.trade_settings.find({}).to_list(None)
        migrated_settings = 0
        for setting in mongo_trade_settings:
            try:
                setting.pop('_id', None)
                await trade_settings.insert_one(setting)
                migrated_settings += 1
            except Exception as e:
                logger.error(f"❌ Fehler bei Trade Setting {setting.get('trade_id')}: {e}")
        
        logger.info(f"✅ {migrated_settings} Trade Settings migriert")
        
        # 4. Migrate Market Data
        logger.info("\n📊 Migriere Market Data...")
        mongo_market_data = await mongo_db.market_data.find({}).to_list(None)
        migrated_market = 0
        for md in mongo_market_data:
            try:
                md.pop('_id', None)
                commodity = md.get('commodity')
                if commodity:
                    await market_data.update_one(
                        {"commodity": commodity},
                        {"$set": md},
                        upsert=True
                    )
                    migrated_market += 1
            except Exception as e:
                logger.error(f"❌ Fehler bei Market Data {md.get('commodity')}: {e}")
        
        logger.info(f"✅ {migrated_market} Market Data Einträge migriert")
        
        # 5. Migrate Market Data History (last 7 days only to save space)
        logger.info("\n📊 Migriere Market Data History (letzte 7 Tage)...")
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=7)
        
        mongo_history = await mongo_db.market_data_history.find({
            "timestamp": {"$gte": cutoff}
        }).to_list(None)
        
        migrated_history = 0
        for hist in mongo_history:
            try:
                hist.pop('_id', None)
                await market_data_history.insert_one(hist)
                migrated_history += 1
            except Exception as e:
                logger.error(f"❌ Fehler bei History: {e}")
        
        logger.info(f"✅ {migrated_history} History Einträge migriert")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("✅ MIGRATION ABGESCHLOSSEN!")
        logger.info("="*60)
        logger.info(f"📊 Trading Settings: {'✅' if settings_doc else '⚠️'}")
        logger.info(f"📊 Trades: {migrated_trades}")
        logger.info(f"📊 Trade Settings: {migrated_settings}")
        logger.info(f"📊 Market Data: {migrated_market}")
        logger.info(f"📊 History: {migrated_history}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Migration fehlgeschlagen: {e}", exc_info=True)
    finally:
        # Cleanup
        await _db.close()
        mongo_client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
