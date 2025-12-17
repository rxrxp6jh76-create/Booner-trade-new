#!/bin/bash
#
# TEST-SETTINGS-UPDATE.sh
# Testet ob SL/TP Updates für bestehende Trades funktionieren
#
# Verwendung: ./TEST-SETTINGS-UPDATE.sh
#

echo "=========================================="
echo "  Booner Trade - Settings Update Test"
echo "=========================================="
echo ""

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_PATH="/Applications/Booner Trade.app"
BACKEND_PATH="$APP_PATH/Contents/Resources/app/backend/server.py"
LOG_PATH="$HOME/Library/Application Support/booner-trade/logs/backend-error.log"
DB_PATH="$HOME/Library/Application Support/booner-trade/database/trades.db"

# 1. Prüfe ob der neue Code installiert ist
echo "1. Prüfe Code-Installation..."
if grep -q "Trading Settings geändert - aktualisiere offene Trades" "$BACKEND_PATH" 2>/dev/null; then
    echo -e "   ${GREEN}✓ Neuer Code ist installiert${NC}"
else
    echo -e "   ${RED}✗ Neuer Code ist NICHT installiert!${NC}"
    echo "   Bitte laden Sie den neuesten Code von GitHub herunter."
    exit 1
fi

if grep -q "force_update=True" "$BACKEND_PATH" 2>/dev/null; then
    echo -e "   ${GREEN}✓ force_update=True gefunden${NC}"
else
    echo -e "   ${RED}✗ force_update=True FEHLT!${NC}"
    exit 1
fi

# 2. Beende alle Prozesse
echo ""
echo "2. Beende alle Booner Trade Prozesse..."
pkill -9 -f "Booner" 2>/dev/null
pkill -9 -f "Python.app" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
sleep 2

# Prüfe ob alle beendet
REMAINING=$(ps aux | grep -i "booner\|python" | grep -v grep | grep -v Dropbox | grep -v "TEST-SETTINGS" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠ Einige Prozesse laufen noch, versuche erneut...${NC}"
    pkill -9 -f "Booner" 2>/dev/null
    pkill -9 -f "Python" 2>/dev/null
    sleep 2
fi
echo -e "   ${GREEN}✓ Alle Prozesse beendet${NC}"

# 3. Starte die App
echo ""
echo "3. Starte Booner Trade..."
open "$APP_PATH"

# 4. Warte auf Backend
echo ""
echo "4. Warte auf Backend (max 30 Sekunden)..."
for i in {1..30}; do
    if curl -s "http://localhost:8000/api/settings" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Backend läuft nach ${i} Sekunden${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Prüfe nochmal
if ! curl -s "http://localhost:8000/api/settings" > /dev/null 2>&1; then
    echo -e "   ${RED}✗ Backend startet nicht!${NC}"
    exit 1
fi

# 5. Hole aktuelle Mean Reversion TP Werte aus DB
echo ""
echo "5. Aktuelle Mean Reversion Trades in DB:"
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "SELECT trade_id, strategy, take_profit, entry_price FROM trade_settings WHERE strategy='mean_reversion' LIMIT 3;" 2>/dev/null
else
    echo -e "   ${YELLOW}⚠ Datenbank nicht gefunden${NC}"
fi

# 6. Ändere Settings auf 0.5% TP
echo ""
echo "6. Ändere mean_reversion_take_profit_percent auf 0.5%..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/settings" \
  -H "Content-Type: application/json" \
  -d '{"id": "trading_settings", "mean_reversion_take_profit_percent": 0.5}')

if echo "$RESPONSE" | grep -q "mean_reversion_take_profit_percent.*0.5"; then
    echo -e "   ${GREEN}✓ Settings wurden gespeichert${NC}"
else
    echo -e "   ${RED}✗ Settings konnten nicht gespeichert werden${NC}"
fi

# 7. Warte kurz und prüfe Logs
sleep 3
echo ""
echo "7. Backend Logs nach Settings-Update:"
echo "----------------------------------------"
tail -20 "$LOG_PATH" 2>/dev/null | grep -i "trading\|trade\|aktualisiere\|update\|position" | tail -10
echo "----------------------------------------"

# 8. Prüfe ob Trades aktualisiert wurden
echo ""
echo "8. Mean Reversion Trades NACH Update:"
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "SELECT trade_id, strategy, take_profit, entry_price FROM trade_settings WHERE strategy='mean_reversion' LIMIT 3;" 2>/dev/null
    
    # Berechne erwarteten Wert
    echo ""
    echo "   Bei 0.5% TP sollte take_profit ca. 0.5% unter entry_price sein"
    echo "   Beispiel: Entry 65.80 -> TP sollte ca. 65.47 sein"
fi

echo ""
echo "=========================================="
echo "  Test abgeschlossen"
echo "=========================================="
echo ""
echo "Falls die Logs KEINE Meldung zeigen wie:"
echo "  '🔄 Trading Settings geändert - aktualisiere offene Trades...'"
echo "  '📊 MT5_LIBERTEX_DEMO: X offene Positionen'"
echo "  '✅ X Trade Settings aktualisiert!'"
echo ""
echo "Dann liegt ein Problem vor. Bitte melden Sie sich."
