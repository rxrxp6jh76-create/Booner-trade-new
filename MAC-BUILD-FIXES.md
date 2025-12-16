# 🍎 MAC BUILD FIXES - v2.3.26

## KRITISCHE FIXES FÜR MAC

### 1. Ollama URL Fix
**Problem:** `localhost:11434` funktioniert nicht auf Mac
**Lösung:** `127.0.0.1:11434` verwenden

**In Settings UI:**
- Standard URL: `http://127.0.0.1:11434`
- Ollama Model: `llama2` (oder was Du mit `ollama pull` installiert hast)

### 2. Scalping UI ist definitiv vorhanden
**Location:** Dashboard.jsx Zeile 2911-2984
**Struktur:**
```
Trading Strategien Section (Zeile 2637-2985)
├── Swing Trading (2648-2778)
├── Day Trading (2781-2909)
└── Scalping (2911-2984) ← HIER!
```

### 3. Build Cleanup
Vor dem Build:
```bash
cd BOONER-V2.3.26-MAC-FIX/frontend
rm -rf node_modules
rm -rf build
yarn install
```

### 4. Electron Cache leeren
```bash
# Auf Mac
rm -rf ~/Library/Application\ Support/booner-trade/
rm -rf ~/Library/Caches/booner-trade/
```

## VOLLSTÄNDIGER BUILD PROZESS:

```bash
cd BOONER-V2.3.26-MAC-FIX

# 1. Backend Dependencies
cd backend
pip3 install -r requirements.txt

# 2. Frontend Clean Build
cd ../frontend
rm -rf node_modules build
yarn install
yarn build

# 3. Electron Build
cd ../electron-app
yarn install
yarn build

# 4. App öffnen
open dist/mac/Booner-Trade.app
```

## SETTINGS PRÜFEN:

Nach Start der App:
1. Öffne Einstellungen
2. **Scrolle KOMPLETT runter** zu "Trading Strategien"
3. Du MUSST 3 Strategien sehen:
   - Swing Trading (grün)
   - Day Trading (blau)  
   - Scalping (lila) ← HIER!

Falls Scalping NICHT sichtbar:
- App komplett schließen
- Cache leeren (siehe oben)
- Neu starten

## OLLAMA SETUP:

1. Prüfe ob Ollama läuft:
```bash
curl http://127.0.0.1:11434/api/tags
```

2. Falls 404:
```bash
ollama serve
```

3. In App Settings:
- Ollama Base URL: `http://127.0.0.1:11434`
- Ollama Model: `llama2` (oder dein Modell)
- Test mit AI Chat

## TROUBLESHOOTING:

### Scalping nicht sichtbar:
- Electron DevTools öffnen: View → Toggle Developer Tools
- Console prüfen auf Errors
- Settings Dialog schließen und neu öffnen
- Komplett neu builden

### Ollama 404:
- URL muss `127.0.0.1` sein (nicht `localhost`)
- Ollama muss laufen (Lama-Icon in Menu Bar)
- Firewall prüfen
- Port 11434 muss frei sein

### Build Fehler:
- Node.js Version prüfen (sollte v18+)
- Yarn Version prüfen
- Dependencies neu installieren
