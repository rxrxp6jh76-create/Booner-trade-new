#!/bin/bash

##############################################################
# RESTORE EMERGENT PLATFORM .ENV
# 
# Nach dem Desktop Build: Stelle die originale .env wieder her
# für die Emergent Platform
##############################################################

set -e

FRONTEND_DIR="/app/frontend"

echo "🔄 Stelle Emergent Platform .env wieder her..."

if [ -f "$FRONTEND_DIR/.env.emergent.backup" ]; then
    cp "$FRONTEND_DIR/.env.emergent.backup" "$FRONTEND_DIR/.env"
    echo "✅ Frontend .env wiederhergestellt"
    echo ""
    echo "Aktuelle .env:"
    cat "$FRONTEND_DIR/.env"
else
    echo "⚠️ Keine Backup-Datei gefunden!"
    echo "Erstelle neue Emergent .env..."
    
    cat > "$FRONTEND_DIR/.env" << 'ENV_EOF'
PUBLIC_URL=.
REACT_APP_BACKEND_URL=https://tradeboost-3.preview.emergentagent.com
WDS_SOCKET_PORT=443
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
ENV_EOF
    
    echo "✅ Emergent .env erstellt"
fi

echo ""
echo "✅ Fertig! Du kannst jetzt wieder auf Emergent Platform entwickeln."
