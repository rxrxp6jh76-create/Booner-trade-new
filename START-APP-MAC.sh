#!/bin/bash

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "  🚀 BOONER TRADE v2.3.27 - Development Start"
echo "=================================================="
echo ""

# Check if dependencies are installed
if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
    echo "❌ Backend venv nicht gefunden!"
    echo "   Bitte erst COMPLETE-MACOS-SETUP.sh ausführen"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "❌ Frontend node_modules nicht gefunden!"
    echo "   Bitte erst COMPLETE-MACOS-SETUP.sh ausführen"
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/frontend/build" ]; then
    echo "⚠️  Frontend build nicht gefunden!"
    echo "   Führe Quick Build durch..."
    cd "$SCRIPT_DIR/frontend"
    GENERATE_SOURCEMAP=false yarn build
    cd "$SCRIPT_DIR"
fi

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

echo "🔧 Starte Backend Server..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python server.py > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ Backend läuft (PID: $BACKEND_PID)"
echo "   📄 Logs: $SCRIPT_DIR/logs/backend.log"

sleep 3

echo ""
echo "⚛️  Starte Electron App..."
cd "$SCRIPT_DIR/electron-app"

# Check if electron-app has dependencies
if [ ! -d "node_modules" ]; then
    echo "   📦 Installiere Electron Dependencies..."
    yarn install > /dev/null 2>&1
fi

yarn start > "$SCRIPT_DIR/logs/electron.log" 2>&1 &
ELECTRON_PID=$!
echo "   ✅ Electron läuft (PID: $ELECTRON_PID)"
echo "   📄 Logs: $SCRIPT_DIR/logs/electron.log"

echo ""
echo "═══════════════════════════════════════"
echo "✅ APP LÄUFT!"
echo "═══════════════════════════════════════"
echo ""
echo "🔍 Prozesse:"
echo "   Backend:  PID $BACKEND_PID"
echo "   Electron: PID $ELECTRON_PID"
echo ""
echo "📊 Logs anzeigen:"
echo "   Backend:  tail -f $SCRIPT_DIR/logs/backend.log"
echo "   Electron: tail -f $SCRIPT_DIR/logs/electron.log"
echo ""
echo "🛑 Zum Beenden:"
echo "   kill $BACKEND_PID $ELECTRON_PID"
echo ""
echo "💡 TIPP: App sollte automatisch öffnen!"
echo ""

# Save PIDs to file for easy cleanup
echo "$BACKEND_PID" > "$SCRIPT_DIR/logs/backend.pid"
echo "$ELECTRON_PID" > "$SCRIPT_DIR/logs/electron.pid"

# Wait for user interrupt
echo "Drücke Ctrl+C zum Beenden..."
trap "echo ''; echo '🛑 Stoppe Services...'; kill $BACKEND_PID $ELECTRON_PID 2>/dev/null; echo '✅ Services gestoppt'; exit 0" INT

# Keep script running
wait
