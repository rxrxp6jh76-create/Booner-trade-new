#!/bin/bash

# 🔍 Booner Trade App Finder v2.3.14
# Findet die gebaute macOS App

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Suche nach Booner Trade App v2.3.14 (DEBUG VERSION)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Standard-Pfad
STANDARD_PATH="electron-app/dist/mac-arm64/Booner Trade.app"

if [ -d "$STANDARD_PATH" ]; then
    echo "✅ App gefunden!"
    echo ""
    echo "📍 Speicherort:"
    echo "   $(pwd)/$STANDARD_PATH"
    echo ""
    echo "📊 App-Informationen:"
    ls -lh "$STANDARD_PATH"
    echo ""
    echo "🚀 App öffnen mit:"
    echo "   open \"$STANDARD_PATH\""
    echo ""
    
    # Frage ob App geöffnet werden soll
    read -p "Möchten Sie die App jetzt öffnen? (j/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[JjYy]$ ]]; then
        echo "🚀 Öffne App..."
        open "$STANDARD_PATH"
        echo "✅ App geöffnet!"
    fi
else
    echo "❌ App nicht gefunden im Standard-Pfad:"
    echo "   $STANDARD_PATH"
    echo ""
    echo "🔍 Suche in allen dist-Ordnern..."
    
    # Suche in allen dist-Ordnern
    FOUND=$(find electron-app/dist -name "*.app" -type d 2>/dev/null)
    
    if [ -n "$FOUND" ]; then
        echo "✅ Gefundene Apps:"
        echo "$FOUND"
        echo ""
        echo "📍 Erste App öffnen mit:"
        FIRST_APP=$(echo "$FOUND" | head -1)
        echo "   open \"$FIRST_APP\""
    else
        echo "❌ Keine .app-Dateien gefunden."
        echo ""
        echo "💡 Die App muss zuerst gebaut werden:"
        echo "   1. ./INSTALL.sh"
        echo "   2. ./COMPLETE-MACOS-SETUP.sh"
        echo ""
        echo "🔍 Prüfe electron-app Verzeichnis..."
        if [ -d "electron-app" ]; then
            echo "   ✅ electron-app Ordner existiert"
            ls -la electron-app/ | head -10
        else
            echo "   ❌ electron-app Ordner nicht gefunden!"
            echo "   Sind Sie im richtigen Verzeichnis?"
            echo "   Aktueller Pfad: $(pwd)"
        fi
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
