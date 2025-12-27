#!/usr/bin/env python3
"""
Fix für bestehende Trades - Erstellt trade_settings Einträge für alle offenen MT5 Trades
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

async def fix_existing_trades():
    """Erstelle trade_settings für alle bestehenden offenen Trades"""
    
    mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client.trading_db
    
    # Hole Settings
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if not settings:
        print("❌ Keine Settings gefunden!")
        return
    
    # Hole alle offenen Trades von MT5 via API
    import requests
    try:
        response = requests.get('http://localhost:8001/api/trades/list', timeout=10)
        data = response.json()
        trades = data.get('trades', [])
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Trades: {e}")
        return
    
    print(f"📊 Gefundene offene Trades: {len(trades)}")
    
    created_count = 0
    skipped_count = 0
    
    for trade in trades:
        ticket = trade.get('mt5_ticket') or trade.get('ticket')
        if not ticket:
            continue
        
        # Prüfe ob trade_settings bereits existiert
        existing = await db.trade_settings.find_one({'trade_id': str(ticket)})
        if existing:
            skipped_count += 1
            continue
        
        # Erstelle trade_settings - NUR Strategie speichern!
        # SL/TP werden dynamisch aus Settings berechnet
        strategy = trade.get('strategy', 'day')  # Default zu day trading
        entry_price = trade.get('entry_price') or trade.get('price')
        commodity = trade.get('commodity')
        platform = trade.get('platform')
        
        trade_settings = {
            'trade_id': str(ticket),
            'strategy': strategy,  # NUR Strategie wird gespeichert!
            'entry_price': entry_price,
            'commodity': commodity,
            'platform': platform,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'created_by': 'FIX_SCRIPT',
            'note': 'Strategie-Info für dynamische SL/TP Berechnung'
        }
        
        await db.trade_settings.insert_one(trade_settings)
        created_count += 1
        
        if created_count % 10 == 0:
            print(f"⏳ {created_count} trade_settings erstellt...")
    
    print()
    print(f"✅ Fertig!")
    print(f"   Neu erstellt: {created_count}")
    print(f"   Übersprungen: {skipped_count}")
    print(f"   Gesamt: {len(trades)}")
    
    client.close()

if __name__ == "__main__":
    print("🔧 Erstelle trade_settings für bestehende Trades...\n")
    asyncio.run(fix_existing_trades())
