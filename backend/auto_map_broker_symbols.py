"""
Automatisches Symbol-Mapping für neuen MT5-Broker
Dieses Script hilft beim Wechsel zu einem neuen Broker
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

load_dotenv()

BACKEND_URL = "https://market-trader-116.preview.emergentagent.com"

# Rohstoffe und ihre möglichen Symbol-Varianten bei verschiedenen Brokern
COMMODITY_PATTERNS = {
    "GOLD": {
        "keywords": ["GOLD", "XAU", "GC"],
        "current": "XAUUSD"
    },
    "SILVER": {
        "keywords": ["SILVER", "XAG", "SI"],
        "current": "XAGUSD"
    },
    "PLATINUM": {
        "keywords": ["PLAT", "XPT", "PL"],
        "current": "XPTUSD"
    },
    "PALLADIUM": {
        "keywords": ["PALL", "XPD", "PA"],
        "current": "XPDUSD"
    },
    "WTI_CRUDE": {
        "keywords": ["WTI", "USOIL", "CL", "CRUDE"],
        "current": "WTI_F6"
    },
    "BRENT_CRUDE": {
        "keywords": ["BRENT", "UKOIL", "BZ"],
        "current": "BRENT_F6"
    },
    "WHEAT": {
        "keywords": ["WHEAT", "ZW"],
        "current": "Wheat_H6"
    },
    "CORN": {
        "keywords": ["CORN", "ZC", "MAIZ"],
        "current": "Corn_H6"
    },
    "SOYBEANS": {
        "keywords": ["SOY", "SBEAN", "ZS"],
        "current": "Sbean_F6"
    },
    "COFFEE": {
        "keywords": ["COFFEE", "KC"],
        "current": "Coffee_H6"
    },
    "SUGAR": {
        "keywords": ["SUGAR", "SB"],
        "current": "Sugar_H6"
    },
    "COTTON": {
        "keywords": ["COTTON", "CT"],
        "current": "Cotton_H6"
    },
    "COCOA": {
        "keywords": ["COCOA", "CC"],
        "current": "Cocoa_H6"
    }
}

async def fetch_broker_symbols():
    """Hole alle verfügbaren Symbole vom aktuellen Broker"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/mt5/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('all_symbols', [])
                else:
                    print(f"❌ Fehler beim Abrufen der Symbole: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return []

def find_matching_symbol(commodity_id, patterns, broker_symbols):
    """Finde das passende Symbol beim Broker"""
    keywords = patterns['keywords']
    current = patterns['current']
    
    # Prüfe zuerst, ob das aktuelle Symbol verfügbar ist
    if current in broker_symbols:
        return current
    
    # Suche nach exakten Matches oder Teilübereinstimmungen
    matches = []
    for symbol in broker_symbols:
        symbol_upper = symbol.upper()
        
        # Ignoriere Aktien-Symbole (.NYSE, .NAS, .ETR, .PAR, etc.)
        if '.' in symbol:
            continue
        
        # Ignoriere Forex-Paare (außer für Metalle)
        if 'USD' in symbol_upper or 'EUR' in symbol_upper or 'GBP' in symbol_upper:
            # Nur erlauben für Metalle (XAU, XAG, XPT, XPD)
            if not any(metal in symbol_upper for metal in ['XAU', 'XAG', 'XPT', 'XPD']):
                continue
        
        # Scoring-System für bessere Matches
        score = 0
        for keyword in keywords:
            if keyword == symbol_upper:
                score += 100  # Exakter Match
            elif symbol_upper.startswith(keyword):
                score += 50  # Beginnt mit Keyword
            elif keyword in symbol_upper:
                score += 10  # Enthält Keyword
        
        if score > 0:
            # Bevorzuge kürzere Symbole
            length_penalty = len(symbol) / 10
            final_score = score - length_penalty
            matches.append((symbol, final_score))
    
    # Sortiere nach Score (höchster zuerst)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    if matches:
        return matches[0][0]  # Bestes Match
    return None

async def auto_map_symbols():
    """Automatisches Mapping der Rohstoff-Symbole"""
    print("="*80)
    print("AUTOMATISCHES SYMBOL-MAPPING FÜR NEUEN BROKER")
    print("="*80)
    
    # Hole alle verfügbaren Symbole vom Broker
    print("\n📡 Rufe verfügbare Symbole vom MT5-Broker ab...")
    broker_symbols = await fetch_broker_symbols()
    
    if not broker_symbols:
        print("❌ Keine Symbole gefunden! Bitte überprüfen Sie:")
        print("   1. MT5-Verbindung ist aktiv")
        print("   2. Neue Broker-Zugangsdaten sind in .env eingetragen")
        print("   3. Backend ist neu gestartet")
        return
    
    print(f"✅ {len(broker_symbols)} Symbole vom Broker gefunden\n")
    
    # Mapping für jedes Rohstoff
    mappings = {}
    tradeable = []
    
    print("="*80)
    print("GEFUNDENE SYMBOL-ZUORDNUNGEN")
    print("="*80)
    
    for commodity_id, patterns in COMMODITY_PATTERNS.items():
        matched_symbol = find_matching_symbol(commodity_id, patterns, broker_symbols)
        
        if matched_symbol:
            mappings[commodity_id] = matched_symbol
            tradeable.append(commodity_id)
            print(f"✅ {commodity_id:15} -> {matched_symbol}")
        else:
            mappings[commodity_id] = patterns['current']  # Behalte altes Symbol
            print(f"⚠️  {commodity_id:15} -> NICHT GEFUNDEN (behalte: {patterns['current']})")
    
    # Generiere Code für commodity_processor.py
    print("\n" + "="*80)
    print("CODE FÜR commodity_processor.py")
    print("="*80)
    print("\nCOMMODITIES = {")
    
    for commodity_id, symbol in mappings.items():
        patterns = COMMODITY_PATTERNS[commodity_id]
        # Finde das richtige Commodity aus der Original-Definition
        if commodity_id in ["GOLD", "SILVER", "PLATINUM", "PALLADIUM"]:
            category = "Edelmetalle"
            unit = "USD/oz"
        elif commodity_id in ["WTI_CRUDE", "BRENT_CRUDE"]:
            category = "Energie"
            unit = "USD/Barrel"
        else:
            category = "Agrar"
            unit = "USD/Bushel" if commodity_id not in ["COFFEE", "SUGAR", "COTTON"] else "USD/lb"
        
        # Ermittle Namen
        names = {
            "GOLD": "Gold", "SILVER": "Silber", "PLATINUM": "Platin", "PALLADIUM": "Palladium",
            "WTI_CRUDE": "WTI Crude Oil", "BRENT_CRUDE": "Brent Crude Oil",
            "WHEAT": "Weizen", "CORN": "Mais", "SOYBEANS": "Sojabohnen",
            "COFFEE": "Kaffee", "SUGAR": "Zucker", "COTTON": "Baumwolle", "COCOA": "Kakao"
        }
        
        print(f'    "{commodity_id}": {{"name": "{names[commodity_id]}", "symbol": "...", "mt5_symbol": "{symbol}", "category": "{category}", "unit": "{unit}", "platform": "MT5"}},')
    
    print("}")
    
    # Liste der handelbaren Rohstoffe
    print("\n" + "="*80)
    print("HANDELBARE ROHSTOFFE (für server.py)")
    print("="*80)
    print("\nMT5_TRADEABLE = [")
    for commodity in tradeable:
        print(f'    "{commodity}",')
    print("]")
    
    print("\n" + "="*80)
    print("NÄCHSTE SCHRITTE")
    print("="*80)
    print("1. Kopieren Sie den COMMODITIES-Code oben")
    print("2. Ersetzen Sie in /app/backend/commodity_processor.py")
    print("3. Kopieren Sie MT5_TRADEABLE Liste")
    print("4. Ersetzen Sie in /app/backend/server.py (bei MT5 Order-Validierung)")
    print("5. Backend neu starten: sudo supervisorctl restart backend")

if __name__ == "__main__":
    asyncio.run(auto_map_symbols())
