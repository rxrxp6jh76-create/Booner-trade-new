#!/bin/bash

################################################################################
# Kopiere .env in die LAUFENDE App (ohne Rebuild!)
################################################################################

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔧 Kopiere .env in die App..."

APP_BACKEND="/Applications/Booner Trade.app/Contents/Resources/app/backend"
SOURCE_ENV="/Users/dj1dbr/mein_python_projekt/Rohstofftrader/Booner-Trade/backend/.env"

# Prüfe ob App existiert
if [ ! -d "$APP_BACKEND" ]; then
    echo -e "${RED}❌ App nicht gefunden: $APP_BACKEND${NC}"
    exit 1
fi

# Prüfe ob .env existiert
if [ ! -f "$SOURCE_ENV" ]; then
    echo -e "${RED}❌ .env nicht gefunden: $SOURCE_ENV${NC}"
    exit 1
fi

# Kopiere .env
cp "$SOURCE_ENV" "$APP_BACKEND/.env"

echo -e "${GREEN}✅ .env kopiert nach: $APP_BACKEND/.env${NC}"
echo ""
echo "📋 MetaAPI Konfiguration:"
grep "METAAPI" "$APP_BACKEND/.env" | grep -v "^#"
echo ""
echo -e "${YELLOW}🔄 Bitte starten Sie die App NEU:${NC}"
echo -e "${YELLOW}   open '/Applications/Booner Trade.app'${NC}"
