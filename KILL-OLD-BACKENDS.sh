#!/bin/bash
#
# Killt alle alten Backend-Prozesse
#

echo "========================================"
echo "  Kill Old Backend Processes"
echo "========================================"
echo ""

echo "🔍 Suche nach laufenden Backend-Prozessen..."
ps aux | grep -i "uvicorn server:app" | grep -v grep

echo ""
echo "🛑 Stoppe alle Backend-Prozesse..."
pkill -f "uvicorn server:app"

sleep 2

echo ""
echo "✅ Überprüfe ob Prozesse gestoppt wurden..."
REMAINING=$(ps aux | grep -i "uvicorn server:app" | grep -v grep | wc -l)

if [ $REMAINING -eq 0 ]; then
    echo "✅ Alle Backend-Prozesse erfolgreich gestoppt!"
else
    echo "⚠️ Noch $REMAINING Prozesse laufen. Force kill..."
    pkill -9 -f "uvicorn server:app"
fi

echo ""
echo "========================================"
