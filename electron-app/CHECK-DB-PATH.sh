#!/bin/bash
#
# Prüft wo die SQLite Datenbank gespeichert wird
#

echo "========================================"
echo "  SQLite Datenbank Pfad Prüfung"
echo "========================================"
echo ""

DB_LOCATION="$HOME/Library/Application Support/booner-trade/database/trading.db"

echo "Erwarteter DB-Pfad:"
echo "$DB_LOCATION"
echo ""

if [ -f "$DB_LOCATION" ]; then
    echo "✅ Datenbank gefunden!"
    echo ""
    echo "Größe: $(du -h "$DB_LOCATION" | cut -f1)"
    echo "Letzte Änderung: $(stat -f "%Sm" "$DB_LOCATION")"
    echo ""
    echo "Tabellen in der Datenbank:"
    sqlite3 "$DB_LOCATION" "SELECT name FROM sqlite_master WHERE type='table';"
    echo ""
    echo "Trading Settings vorhanden?"
    sqlite3 "$DB_LOCATION" "SELECT COUNT(*) FROM trading_settings;" 2>/dev/null && echo "✅ Ja" || echo "❌ Nein"
else
    echo "❌ Datenbank nicht gefunden!"
    echo ""
    echo "Mögliche andere Orte:"
    find ~/Library -name "trading.db" 2>/dev/null || echo "Keine gefunden"
    find ~/Booner-App -name "trading.db" 2>/dev/null || echo "Keine in ~/Booner-App"
fi

echo ""
echo "========================================"
