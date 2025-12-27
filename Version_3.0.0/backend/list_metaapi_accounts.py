#!/usr/bin/env python3
"""
MetaAPI Account Lister - Zeigt alle verfügbaren MetaAPI Accounts
Hilft beim Finden der korrekten Account IDs für die .env Konfiguration
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')

async def list_metaapi_accounts():
    """Liste alle MetaAPI Accounts für diesen Token"""
    
    if not METAAPI_TOKEN:
        print("❌ METAAPI_TOKEN nicht gefunden in .env Datei!")
        return
    
    print("🔍 Suche nach MetaAPI Accounts...\n")
    
    url = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts"
    headers = {
        "auth-token": METAAPI_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    accounts = await response.json()
                    
                    if not accounts:
                        print("⚠️  Keine Accounts gefunden!")
                        return
                    
                    print(f"✅ Gefunden: {len(accounts)} Account(s)\n")
                    print("=" * 80)
                    
                    for i, account in enumerate(accounts, 1):
                        print(f"\n📊 ACCOUNT #{i}")
                        print("-" * 80)
                        print(f"Account ID:    {account.get('_id', 'N/A')}")
                        print(f"Name:          {account.get('name', 'N/A')}")
                        print(f"Login:         {account.get('login', 'N/A')}")
                        print(f"Server:        {account.get('server', 'N/A')}")
                        print(f"Broker:        {account.get('brokerName', 'N/A')}")
                        print(f"Plattform:     {account.get('platform', 'N/A')}")
                        print(f"Type:          {account.get('type', 'N/A')}")
                        print(f"Status:        {account.get('state', 'N/A')}")
                        print(f"Connection:    {account.get('connectionStatus', 'N/A')}")
                        
                        # Determine which account this is based on login or broker
                        broker = account.get('brokerName', '').lower()
                        login = str(account.get('login', ''))
                        
                        print(f"\n💡 Verwendung in .env:")
                        if 'libertex' in broker.lower() or 'libertex' in account.get('server', '').lower():
                            print(f"   METAAPI_ACCOUNT_ID={account.get('_id')}")
                        elif 'icmarkets' in broker.lower():
                            print(f"   METAAPI_ICMARKETS_ACCOUNT_ID={account.get('_id')}")
                        else:
                            print(f"   # Unbekannter Broker - manuell zuordnen")
                            print(f"   METAAPI_ACCOUNT_ID={account.get('_id')}")
                    
                    print("\n" + "=" * 80)
                    print("\n📝 NÄCHSTE SCHRITTE:")
                    print("1. Kopiere die passenden Account IDs (die UUIDs)")
                    print("2. Aktualisiere /app/backend/.env:")
                    print("   - METAAPI_ACCOUNT_ID=<Libertex Account ID>")
                    print("   - METAAPI_ICMARKETS_ACCOUNT_ID=<ICMarkets Account ID>")
                    print("3. Starte Backend neu: sudo supervisorctl restart backend")
                    
                elif response.status == 401:
                    print("❌ Authentifizierung fehlgeschlagen!")
                    print("   Der METAAPI_TOKEN ist ungültig oder abgelaufen.")
                    print("   Bitte generiere einen neuen Token auf: https://app.metaapi.cloud/")
                else:
                    text = await response.text()
                    print(f"❌ API Fehler: Status {response.status}")
                    print(f"   Response: {text}")
                    
    except asyncio.TimeoutError:
        print("❌ Timeout: MetaAPI Server antwortet nicht!")
    except Exception as e:
        print(f"❌ Fehler beim Abrufen der Accounts: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  MetaAPI Account Lister")
    print("=" * 80 + "\n")
    
    asyncio.run(list_metaapi_accounts())
