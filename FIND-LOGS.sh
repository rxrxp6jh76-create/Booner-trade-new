#!/bin/bash
#
# Findet Backend-Logs und zeigt sie an
#

echo "========================================"
echo "  BOONER Trade - Log Finder"
echo "========================================"
echo ""

echo "🔍 Suche nach Backend-Logs..."
echo ""

# Prüfe verschiedene mögliche Orte
POSSIBLE_LOCATIONS=(
  "$HOME/Booner-App/backend/logs/backend.log"
  "$HOME/Library/Application Support/booner-trade/logs/backend.log"
  "$HOME/Library/Logs/booner-trade/backend.log"
  "/tmp/booner-backend.log"
)

FOUND=0

for location in "${POSSIBLE_LOCATIONS[@]}"; do
  if [ -f "$location" ]; then
    echo "✅ Log gefunden: $location"
    echo ""
    echo "Letzte 50 Zeilen:"
    echo "----------------------------------------"
    tail -50 "$location"
    echo "----------------------------------------"
    FOUND=1
    break
  fi
done

if [ $FOUND -eq 0 ]; then
  echo "❌ Keine Log-Dateien gefunden!"
  echo ""
  echo "Mögliche Ursachen:"
  echo "1. Backend läuft nicht"
  echo "2. App wurde noch nicht gestartet"
  echo ""
  echo "Suche nach allen .log Dateien in relevanten Ordnern:"
  find ~/Library -name "*.log" -path "*booner*" 2>/dev/null | head -10
  find ~/Booner-App -name "*.log" 2>/dev/null | head -10
  
  echo ""
  echo "Prüfe ob Backend-Prozess läuft:"
  ps aux | grep -i "python.*server\|uvicorn" | grep -v grep
fi

echo ""
echo "========================================"
