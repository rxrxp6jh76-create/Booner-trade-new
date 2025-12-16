#!/bin/bash

##############################################################
# Test Backend direkt ohne Electron
##############################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   TEST BACKEND DIREKT (ohne Electron)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

APP_PATH="/Applications/Booner Trade.app"
BACKEND_PATH="$APP_PATH/Contents/Resources/app/backend"
PYTHON_PATH="$APP_PATH/Contents/Resources/app/python/venv/bin/python3"
UVICORN_PATH="$APP_PATH/Contents/Resources/app/python/venv/bin/uvicorn"

echo -e "${CYAN}📁 Prüfe Pfade...${NC}"
echo "   Backend: $BACKEND_PATH"
echo "   Python: $PYTHON_PATH"
echo "   Uvicorn: $UVICORN_PATH"
echo ""

# Prüfe ob Dateien existieren
if [ ! -d "$BACKEND_PATH" ]; then
    echo -e "${RED}❌ Backend nicht gefunden!${NC}"
    exit 1
fi

if [ ! -f "$PYTHON_PATH" ]; then
    echo -e "${RED}❌ Python nicht gefunden!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Alle Pfade existieren${NC}"
echo ""

# Prüfe .env
echo -e "${CYAN}📄 Prüfe .env Datei...${NC}"
if [ -f "$BACKEND_PATH/.env" ]; then
    echo -e "${GREEN}✅ .env gefunden${NC}"
    echo "   Erste 10 Zeilen (ohne sensitive Daten):"
    head -10 "$BACKEND_PATH/.env" | grep -v "TOKEN\|PASSWORD\|KEY" || echo "   (keine nicht-sensitiven Zeilen)"
else
    echo -e "${RED}❌ .env NICHT gefunden!${NC}"
fi
echo ""

# Prüfe Python Version
echo -e "${CYAN}🐍 Python Version:${NC}"
"$PYTHON_PATH" --version
echo ""

# Prüfe ob server.py existiert
echo -e "${CYAN}📄 Prüfe server.py...${NC}"
if [ -f "$BACKEND_PATH/server.py" ]; then
    SIZE=$(wc -c < "$BACKEND_PATH/server.py")
    echo -e "${GREEN}✅ server.py gefunden ($SIZE bytes)${NC}"
else
    echo -e "${RED}❌ server.py nicht gefunden!${NC}"
    exit 1
fi
echo ""

# Teste Python Import
echo -e "${CYAN}🧪 Teste Python Imports...${NC}"
cd "$BACKEND_PATH"
"$PYTHON_PATH" -c "
import sys
print('Python Executable:', sys.executable)
print('Python Version:', sys.version)
print('')

# Test basic imports
try:
    import fastapi
    print('✅ fastapi importiert')
except Exception as e:
    print(f'❌ fastapi fehlt: {e}')

try:
    import uvicorn
    print('✅ uvicorn importiert')
except Exception as e:
    print(f'❌ uvicorn fehlt: {e}')

try:
    from metaapi_cloud_sdk import MetaApi
    print('✅ metaapi_cloud_sdk importiert')
except Exception as e:
    print(f'❌ metaapi_cloud_sdk fehlt: {e}')

try:
    import motor
    print('✅ motor (MongoDB) importiert')
except Exception as e:
    print(f'❌ motor fehlt: {e}')
" 2>&1
echo ""

# Versuche server.py zu importieren
echo -e "${CYAN}🧪 Teste server.py Import...${NC}"
"$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '$BACKEND_PATH')

try:
    import server
    print('✅ server.py erfolgreich importiert!')
except Exception as e:
    print(f'❌ server.py Import fehlgeschlagen:')
    print(f'   {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
" 2>&1
echo ""

# Starte Backend manuell im Vordergrund
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🚀 Starte Backend manuell (Vordergrund)...${NC}"
echo -e "${YELLOW}   Drücken Sie Ctrl+C zum Beenden${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd "$BACKEND_PATH"
export PORT=8000
export SQLITE_DB_PATH="$HOME/Library/Application Support/Booner Trade/database/trading.db"

# Load .env manually
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start uvicorn
"$UVICORN_PATH" server:app --host 0.0.0.0 --port 8000 --log-level debug
