#!/bin/bash
#
# Zeigt Backend-Logs an
#

echo "========================================"
echo "  Backend Logs"
echo "========================================"
echo ""

LOG_FILE="$HOME/Library/Application Support/booner-trade/backend.log"

if [ -f "$LOG_FILE" ]; then
    echo "✅ Log gefunden: $LOG_FILE"
    echo ""
    echo "Letzte 100 Zeilen:"
    echo "----------------------------------------"
    tail -100 "$LOG_FILE"
else
    echo "❌ Keine Logs gefunden!"
    echo ""
    echo "Suche nach Backend-Prozess:"
    ps aux | grep -i "python.*server\|uvicorn" | grep -v grep
fi

echo ""
echo "========================================"
