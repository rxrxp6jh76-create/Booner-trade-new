#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       🚀 BOONER TRADE V2.3.12 - KOMPLETTINSTALLATION      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -1. ALTE BACKEND-PROZESSE KILLEN (2x für Sicherheit!)
echo -e "${CYAN}💀 Schritt -1: Alte Backend-Prozesse beenden...${NC}"
if [ -f "$SCRIPT_DIR/KILL-OLD-BACKENDS.sh" ]; then
    chmod +x "$SCRIPT_DIR/KILL-OLD-BACKENDS.sh"
    "$SCRIPT_DIR/KILL-OLD-BACKENDS.sh" || true
    echo -e "${CYAN}⏱️  Warte 5 Sekunden...${NC}"
    sleep 5
    "$SCRIPT_DIR/KILL-OLD-BACKENDS.sh" || true
    echo -e "${GREEN}✅ Alte Prozesse beendet${NC}"
else
    echo -e "${CYAN}ℹ️  KILL-OLD-BACKENDS.sh nicht gefunden, überspringe...${NC}"
fi
echo ""

# 0. DATENBANK LÖSCHEN (WICHTIG!)
echo -e "${CYAN}🗑️  Schritt 0: Alte Datenbank löschen...${NC}"
rm -f "$SCRIPT_DIR/backend/trading.db"
rm -f "$SCRIPT_DIR/backend/trading.db-shm"
rm -f "$SCRIPT_DIR/backend/trading.db-wal"
echo -e "${GREEN}✅ Datenbank gelöscht (wird neu erstellt)${NC}"
echo ""

# 1. ALLES ALTE LÖSCHEN
echo -e "${CYAN}🗑️  Schritt 1: Alte Installation komplett entfernen...${NC}"
rm -rf "/Applications/Booner Trade.app"
rm -rf "/Applications/Booner.app"
rm -rf ~/Booner-App
rm -rf ~/Library/Application\ Support/Booner\ Trade
rm -rf ~/Library/Application\ Support/Booner
rm -rf ~/Library/Application\ Support/booner-trade
rm -rf ~/Library/Caches/Booner\ Trade
rm -rf ~/Library/Caches/Booner
echo -e "${GREEN}✅ Alte Installation entfernt${NC}"
echo ""

# 2. INSTALLATION
echo -e "${CYAN}📦 Schritt 2: Installiere neue Version...${NC}"
cd "$SCRIPT_DIR"
chmod +x COMPLETE-MACOS-SETUP.sh
./COMPLETE-MACOS-SETUP.sh

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ INSTALLATION ABGESCHLOSSEN               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Kritische Fixes in v2.3.3:${NC}"
echo "  ✅ Settings Persistence über App-Restart"
echo "  ✅ App Crash nach 10 Min behoben"
echo "  ✅ SL/TP Updates auf offene Trades"
echo "  ✅ MetaAPI IDs korrigiert"
echo "  ✅ Database Symlinks"
echo ""
echo -e "${CYAN}Bekannte Issues:${NC}"
echo "  ⚠️  Checkbox Visualisierung (Funktion OK)"
echo ""
echo -e "${GREEN}App starten:${NC}"
echo "  open -a 'Booner Trade'"
echo ""
