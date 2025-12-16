#!/bin/bash

##############################################################
# Kill Process auf Port 8000
# Verwendung: Vor dem App-Start ausführen
##############################################################

echo "🔍 Suche Prozess auf Port 8000..."

# Finde Prozess auf Port 8000
PID=$(lsof -ti:8000)

if [ -z "$PID" ]; then
    echo "✅ Port 8000 ist frei"
    exit 0
fi

echo "🔴 Gefunden: Prozess $PID läuft auf Port 8000"
echo "   Töte Prozess..."

kill -9 $PID

sleep 1

# Prüfe ob erfolgreich
PID=$(lsof -ti:8000)
if [ -z "$PID" ]; then
    echo "✅ Port 8000 ist jetzt frei"
else
    echo "❌ Prozess konnte nicht getötet werden"
    echo "   Versuche mit sudo:"
    sudo kill -9 $PID
fi
