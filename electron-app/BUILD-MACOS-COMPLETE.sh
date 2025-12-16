#!/bin/bash

##############################################################
# BOONER TRADE - KOMPLETTER AUTOMATISCHER macOS BUILD
# 
# Was dieses Script macht:
# 1. Baut Frontend (React)
# 2. Erstellt Python venv
# 3. Kopiert alle Resources
# 4. Baut Electron App
# 5. Löscht alte App
# 6. Installiert neue App
# 7. Entfernt Quarantine Flag
# 8. Öffnet App
#
# Version 2.0 - Verbessert mit Helper Scripts
##############################################################

set -e  # Exit bei Fehler

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  BOONER TRADE - KOMPLETTER AUTOMATISCHER macOS BUILD     ║"
echo "║  Für macOS M4 ARM64                                       ║"
echo "║  Version 2.0                                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verzeichnisse - automatisch erkannt basierend auf Script-Location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ELECTRON_DIR="$SCRIPT_DIR"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
RESOURCES_DIR="$ELECTRON_DIR/resources"
APP_NAME="Booner Trade"
APP_PATH="$ELECTRON_DIR/dist/mac-arm64/$APP_NAME.app"
INSTALL_PATH="/Applications/$APP_NAME.app"

echo -e "${GREEN}📁 Projekt-Verzeichnisse:${NC}"
echo "   PROJECT_ROOT: $PROJECT_ROOT"
echo "   ELECTRON_DIR: $ELECTRON_DIR"
echo "   RESOURCES_DIR: $RESOURCES_DIR"
echo ""

##############################################################
# SCHRITT 1: Port 8000 freigeben (falls belegt)
##############################################################
echo -e "${BLUE}🔓 SCHRITT 1/10: Port 8000 freigeben...${NC}"

# Nutze das KILL-PORT-8000.sh Helper Script
if [ -f "$SCRIPT_DIR/KILL-PORT-8000.sh" ]; then
    bash "$SCRIPT_DIR/KILL-PORT-8000.sh"
else
    echo -e "${YELLOW}   ⚠️ KILL-PORT-8000.sh nicht gefunden, überspringe...${NC}"
fi

echo ""

##############################################################
# SCHRITT 2: Frontend .env für Desktop anpassen
##############################################################
echo -e "${BLUE}⚙️ SCHRITT 2/10: Frontend .env für Desktop anpassen...${NC}"

cd "$FRONTEND_DIR"

# Backup der originalen .env (für Emergent Platform)
if [ -f .env ] && [ ! -f .env.emergent.backup ]; then
    cp .env .env.emergent.backup
    echo "   ✅ Backup erstellt: .env.emergent.backup"
fi

# Erstelle Desktop .env
cat > .env << 'ENV_EOF'
PUBLIC_URL=.
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
ENV_EOF

echo "   ✅ Frontend .env angepasst für Desktop (localhost:8000)"
echo ""

##############################################################
# SCHRITT 3: Frontend Dependencies installieren
##############################################################
echo -e "${BLUE}📦 SCHRITT 3/10: Frontend Dependencies installieren...${NC}"

# Prüfe ob node_modules existiert
if [ ! -d "node_modules" ]; then
    echo "   Installiere Dependencies (dauert beim ersten Mal 2-3 Minuten)..."
    yarn install --frozen-lockfile
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Dependencies installiert"
    else
        echo -e "${RED}   ❌ yarn install fehlgeschlagen!${NC}"
        exit 1
    fi
else
    echo "   ✅ node_modules existiert bereits"
fi

echo ""

##############################################################
# SCHRITT 4: Frontend Build
##############################################################
echo -e "${BLUE}🔨 SCHRITT 4/10: Frontend bauen...${NC}"

echo "   Backend URL: http://localhost:8000"
echo "   Building..."

yarn build

if [ ! -d "$FRONTEND_DIR/build" ]; then
    echo -e "${RED}❌ Frontend Build fehlgeschlagen!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend gebaut${NC}"
echo ""

##############################################################
# SCHRITT 5: Resources Ordner vorbereiten
##############################################################
echo -e "${BLUE}🗑️ SCHRITT 5/10: Alte Resources löschen...${NC}"

cd "$ELECTRON_DIR"

if [ -d "$RESOURCES_DIR" ]; then
    rm -rf "$RESOURCES_DIR"
    echo "   Alte Resources gelöscht"
fi

