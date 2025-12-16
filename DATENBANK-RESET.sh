#!/bin/bash

# 🗑️ Datenbank Reset Script für Booner Trade
# Löscht alle lokalen Daten für einen sauberen Neustart

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗑️  Booner Trade - Datenbank Reset"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  WARNUNG: Dies löscht ALLE lokalen Daten!"
echo "   - Alle Trade Settings"
echo "   - Alle Trade History"
echo "   - Alle gespeicherten Einstellungen"
echo ""
read -p "Fortfahren? (j/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
    echo "❌ Abgebrochen"
    exit 0
fi

echo ""
echo "🔍 Suche Datenbank-Ordner..."

# Mögliche Speicherorte
DB_LOCATIONS=(
    "$HOME/Library/Application Support/booner-trade/database"
    "$HOME/Library/Application Support/booner-trade/logs"
    "$(pwd)/backend/trading.db"
)

DELETED=0

for location in "${DB_LOCATIONS[@]}"; do
    if [ -e "$location" ]; then
        echo "📁 Gefunden: $location"
        
        # Backup erstellen
        BACKUP_NAME="${location}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "💾 Erstelle Backup: $(basename "$BACKUP_NAME")"
        cp -r "$location" "$BACKUP_NAME" 2>/dev/null || true
        
        # Löschen
        rm -rf "$location"
        echo "✅ Gelöscht: $location"
        DELETED=$((DELETED + 1))
        echo ""
    fi
done

if [ $DELETED -eq 0 ]; then
    echo "ℹ️  Keine Datenbank-Dateien gefunden"
    echo "   Die App wird beim nächsten Start eine neue Datenbank erstellen"
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Reset abgeschlossen!"
    echo "   $DELETED Speicherorte gelöscht/zurückgesetzt"
    echo ""
    echo "🚀 Nächste Schritte:"
    echo "   1. App öffnen"
    echo "   2. Settings werden mit Defaults neu erstellt"
    echo "   3. MetaAPI-Verbindung wird neu aufgebaut"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
