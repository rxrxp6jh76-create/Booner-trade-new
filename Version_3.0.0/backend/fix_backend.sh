#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 BACKEND HARD RESET für macOS
# ═══════════════════════════════════════════════════════════════════════════════
# Dieses Script behebt das Problem wenn das Backend nicht mehr startet.
# 
# Verwendung:
#   chmod +x fix_backend.sh
#   ./fix_backend.sh
# ═══════════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════"
echo "🔄 BACKEND HARD RESET"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1. Alle Python/Backend Prozesse beenden
echo "🛑 Beende alle Backend-Prozesse..."
pkill -f "server.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
pkill -f "python.*8000" 2>/dev/null

# 2. Port 8000 freigeben
echo "🔓 Gebe Port 8000 frei..."
lsof -ti:8000 | xargs kill -9 2>/dev/null

# 3. Warten
sleep 2

# 4. Datenbank-Locks entfernen
echo "🗑️  Entferne Datenbank-Locks..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
rm -f "$SCRIPT_DIR/trading.db-journal" 2>/dev/null
rm -f "$SCRIPT_DIR/trading.db-wal" 2>/dev/null
rm -f "$SCRIPT_DIR/trading.db-shm" 2>/dev/null

# 5. Cache leeren
echo "🧹 Leere Python Cache..."
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null

# 6. Prüfen ob Port frei ist
if lsof -i:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 noch belegt - Force Kill..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ CLEANUP ABGESCHLOSSEN"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Du kannst die App jetzt neu starten."
echo ""
