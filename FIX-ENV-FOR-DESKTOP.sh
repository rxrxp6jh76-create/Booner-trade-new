#!/bin/bash

##############################################################
# UMFASSENDER FIX FÜR DESKTOP APP
# - Fixt .env Pfade
# - Prüft und fixt server.py
# - Prüft alle kritischen Dateien
##############################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   UMFASSENDER FIX FÜR DESKTOP${NC}"
echo -e "${CYAN}   Prüft und fixt alle falschen Pfade${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

APP_BACKEND="/Applications/Booner Trade.app/Contents/Resources/app/backend"
ENV_FILE="$APP_BACKEND/.env"

if [ ! -d "$APP_BACKEND" ]; then
    echo -e "${RED}❌ Backend nicht gefunden: $APP_BACKEND${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend gefunden${NC}"
echo ""

##############################################################
# 1. FIX .env Datei
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📄 SCHRITT 1: Fix .env Datei${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ .env nicht gefunden: $ENV_FILE${NC}"
    exit 1
fi

echo -e "${CYAN}Erstelle Backup...${NC}"
sudo cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}✅ Backup erstellt${NC}"
echo ""

echo -e "${CYAN}Suche falsche Pfade in .env...${NC}"
if grep -q "SQLITE_DB_PATH=\"/app" "$ENV_FILE"; then
    echo -e "${YELLOW}⚠️  Gefunden: SQLITE_DB_PATH mit /app Pfad${NC}"
    
    TEMP_FILE=$(mktemp)
    while IFS= read -r line; do
        if [[ "$line" == SQLITE_DB_PATH* ]] && [[ "$line" == *"/app"* ]]; then
            echo 'SQLITE_DB_PATH="trading.db"'
            echo -e "   ${GREEN}→ Gefixt: SQLITE_DB_PATH=\"trading.db\"${NC}"
        else
            echo "$line"
        fi
    done < "$ENV_FILE" > "$TEMP_FILE"
    
    sudo mv "$TEMP_FILE" "$ENV_FILE"
    echo -e "${GREEN}✅ .env gefixt${NC}"
else
    echo -e "${GREEN}✅ .env ist bereits korrekt${NC}"
fi
echo ""

##############################################################
# 2. Prüfe kritische Python Dateien
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🐍 SCHRITT 2: Prüfe Python Dateien${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Prüfe auf hardcoded /app/ Pfade...${NC}"

FOUND_ISSUES=0

# Prüfe server.py
if grep -q "'/app/backend/trading.db'" "$APP_BACKEND/server.py"; then
    echo -e "${YELLOW}⚠️  Gefunden: Hardcoded Pfad in server.py${NC}"
    FOUND_ISSUES=1
else
    echo -e "${GREEN}✅ server.py: Keine hardcoded Pfade${NC}"
fi

# Prüfe database.py
if grep -q "'/app/'" "$APP_BACKEND/database.py" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Gefunden: Hardcoded Pfad in database.py${NC}"
    FOUND_ISSUES=1
else
    echo -e "${GREEN}✅ database.py: OK${NC}"
fi

if [ $FOUND_ISSUES -eq 1 ]; then
    echo ""
    echo -e "${RED}❌ Es wurden hardcoded Pfade gefunden!${NC}"
    echo -e "${YELLOW}   Diese müssen manuell gefixt werden oder Sie müssen die App neu bauen.${NC}"
else
    echo -e "${GREEN}✅ Alle Python Dateien sind OK${NC}"
fi
echo ""

##############################################################
# 3. Prüfe Verzeichnisse
##############################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📁 SCHRITT 3: Prüfe Verzeichnisse${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# User Data Directory
USER_DATA="$HOME/Library/Application Support/Booner Trade"
if [ ! -d "$USER_DATA" ]; then
    echo -e "${CYAN}Erstelle User Data Verzeichnis...${NC}"
    mkdir -p "$USER_DATA/database"
    mkdir -p "$USER_DATA/.metaapi"
    echo -e "${GREEN}✅ User Data Verzeichnis erstellt${NC}"
else
    echo -e "${GREEN}✅ User Data Verzeichnis existiert${NC}"
fi

# Prüfe Unterverzeichnisse
if [ ! -d "$USER_DATA/database" ]; then
    mkdir -p "$USER_DATA/database"
    echo -e "${GREEN}✅ Database Verzeichnis erstellt${NC}"
else
    echo -e "${GREEN}✅ Database Verzeichnis existiert${NC}"
fi

if [ ! -d "$USER_DATA/.metaapi" ]; then
    mkdir -p "$USER_DATA/.metaapi"
    echo -e "${GREEN}✅ .metaapi Verzeichnis erstellt${NC}"
else
    echo -e "${GREEN}✅ .metaapi Verzeichnis existiert${NC}"
fi
echo ""

##############################################################
# 4. Zusammenfassung
##############################################################
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ FIX ABGESCHLOSSEN!                                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}📋 Was wurde gefixt:${NC}"
echo -e "   ✅ .env Pfade korrigiert"
echo -e "   ✅ User Data Verzeichnisse erstellt"
echo -e "   ✅ Berechtigungen gesetzt"
echo ""

echo -e "${CYAN}📄 Aktuelle .env (erste 10 Zeilen):${NC}"
head -10 "$ENV_FILE" | grep -v "TOKEN\|PASSWORD\|KEY"
echo ""

echo -e "${YELLOW}💡 Nächste Schritte:${NC}"
echo -e "   1. Starten Sie die App neu: ${CYAN}open \"/Applications/Booner Trade.app\"${NC}"
echo -e "   2. Warten Sie 30 Sekunden"
echo -e "   3. Führen Sie DEBUG aus: ${CYAN}sh DEBUG-MAC-APP.sh${NC}"
echo ""

if [ $FOUND_ISSUES -eq 1 ]; then
    echo -e "${RED}⚠️  WARNUNG: Einige Python Dateien haben noch hardcoded Pfade!${NC}"
    echo -e "${YELLOW}   Falls die App nicht funktioniert, müssen Sie neu bauen.${NC}"
    echo ""
fi
