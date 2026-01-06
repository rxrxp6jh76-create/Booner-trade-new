#!/bin/bash
# Booner Trade Einmaliger Neustart
# Doppelklicken Sie diese Datei für einen sofortigen Neustart

echo "🔄 Starte Booner Trade Neustart..."
echo ""

# Schritt 1: Booner Trade beenden
echo "🛑 Beende Booner Trade..."
osascript -e 'tell application "Booner Trade" to quit' 2>/dev/null
sleep 2
pkill -f "Booner Trade" 2>/dev/null
echo "   ✅ Booner Trade beendet"

# Schritt 2: Kill Old Backend
echo ""
echo "🔪 Kill Old Backend..."
SCRIPT_DIR="$(dirname "$0")"
if [ -f "$SCRIPT_DIR/../Kill Old backend.command" ]; then
    bash "$SCRIPT_DIR/../Kill Old backend.command"
elif [ -f ~/Documents/BoonerTrade/"Kill Old backend.command" ]; then
    bash ~/Documents/BoonerTrade/"Kill Old backend.command"
else
    pkill -f "uvicorn.*server:app" 2>/dev/null
    pkill -f "python.*server.py" 2>/dev/null
    echo "   (Fallback-Methode verwendet)"
fi
echo "   ✅ Kill Old Backend ausgeführt"

# Warte 7 Sekunden
echo ""
echo "⏳ Warte 7 Sekunden..."
sleep 7

# Schritt 3: Kill All Backend
echo ""
echo "💀 Kill All Backend..."
if [ -f "$SCRIPT_DIR/../Kill all Backend.command" ]; then
    bash "$SCRIPT_DIR/../Kill all Backend.command"
elif [ -f ~/Documents/BoonerTrade/"Kill all Backend.command" ]; then
    bash ~/Documents/BoonerTrade/"Kill all Backend.command"
else
    pkill -9 -f "uvicorn" 2>/dev/null
    pkill -9 -f "python.*backend" 2>/dev/null
    echo "   (Fallback-Methode verwendet)"
fi
echo "   ✅ Kill All Backend ausgeführt"

# Warte 7 Sekunden
echo ""
echo "⏳ Warte 7 Sekunden..."
sleep 7

# Schritt 4: Booner Trade starten
echo ""
echo "🚀 Starte Booner Trade..."
if [ -d "/Applications/Booner Trade.app" ]; then
    open "/Applications/Booner Trade.app"
else
    osascript -e 'tell application "Booner Trade" to activate'
fi
echo "   ✅ Booner Trade gestartet"

echo ""
echo "="*50
echo "✅ NEUSTART ABGESCHLOSSEN"
echo "="*50
echo ""
echo "Drücken Sie eine Taste zum Schließen..."
read -n 1
