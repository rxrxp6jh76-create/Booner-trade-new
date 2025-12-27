#!/usr/bin/env python3
"""
Fix Database: Füge fehlende api_keys Tabelle hinzu
"""

import sqlite3
import os
from pathlib import Path

# Datenbank-Pfad auf macOS
db_path = os.path.expanduser("~/Library/Application Support/booner-trade/database/trading.db")

print(f"🔧 Repariere Datenbank: {db_path}")

if not os.path.exists(db_path):
    print(f"❌ Datenbank nicht gefunden: {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prüfe ob api_keys Tabelle existiert
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_keys'")
    if cursor.fetchone():
        print("✅ api_keys Tabelle existiert bereits")
    else:
        print("➕ Erstelle api_keys Tabelle...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                metaapi_token TEXT,
                metaapi_account_id TEXT,
                metaapi_icmarkets_account_id TEXT,
                bitpanda_api_key TEXT,
                bitpanda_email TEXT,
                finnhub_api_key TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        print("✅ api_keys Tabelle erstellt")
    
    # Zeige alle Tabellen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\n📋 Vorhandene Tabellen:")
    for table in tables:
        print(f"   - {table[0]}")
    
    conn.close()
    print("\n✅ Datenbank erfolgreich repariert!")
    print("\n🔄 Bitte starten Sie die App neu.")
    
except Exception as e:
    print(f"❌ Fehler: {e}")
    exit(1)
