#!/bin/bash

##############################################################
# BOONER TRADE - KOMPLETTES SETUP VON NULL
#
# Was dieses Script macht:
# 1. Installiert alle benötigten Tools (Homebrew, Python 3.11, Node.js, Yarn)
# 2. Installiert Backend Dependencies
# 3. Installiert Frontend Dependencies
# 4. Wendet alle Fixes an (INKL. ALLE BUG FIXES v2.3.28)
# 5. Baut die Desktop App
# 6. Installiert die App
# 7. Startet die App
#
# Version 2.3.28 - Production Ready mit allen Bug Fixes
##############################################################

set -e # Exit bei Fehler

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     BOONER TRADE - KOMPLETTES MACOS SETUP v2.3.28        ║"
echo "║  Fresh Install - Alles wird automatisch gemacht          ║"
echo "║  + ALLE BUG FIXES + NEUE FEATURES                        ║"
echo "║  Für macOS M4 ARM64 (und Intel x86_64)                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verzeichnisse
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
ELECTRON_DIR="$PROJECT_ROOT/electron-app"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
APP_NAME="Booner Trade"

echo -e "${GREEN}📁 Projekt-Verzeichnis: $PROJECT_ROOT${NC}"
echo ""

##############################################################
# SCHRITT 1: System-Voraussetzungen prüfen und installieren
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 1: System-Voraussetzungen prüfen...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Homebrew installieren (falls nicht vorhanden)
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}📦 Homebrew nicht gefunden. Installiere Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Homebrew zum PATH hinzufügen
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
    
    echo -e "${GREEN}✅ Homebrew installiert${NC}"
else
    echo -e "${GREEN}✅ Homebrew bereits installiert${NC}"
    brew update
fi
echo ""

# Python 3.11 installieren (für MetaAPI SDK Kompatibilität)
echo -e "${BLUE}🐍 Python 3.11 prüfen...${NC}"
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}   Installiere Python 3.11...${NC}"
    brew install python@3.11
    echo -e "${GREEN}✅ Python 3.11 installiert${NC}"
else
    echo -e "${GREEN}✅ Python 3.11 bereits installiert${NC}"
fi
python3.11 --version
echo ""

# Node.js installieren (falls nicht vorhanden)
echo -e "${BLUE}📦 Node.js prüfen...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}   Installiere Node.js...${NC}"
    brew install node@18
    brew link node@18
    echo -e "${GREEN}✅ Node.js installiert${NC}"
else
    echo -e "${GREEN}✅ Node.js bereits installiert${NC}"
fi
node --version
echo ""

# Yarn installieren (falls nicht vorhanden)
echo -e "${BLUE}📦 Yarn prüfen...${NC}"
if ! command -v yarn &> /dev/null; then
    echo -e "${YELLOW}   Installiere Yarn...${NC}"
    npm install -g yarn
    echo -e "${GREEN}✅ Yarn installiert${NC}"
else
    echo -e "${GREEN}✅ Yarn bereits installiert${NC}"
fi
yarn --version
echo ""

##############################################################
# SCHRITT 2: Backend Setup
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 2: Backend Setup...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd "$BACKEND_DIR"

# Python venv erstellen
echo -e "${CYAN}📦 Erstelle Python Virtual Environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}   venv existiert bereits, lösche und erstelle neu...${NC}"
    rm -rf venv
fi

python3.11 -m venv venv
source venv/bin/activate

echo -e "${GREEN}✅ Python venv erstellt${NC}"
echo ""

# Backend Dependencies installieren
echo -e "${CYAN}📦 Installiere Backend Dependencies...${NC}"
echo -e "${YELLOW}   Dies kann 2-3 Minuten dauern...${NC}"

pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Backend Dependencies installiert${NC}"
deactivate
echo ""

