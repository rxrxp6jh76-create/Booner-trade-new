#!/bin/bash
#
# Debug Script für Settings-Problem
#

echo "========================================"
echo "  Settings Debug Info"
echo "========================================"
echo ""

DB_PATH="$HOME/Library/Application Support/booner-trade/database/trading.db"

if [ -f "$DB_PATH" ]; then
    echo "✅ DB gefunden: $DB_PATH"
    echo "Größe: $(du -h "$DB_PATH" | cut -f1)"
    echo "Letzte Änderung: $(stat -f "%Sm" "$DB_PATH")"
    echo ""
    
    echo "Tabellen:"
    sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table';"
    echo ""
    
    echo "Trading Settings (id):"
    sqlite3 "$DB_PATH" "SELECT id FROM trading_settings LIMIT 5;" 2>/dev/null || echo "Keine trading_settings Tabelle"
    echo ""
    
    echo "Trading Settings (data length):"
    sqlite3 "$DB_PATH" "SELECT id, length(data) as data_length FROM trading_settings LIMIT 5;" 2>/dev/null || echo "Fehler"
    echo ""
    
    echo "Erste 500 Zeichen von Settings:"
    sqlite3 "$DB_PATH" "SELECT substr(data, 1, 500) FROM trading_settings WHERE id='trading_settings' LIMIT 1;" 2>/dev/null || echo "Keine Settings gefunden"
else
    echo "❌ DB nicht gefunden: $DB_PATH"
fi

echo ""
echo "========================================"