mkdir -p "$RESOURCES_DIR/python"
mkdir -p "$RESOURCES_DIR/backend"
mkdir -p "$RESOURCES_DIR/frontend"

echo -e "${GREEN}✅ Resources Ordner vorbereitet${NC}"
echo ""

##############################################################
# SCHRITT 6: Python 3.11 sicherstellen & venv erstellen
##############################################################
echo -e "${BLUE}🐍 SCHRITT 6/10: Python 3.11 prüfen/installieren...${NC}"

# Suche Python 3.11
PYTHON_CMD=""
if [ -f "/opt/homebrew/bin/python3.11" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3.11"
    echo "   ✅ Python 3.11 gefunden (Homebrew)"
elif [ -f "/usr/local/bin/python3.11" ]; then
    PYTHON_CMD="/usr/local/bin/python3.11"
    echo "   ✅ Python 3.11 gefunden (lokal)"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    echo "   ✅ Python 3.11 gefunden (System)"
fi

# Falls nicht gefunden: Automatisch installieren
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}   ⚠️ Python 3.11 nicht gefunden!${NC}"
    echo "   📦 Installiere Python 3.11 via Homebrew..."
    
    # Prüfe ob Homebrew installiert ist
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}   ❌ Homebrew nicht installiert!${NC}"
        echo "   Bitte installiere Homebrew: https://brew.sh"
        exit 1
    fi
    
    # Installiere Python 3.11
    echo "   Dies dauert ca. 2-3 Minuten..."
    brew install python@3.11
    
    if [ $? -eq 0 ]; then
        PYTHON_CMD="/opt/homebrew/bin/python3.11"
        echo -e "${GREEN}   ✅ Python 3.11 erfolgreich installiert!${NC}"
    else
        echo -e "${RED}   ❌ Installation fehlgeschlagen!${NC}"
        exit 1
    fi
fi

# Version anzeigen
echo -e "${GREEN}   Python Version: $($PYTHON_CMD --version)${NC}"

# WICHTIG: --copies für macOS (keine Symlinks!)
echo "   Erstelle Virtual Environment..."
$PYTHON_CMD -m venv --copies "$RESOURCES_DIR/python/venv"

if [ ! -f "$RESOURCES_DIR/python/venv/bin/python3" ]; then
    echo -e "${RED}❌ Python venv konnte nicht erstellt werden!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python venv erstellt (mit --copies für macOS)${NC}"
echo ""

##############################################################
# SCHRITT 7: Python Dependencies installieren
##############################################################
echo -e "${BLUE}📦 SCHRITT 7/10: Python Dependencies installieren...${NC}"

source "$RESOURCES_DIR/python/venv/bin/activate"

pip install --upgrade pip > /dev/null 2>&1
pip install -r "$BACKEND_DIR/requirements.txt"

deactivate

echo -e "${GREEN}✅ Dependencies installiert${NC}"
echo ""

##############################################################
# SCHRITT 8: Backend, Frontend & .env kopieren
##############################################################
echo -e "${BLUE}📋 SCHRITT 8/10: Backend, Frontend & .env kopieren...${NC}"

# Backend kopieren
cp -r "$BACKEND_DIR/"* "$RESOURCES_DIR/backend/"
echo "   Backend kopiert"

# Frontend Build kopieren
cp -r "$FRONTEND_DIR/build/"* "$RESOURCES_DIR/frontend/"
echo "   Frontend kopiert"

# .env kopieren
if [ -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env" "$RESOURCES_DIR/backend/.env"
    echo "   .env kopiert"
else
    echo -e "${YELLOW}   ⚠️ Warnung: .env nicht gefunden${NC}"
fi

echo -e "${GREEN}✅ Alle Files kopiert${NC}"
echo ""

##############################################################
# SCHRITT 9: Electron Dependencies installieren & App bauen
##############################################################
echo -e "${BLUE}🏗️ SCHRITT 9/10: Electron App bauen...${NC}"

cd "$ELECTRON_DIR"

# Prüfe ob node_modules existiert
if [ ! -d "node_modules" ]; then
    echo "   Installiere Electron Dependencies..."
    npm install
    if [ $? -eq 0 ]; then
        echo "   ✅ Electron Dependencies installiert"
    else
        echo -e "${RED}   ❌ npm install fehlgeschlagen!${NC}"
        exit 1
    fi
else
    echo "   ✅ Electron node_modules existiert bereits"
fi

cd "$ELECTRON_DIR"

# Build für macOS ARM64
echo "   Starte electron-builder..."
npm run build

if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}❌ App Build fehlgeschlagen!${NC}"
    echo "   Erwarteter Pfad: $APP_PATH"
    exit 1