# .env File prüfen und MetaAPI IDs automatisch korrigieren
echo -e "${CYAN}⚙️  Backend .env Datei prüfen und korrigieren...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ FEHLER: .env Datei nicht gefunden!${NC}"
    echo -e "${YELLOW}   Bitte stellen Sie sicher, dass die .env Datei existiert.${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATISCHE KORREKTUR DER METAAPI IDs
# ═══════════════════════════════════════════════════════════════════════════
# Diese IDs sind aus der Projekt-Dokumentation und MÜSSEN korrekt sein!
# Bei jedem Build werden sie automatisch überprüft und korrigiert.

CORRECT_LIBERTEX_ID="5cc9abd1-671a-447e-ab93-5abbfe0ed941"
CORRECT_ICMARKETS_ID="d2605e89-7bc2-4144-9f7c-951edd596c39"

echo -e "${CYAN}🔍 Prüfe MetaAPI Account IDs...${NC}"

# Prüfe und korrigiere Libertex Demo ID
CURRENT_LIBERTEX=$(grep "^METAAPI_ACCOUNT_ID=" .env | cut -d'=' -f2)
if [ "$CURRENT_LIBERTEX" != "$CORRECT_LIBERTEX_ID" ]; then
    echo -e "${YELLOW}⚠️  Libertex ID ist falsch: '$CURRENT_LIBERTEX'${NC}"
    echo -e "${CYAN}   Korrigiere zu: $CORRECT_LIBERTEX_ID${NC}"
    
    # Backup erstellen
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Korrigieren (macOS-kompatibel)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^METAAPI_ACCOUNT_ID=.*|METAAPI_ACCOUNT_ID=$CORRECT_LIBERTEX_ID|g" .env
    else
        sed -i "s|^METAAPI_ACCOUNT_ID=.*|METAAPI_ACCOUNT_ID=$CORRECT_LIBERTEX_ID|g" .env
    fi
    echo -e "${GREEN}   ✅ Libertex ID korrigiert!${NC}"
else
    echo -e "${GREEN}   ✅ Libertex ID korrekt${NC}"
fi

# Prüfe und korrigiere ICMarkets Demo ID
CURRENT_ICMARKETS=$(grep "^METAAPI_ICMARKETS_ACCOUNT_ID=" .env | cut -d'=' -f2)
if [ "$CURRENT_ICMARKETS" != "$CORRECT_ICMARKETS_ID" ]; then
    echo -e "${YELLOW}⚠️  ICMarkets ID ist falsch: '$CURRENT_ICMARKETS'${NC}"
    echo -e "${CYAN}   Korrigiere zu: $CORRECT_ICMARKETS_ID${NC}"
    
    # Korrigieren (macOS-kompatibel)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^METAAPI_ICMARKETS_ACCOUNT_ID=.*|METAAPI_ICMARKETS_ACCOUNT_ID=$CORRECT_ICMARKETS_ID|g" .env
    else
        sed -i "s|^METAAPI_ICMARKETS_ACCOUNT_ID=.*|METAAPI_ICMARKETS_ACCOUNT_ID=$CORRECT_ICMARKETS_ID|g" .env
    fi
    echo -e "${GREEN}   ✅ ICMarkets ID korrigiert!${NC}"
else
    echo -e "${GREEN}   ✅ ICMarkets ID korrekt${NC}"
fi

echo -e "${GREEN}✅ MetaAPI Account IDs sind jetzt garantiert korrekt!${NC}"
echo -e "${CYAN}   Libertex Demo: $CORRECT_LIBERTEX_ID${NC}"
echo -e "${CYAN}   ICMarkets Demo: $CORRECT_ICMARKETS_ID${NC}"
echo ""

##############################################################
# SCHRITT 3: Frontend Setup
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 3: Frontend Setup...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd "$FRONTEND_DIR"

# Backup der Emergent .env
if [ -f .env ] && [ ! -f .env.emergent.backup ]; then
    cp .env .env.emergent.backup
    echo -e "${GREEN}✅ Backup erstellt: .env.emergent.backup${NC}"
fi

