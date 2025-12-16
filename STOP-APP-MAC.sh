#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🛑 Stoppe BOONER TRADE App..."
echo ""

# Read PIDs from file
if [ -f "$SCRIPT_DIR/logs/backend.pid" ]; then
    BACKEND_PID=$(cat "$SCRIPT_DIR/logs/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo "✅ Backend gestoppt (PID: $BACKEND_PID)"
    else
        echo "ℹ️  Backend läuft nicht"
    fi
    rm "$SCRIPT_DIR/logs/backend.pid"
fi

if [ -f "$SCRIPT_DIR/logs/electron.pid" ]; then
    ELECTRON_PID=$(cat "$SCRIPT_DIR/logs/electron.pid")
    if ps -p $ELECTRON_PID > /dev/null 2>&1; then
        kill $ELECTRON_PID
        echo "✅ Electron gestoppt (PID: $ELECTRON_PID)"
    else
        echo "ℹ️  Electron läuft nicht"
    fi
    rm "$SCRIPT_DIR/logs/electron.pid"
fi

# Fallback: Kill all related processes
pkill -f "python.*server.py" 2>/dev/null && echo "✅ Python Prozesse gestoppt"
pkill -f "electron.*booner" 2>/dev/null && echo "✅ Electron Prozesse gestoppt"

echo ""
echo "✅ Alle Services gestoppt!"