fi

echo -e "${GREEN}✅ Electron App gebaut${NC}"
echo "   App Path: $APP_PATH"
echo ""

##############################################################
# SCHRITT 10: Alte App löschen & neue installieren
##############################################################
echo -e "${BLUE}🗑️ SCHRITT 10/10: Alte App löschen & neue installieren...${NC}"

# Alte App löschen falls vorhanden
if [ -d "$INSTALL_PATH" ]; then
    echo "   Lösche alte App (benötigt sudo)..."
    sudo rm -rf "$INSTALL_PATH"
    echo "   Alte App gelöscht"
fi

# Neue App kopieren
echo "   Kopiere neue App nach /Applications (benötigt sudo)..."
sudo cp -R "$APP_PATH" "/Applications/"

if [ ! -d "$INSTALL_PATH" ]; then
    echo -e "${RED}❌ Installation fehlgeschlagen!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ App installiert in /Applications${NC}"
echo ""

##############################################################
# FINALE: Quarantine entfernen & App öffnen
##############################################################
echo -e "${BLUE}🔓 FINALE: Quarantine entfernen & App starten...${NC}"

# Quarantine Flag entfernen
echo "   Entferne Quarantine Flag (benötigt sudo)..."
sudo xattr -cr "$INSTALL_PATH"

# Prüfen ob erfolgreich
if xattr "$INSTALL_PATH" 2>/dev/null | grep -q "com.apple.quarantine"; then
    echo -e "${YELLOW}   ⚠️ Quarantine Flag konnte nicht vollständig entfernt werden${NC}"
else
    echo "   ✅ Quarantine Flag entfernt"
fi

# Warte kurz bevor App geöffnet wird
sleep 2

# App öffnen
echo "   Öffne App..."
open "$INSTALL_PATH"

echo -e "${GREEN}✅ App geöffnet${NC}"
echo ""

##############################################################
# FERTIG!
##############################################################
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ BUILD ERFOLGREICH ABGESCHLOSSEN!                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BLUE}📊 Zusammenfassung:${NC}"
echo "   ✅ Port 8000 freigegeben"
echo "   ✅ Frontend .env angepasst (Desktop Mode)"
echo "   ✅ Frontend Dependencies installiert"
echo "   ✅ Frontend gebaut (REACT_APP_BACKEND_URL=http://localhost:8000)"
echo "   ✅ Python venv erstellt (mit --copies für macOS)"
echo "   ✅ Python Dependencies installiert"
echo "   ✅ Resources kopiert"
echo "   ✅ Electron App gebaut"
echo "   ✅ Alte App gelöscht"
echo "   ✅ Neue App installiert"
echo "   ✅ Quarantine Flag entfernt"
echo "   ✅ App geöffnet"
echo ""

echo -e "${GREEN}🎉 Die App sollte jetzt laufen!${NC}"
echo ""
echo -e "${YELLOW}📝 Hinweise:${NC}"
echo "   - Backend läuft auf: http://localhost:8000 (API)"
echo "   - Frontend ist in der Electron App embedded"
echo "   - Logs: ~/Library/Logs/Booner Trade/"
echo ""
echo -e "${YELLOW}⚠️ WICHTIG:${NC}"
echo "   Die Frontend .env wurde für Desktop angepasst!"
echo "   Original gesichert als: frontend/.env.emergent.backup"
echo "   Für Emergent Platform: Nutze RESTORE-EMERGENT-ENV.sh"
echo ""
echo -e "${BLUE}🔍 Falls Probleme auftreten:${NC}"
echo "   1. Prüfe Logs: tail -f ~/Library/Logs/Booner\\ Trade/main.log"
echo "   2. Prüfe Errors: tail -f ~/Library/Logs/Booner\\ Trade/error.log"
echo "   3. Siehe Dokumentation: /app/BOONER-TRADE-APP-VOLLSTAENDIGE-DOKUMENTATION.md"
echo ""
echo -e "${GREEN}💡 Quick-Fix (wenn nur main.js geändert wurde):${NC}"
echo "   sudo cp /app/electron-app/main.js \"/Applications/Booner Trade.app/Contents/Resources/app/main.js\""
echo "   (Startet die App mit der neuen main.js ohne kompletten Rebuild)"
echo ""