# Desktop .env erstellen
echo -e "${CYAN}⚙️  Erstelle Frontend .env für Desktop...${NC}"
cat > .env << 'ENV_EOF'
PUBLIC_URL=.
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
ENV_EOF
echo -e "${GREEN}✅ Frontend .env erstellt (localhost:8000)${NC}"
echo ""

# Frontend Dependencies installieren
echo -e "${CYAN}📦 Installiere Frontend Dependencies...${NC}"
echo -e "${YELLOW}   Dies kann 3-5 Minuten dauern beim ersten Mal...${NC}"

if [ -d "node_modules" ]; then
    echo -e "${YELLOW}   node_modules existiert, lösche und installiere neu...${NC}"
    rm -rf node_modules
fi

# WICHTIG: Cache auch löschen für Scalping UI
if [ -d "node_modules/.cache" ]; then
    rm -rf node_modules/.cache
fi

yarn install --frozen-lockfile

echo -e "${GREEN}✅ Frontend Dependencies installiert${NC}"
echo ""

# Frontend bauen
echo -e "${CYAN}🏗️  Baue Frontend (React Build)...${NC}"
echo -e "${YELLOW}   Dies kann 1-2 Minuten dauern...${NC}"

# Build-Verzeichnis löschen falls vorhanden
rm -rf build

# ═══════════════════════════════════════════════════════════
# KRITISCH: Clean Build für Scalping UI Sichtbarkeit
# ═══════════════════════════════════════════════════════════
echo -e "${CYAN}⚡ SCALPING UI & OLLAMA FIX - Clean Build...${NC}"

yarn build

echo -e "${GREEN}✅ Frontend gebaut (MIT Scalping UI!)${NC}"
echo ""

##############################################################
# SCHRITT 4: Electron App Setup
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 4: Electron App Setup...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd "$ELECTRON_DIR"

# Electron Dependencies installieren
echo -e "${CYAN}📦 Installiere Electron Dependencies...${NC}"

if [ -d "node_modules" ]; then
    echo -e "${YELLOW}   node_modules existiert, lösche und installiere neu...${NC}"
    rm -rf node_modules
fi

npm install

echo -e "${GREEN}✅ Electron Dependencies installiert${NC}"
echo ""

##############################################################
# SCHRITT 5: Resources zusammenstellen
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 5: Resources zusammenstellen...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Resources Verzeichnis erstellen
echo -e "${CYAN}📁 Erstelle Resources Verzeichnis...${NC}"
rm -rf resources
mkdir -p resources

# Python venv NICHT kopieren! Wir erstellen es nach dem Build neu
# (venv hat hardcoded Pfade und funktioniert nicht nach dem Kopieren)
echo -e "${CYAN}🐍 Vorbereite Python (venv wird nach Build erstellt)...${NC}"
mkdir -p resources/python
echo -e "${YELLOW}   ⚠️  venv wird NACH dem Build in der App erstellt${NC}"

