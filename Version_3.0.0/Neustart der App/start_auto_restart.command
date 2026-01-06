#!/bin/bash
# Booner Trade Auto-Restart Starter
# Doppelklicken Sie diese Datei um den Auto-Restart Service zu starten

cd "$(dirname "$0")"
echo "🔄 Starte Booner Trade Auto-Restart Service..."
echo "   Neustart erfolgt alle 1 Stunde"
echo "   Drücken Sie Ctrl+C zum Beenden"
echo ""

python3 auto_restart.py
