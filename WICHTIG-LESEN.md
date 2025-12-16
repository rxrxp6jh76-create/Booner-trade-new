# ⚠️ WICHTIG - VOR DEM BUILD LESEN!

## 🎯 SCALPING PROBLEM LÖSUNG

### **WARUM Scalping nicht sichtbar war:**

**Das Problem:** React Build Cache!
- Scalping Code IST vorhanden (Zeile 2911-2984 in Dashboard.jsx)
- Aber: `node_modules` und `build/` Ordner sind gecached
- Lösung: **KOMPLETTER CLEAN BUILD**

---

## 🛠️ SCHRITT-FÜR-SCHRITT BUILD ANLEITUNG:

### **1. Alte Version löschen**
```bash
# Alte App und Cache komplett löschen
rm -rf ~/Library/Application\ Support/booner-trade/
rm -rf ~/Library/Caches/booner-trade/
rm -rf /Applications/Booner-Trade.app  # falls vorhanden
```

### **2. Clean Build**
```bash
cd BOONER-V2.3.26-MAC-FIX

# Backend
cd backend
pip3 install -r requirements.txt

# Frontend CLEAN
cd ../frontend
rm -rf node_modules
rm -rf build
rm -rf .cache
yarn cache clean
yarn install
yarn build

# Electron CLEAN
cd ../electron-app
rm -rf node_modules
rm -rf dist
yarn cache clean
yarn install
yarn build
```

### **3. App starten**
```bash
open dist/mac/Booner-Trade.app
```

---

## ✅ SCALPING PRÜFEN:

**In der App:**
1. Klicke "Einstellungen" (⚙️ rechts oben)
2. **Scrolle GANZ nach unten** zu "Trading Strategien"
3. Du **MUSST** jetzt sehen:
   ```
   📈 Swing Trading (grün)
   ⚡ Day Trading (blau)
   ⚡🎯 Scalping (lila) ← NEU!
   ```

**Falls IMMER NOCH nicht da:**
- Öffne Electron DevTools: `View → Toggle Developer Tools`
- Gehe zu `Console` Tab
- Mach Screenshot und schick mir

---

## 🦙 OLLAMA SETUP:

### **Dein Ollama funktioniert bereits!**

Aus Deinem Terminal:
```bash
curl http://127.0.0.1:11434/api/tags
# ✅ Zeigt: llama3:latest
```

### **In den App Settings:**

**Gehe zu Einstellungen → KI Chat Konfiguration:**
1. **AI Provider:** "Ollama (Lokal)"
2. **Ollama Base URL:** `http://127.0.0.1:11434`
3. **Ollama Model:** `llama3:latest` ← WICHTIG! (nicht llama2)
4. Klicke "Speichern"

**Dann teste:**
- Gehe zum AI Chat Tab
- Stelle eine Frage z.B. "Was ist Gold?"
- Sollte jetzt funktionieren!

---

## 🔧 WARUM 404 Fehler?

**Zwei mögliche Gründe:**

### **1. Falscher Model-Name**
```
❌ Falsch: "llama2"
✅ Richtig: "llama3:latest"
```

### **2. Falscher Endpoint**
Die App versucht `/api/generate` aber Ollama erwartet `/api/chat`

**Fix ist bereits in v2.3.26 enthalten!**

---

## 📋 TROUBLESHOOTING:

### Problem: Build Fehler
```bash
# Node Version prüfen
node --version  # Sollte v18 oder höher sein

# Yarn neu installieren
npm install -g yarn

# Xcode Command Line Tools
xcode-select --install
```

### Problem: Python Fehler
```bash
# Python 3 prüfen
python3 --version  # Sollte 3.9 oder höher sein

# pip updaten
python3 -m pip install --upgrade pip
```

### Problem: Electron Build Fehler
```bash
cd electron-app
rm -rf node_modules dist
yarn install
yarn build
```

---

## 📸 WENN NICHTS HILFT:

**Schick mir:**
1. Screenshot von Einstellungen (komplette Seite)
2. Electron Console Log (F12 → Console)
3. Terminal Output vom Build
4. Output von:
   ```bash
   cd frontend
   ls -la node_modules/@craco/
   ls -la build/
   ```

---

## ✅ CHECKLISTE:

- [ ] Alte App Cache gelöscht
- [ ] Frontend `node_modules` gelöscht
- [ ] Frontend `build` gelöscht
- [ ] Electron `node_modules` gelöscht
- [ ] Electron `dist` gelöscht
- [ ] `yarn install` ausgeführt
- [ ] `yarn build` ausgeführt
- [ ] App gestartet
- [ ] Scalping in Settings sichtbar
- [ ] Ollama Model auf `llama3:latest` gesetzt
- [ ] AI Chat funktioniert

---

**VIEL ERFOLG!** 🚀

Wenn Du das hier befolgt hast und es IMMER NOCH nicht geht, ist es ein spezifisches Problem mit Deinem Setup und ich helfe Dir individuell!