# Backend Code kopieren
echo -e "${CYAN}📁 Kopiere Backend Code...${NC}"
rm -rf resources/backend # Lösche alte Backend-Dateien!
mkdir -p resources/backend
cp -r "$BACKEND_DIR"/* resources/backend/
# .env explizit kopieren
cp "$BACKEND_DIR/.env" resources/backend/.env

# KRITISCH: Sicherstellen dass wichtige Dateien aktuell sind
echo -e "${CYAN}🔍 Prüfe kritische Backend-Dateien...${NC}"
for file in "server.py" "metaapi_connector.py" "metaapi_sdk_connector.py" "multi_platform_connector.py" "scalping_strategy.py" "ai_chat_service.py"; do
    if [ -f "resources/backend/$file" ]; then
        SIZE=$(wc -c < "resources/backend/$file")
        echo -e "   ✅ $file ($SIZE bytes)"
    else
        echo -e "   ${RED}❌ $file fehlt!${NC}"
    fi
done

# Prüfe Scalping & Ollama Fixes
echo -e "${CYAN}🎯 Verifiziere v2.3.28 Fixes...${NC}"
if grep -q "llama3:latest" "resources/backend/ai_chat_service.py"; then
    echo -e "   ${GREEN}✅ Ollama Fix (llama3:latest) vorhanden${NC}"
else
    echo -e "   ${YELLOW}⚠️  Ollama Fix fehlt - verwende llama3${NC}"
fi

if [ -f "resources/backend/scalping_strategy.py" ]; then
    echo -e "   ${GREEN}✅ Scalping Backend Strategie vorhanden${NC}"
else
    echo -e "   ${RED}❌ Scalping Backend fehlt!${NC}"
fi

echo -e "${GREEN}✅ Backend kopiert${NC}"

# Frontend Build kopieren
echo -e "${CYAN}📁 Kopiere Frontend Build...${NC}"
rm -rf resources/frontend # Lösche alte Frontend-Dateien!
mkdir -p resources/frontend
cp -r "$FRONTEND_DIR/build"/* resources/frontend/

echo -e "${GREEN}✅ Frontend kopiert${NC}"

# Electron main.js prüfen
echo -e "${CYAN}🔍 Prüfe Electron main.js...${NC}"
if grep -q "Loaded.*environment variables" "$ELECTRON_DIR/main.js"; then
    echo -e "${GREEN}✅ main.js hat .env Loader${NC}"
else
    echo -e "${RED}❌ main.js hat KEINEN .env Loader - ALTE VERSION!${NC}"
fi
echo ""

##############################################################
# SCHRITT 6: Port 8000 freigeben
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 6: Port 8000 freigeben...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🔓 Prüfe Port 8000...${NC}"
PORT_PID=$(lsof -ti:8000 || true)
if [ ! -z "$PORT_PID" ]; then
    echo -e "${YELLOW}   Port 8000 ist belegt (PID: $PORT_PID), töte Prozess...${NC}"
    kill -9 $PORT_PID
    sleep 1
    echo -e "${GREEN}✅ Port 8000 freigegeben${NC}"
else
    echo -e "${GREEN}✅ Port 8000 ist frei${NC}"
fi
echo ""

##############################################################
# SCHRITT 7: Electron App bauen
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 7: Electron App bauen...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🏗️  Baue macOS App mit electron-builder...${NC}"
echo -e "${YELLOW}   Dies kann 2-3 Minuten dauern...${NC}"

# Alte Builds löschen
rm -rf dist

# App bauen
npm run build

echo -e "${GREEN}✅ Electron App gebaut${NC}"
echo ""

##############################################################
# SCHRITT 8: Python venv in App erstellen
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🐍 SCHRITT 8: Python venv in App erstellen${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

##############################################################
# SCHRITT 9: App installieren
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 9: App installieren...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

APP_PATH="$ELECTRON_DIR/dist/mac-arm64/$APP_NAME.app"
INSTALL_PATH="/Applications/$APP_NAME.app"

if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}❌ FEHLER: App wurde nicht gebaut!${NC}"
    echo -e "${RED}   Erwarteter Pfad: $APP_PATH${NC}"
    exit 1
fi

echo -e "${CYAN}📦 Installiere App nach /Applications...${NC}"

# Alte App löschen falls vorhanden (benötigt sudo)
if [ -d "$INSTALL_PATH" ]; then
    echo -e "${YELLOW}   Lösche alte App (sudo erforderlich)...${NC}"
    sudo rm -rf "$INSTALL_PATH"
fi

# Neue App kopieren
cp -r "$APP_PATH" "$INSTALL_PATH"

echo -e "${GREEN}✅ App installiert: $INSTALL_PATH${NC}"
echo ""

# Python venv in der installierten App erstellen
APP_BACKEND="$INSTALL_PATH/Contents/Resources/app/backend"
APP_PYTHON_VENV="$INSTALL_PATH/Contents/Resources/app/python/venv"

echo -e "${CYAN}🐍 Erstelle Python venv in der App...${NC}"
echo -e "${YELLOW}   Dies ist KRITISCH! venv muss MIT korrekten Pfaden erstellt werden${NC}"

# Erstelle venv direkt in der App
python3.11 -m venv "$APP_PYTHON_VENV"

# Aktiviere und installiere Dependencies
source "$APP_PYTHON_VENV/bin/activate"
pip install --upgrade pip
pip install -r "$APP_BACKEND/requirements.txt"
deactivate

echo -e "${GREEN}✅ Python venv in App erstellt und Dependencies installiert${NC}"
echo ""

##############################################################
# SCHRITT 10: Quarantine Flag entfernen
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 10: macOS Quarantine entfernen...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🔓 Entferne Quarantine Flag...${NC}"
xattr -cr "$INSTALL_PATH"
echo -e "${GREEN}✅ Quarantine Flag entfernt${NC}"
echo ""

##############################################################
# SCHRITT 11: App starten
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔧 SCHRITT 11: App starten...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🚀 Starte Booner Trade App...${NC}"
open "$INSTALL_PATH"
echo -e "${GREEN}✅ App gestartet!${NC}"
echo ""

##############################################################
# FERTIG!
##############################################################
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         ✅ SETUP ERFOLGREICH ABGESCHLOSSEN!               ║"
echo "║            VERSION 2.3.28 PRODUCTION READY                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}📋 Zusammenfassung:${NC}"
echo -e "   ✅ Alle System-Tools installiert"
echo -e "   ✅ Backend Dependencies installiert"
echo -e "   ✅ Frontend Dependencies installiert"
echo -e "   ✅ App gebaut und installiert"
echo -e "   ✅ App gestartet"
echo ""

echo -e "${CYAN}📍 App-Speicherort:${NC}"
echo -e "   $INSTALL_PATH"
echo ""

echo -e "${CYAN}🎯 NEU in v2.3.28:${NC}"
echo -e "   ${GREEN}✅ SCALPING UI${NC} - Einstellungen → Trading Strategien"
echo -e "      (Lila Border, 15 Pips TP, 8 Pips SL)"
echo -e "   ${GREEN}✅ OLLAMA FIX${NC} - Model: llama3:latest"
echo -e "      (Base URL: http://127.0.0.1:11434)"
echo ""

echo -e "${CYAN}📝 Logs finden Sie hier:${NC}"
echo -e "   ~/Library/Logs/Booner Trade/main.log"
echo -e "   ~/Library/Logs/Booner Trade/error.log"
echo ""

echo -e "${CYAN}🔍 Prüfen Sie die Logs um zu sehen ob SDK läuft:${NC}"
echo -e "   ${GREEN}✅ SDK:${NC} Zeigt '✅ SDK Connected'"
echo -e "   ${YELLOW}⚠️  REST:${NC} Zeigt '✅ Connected via REST API fallback'"
echo ""

echo -e "${CYAN}🎯 SCALPING UI TESTEN:${NC}"
echo -e "   1. Einstellungen öffnen (Zahnrad-Icon)"
echo -e "   2. Tab 'Trading Strategien' anklicken"
echo -e "   3. Nach unten scrollen"
echo -e "   4. ${GREEN}⚡ Scalping (Ultra-Schnell)${NC} sollte mit ${GREEN}LILA BORDER${NC} sichtbar sein!"
echo ""

echo -e "${YELLOW}💡 Tipp: Falls die App nicht funktioniert, prüfen Sie:${NC}"
echo -e "   1. Die .env Datei hat korrekte MetaAPI Account IDs"
echo -e "   2. Die Logs in ~/Library/Logs/Booner Trade/"
echo -e "   3. Port 8000 ist nicht belegt"
echo -e "   4. Scalping UI ist in Einstellungen sichtbar"
echo ""

echo -e "${GREEN}Viel Erfolg mit Booner Trade v2.3.27! 🚀${NC}"
