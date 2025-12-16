#!/bin/bash

##############################################################
# QUICK-FIX: main.js in installierte App kopieren
# 
# Nutzen: Wenn nur main.js geändert wurde, kann dieser
# Befehl die Datei direkt in die installierte App kopieren,
# ohne die komplette App neu zu bauen.
#
# WICHTIG: Die App muss bereits installiert sein!
##############################################################

set -e

# Farben
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  QUICK-FIX: main.js in installierte App kopieren         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_MAIN="$SCRIPT_DIR/main.js"
APP_PATH="/Applications/Booner Trade.app"
TARGET_MAIN="$APP_PATH/Contents/Resources/app/main.js"

# Prüfe ob Source existiert
if [ ! -f "$SOURCE_MAIN" ]; then
    echo -e "${RED}❌ Fehler: main.js nicht gefunden!${NC}"
    echo "   Erwartet: $SOURCE_MAIN"
    exit 1
fi

# Prüfe ob App installiert ist
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}❌ Fehler: Booner Trade App nicht installiert!${NC}"
    echo "   Erwartet: $APP_PATH"
    echo ""
    echo "   Bitte erst die App bauen mit: ./BUILD-MACOS-COMPLETE.sh"
    exit 1
fi

echo -e "${YELLOW}Dieser Befehl benötigt sudo-Rechte.${NC}"
echo ""

# Backup erstellen
if [ -f "$TARGET_MAIN" ]; then
    echo "📋 Erstelle Backup der alten main.js..."
    sudo cp "$TARGET_MAIN" "$TARGET_MAIN.backup"
    echo -e "${GREEN}✅ Backup erstellt: $TARGET_MAIN.backup${NC}"
fi

# Kopiere neue main.js
echo "📋 Kopiere neue main.js in die App..."
sudo cp "$SOURCE_MAIN" "$TARGET_MAIN"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ main.js erfolgreich aktualisiert!${NC}"
    echo ""
    echo -e "${BLUE}📝 Nächste Schritte:${NC}"
    echo "   1. Starte die App: open '/Applications/Booner Trade.app'"
    echo "   2. Prüfe Logs: tail -f ~/Library/Logs/Booner\\ Trade/main.log"
    echo ""
    echo -e "${YELLOW}💡 Tipp:${NC}"
    echo "   Falls die App nicht startet, Backup wiederherstellen:"
    echo "   sudo cp '$TARGET_MAIN.backup' '$TARGET_MAIN'"
else
    echo -e "${RED}❌ Fehler beim Kopieren!${NC}"
    exit 1
fi
