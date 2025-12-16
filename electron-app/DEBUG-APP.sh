#!/bin/bash

##############################################################
# DEBUG BOONER TRADE APP
# Zeigt warum die App abstürzt
##############################################################

echo "🔍 DEBUG: Booner Trade App"
echo ""

APP_PATH="/Applications/Booner Trade.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ App nicht gefunden in /Applications"
    exit 1
fi

echo "✅ App gefunden: $APP_PATH"
echo ""

# Prüfe Struktur
echo "📁 App Struktur:"
ls -la "$APP_PATH/Contents/Resources/app/"
echo ""

# Prüfe ob Python existiert
echo "🐍 Python Check:"
if [ -f "$APP_PATH/Contents/Resources/app/python/venv/bin/python3" ]; then
    echo "   ✅ Python gefunden"
    "$APP_PATH/Contents/Resources/app/python/venv/bin/python3" --version
else
    echo "   ❌ Python NICHT gefunden!"
fi
echo ""

# Prüfe ob Uvicorn existiert
echo "🦄 Uvicorn Check:"
if [ -f "$APP_PATH/Contents/Resources/app/python/venv/bin/uvicorn" ]; then
    echo "   ✅ Uvicorn gefunden"
else
    echo "   ❌ Uvicorn NICHT gefunden!"
fi
echo ""

# Prüfe ob Backend existiert
echo "🔧 Backend Check:"
if [ -d "$APP_PATH/Contents/Resources/app/backend" ]; then
    echo "   ✅ Backend Ordner gefunden"
    ls "$APP_PATH/Contents/Resources/app/backend/" | head -5
else
    echo "   ❌ Backend NICHT gefunden!"
fi
echo ""

# Prüfe ob Frontend existiert
echo "🎨 Frontend Check:"
if [ -d "$APP_PATH/Contents/Resources/app/frontend" ]; then
    echo "   ✅ Frontend gefunden"
    ls "$APP_PATH/Contents/Resources/app/frontend/" | head -5
else
    echo "   ❌ Frontend NICHT gefunden!"
fi
echo ""

# Versuche Backend manuell zu starten
echo "🚀 Versuche Backend manuell zu starten..."
echo "   (Drücke Ctrl+C zum Beenden)"
echo ""

cd "$APP_PATH/Contents/Resources/app/backend"
"$APP_PATH/Contents/Resources/app/python/venv/bin/uvicorn" server:app --host 0.0.0.0 --port 8000
