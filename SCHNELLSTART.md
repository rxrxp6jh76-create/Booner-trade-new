# ⚡ SCHNELLSTART - Mac Development

## 🚀 Einfachster Weg (Empfohlen!)

### **Option 1: Mit Start-Script (Einfach!)**

```bash
cd BOONER-V2.3.26-MAC-FIX
./START-APP-MAC.sh
```

Das Script:
1. ✅ Startet Backend (Port 8000)
2. ✅ Startet Frontend (Port 3000)
3. ✅ Öffnet Browser automatisch
4. ✅ Zeigt alle Status-Infos

**Zum Beenden:** STRG+C drücken

---

### **Option 2: Electron Desktop App (Komplex)**

Nur wenn Du die standalone .app brauchst:

```bash
cd BOONER-V2.3.26-MAC-FIX

# Clean Build (siehe WICHTIG-LESEN.md)
cd frontend
rm -rf node_modules build
yarn install
yarn build

cd ../electron-app
rm -rf node_modules dist
yarn install
yarn build

# App öffnen
open dist/mac/Booner-Trade.app
```

⚠️ **Problem:** Electron App hat komplexe Python-Umgebung Requirements!

---

## 🎯 **Was Du jetzt tun solltest:**

### **Für Entwicklung/Testen:**
→ **Benutze START-APP-MAC.sh** (Option 1)
- Viel einfacher
- Schnellerer Reload
- Besseres Debugging
- Keine Build-Probleme

### **Für Produktion/Verteilung:**
→ Benutze Electron Build (Option 2)
- Standalone .app
- Keine Terminal nötig
- Aber: Komplizierteres Setup

---

## ✅ **Nach Start mit START-APP-MAC.sh:**

**Im Browser (automatisch öffnet):**
- http://localhost:3000

**Teste jetzt:**
1. ✅ Einstellungen öffnen
2. ✅ Zu "Trading Strategien" scrollen
3. ✅ **Scalping** sollte da sein!
4. ✅ Ollama einstellen:
   - Base URL: `http://127.0.0.1:11434`
   - Model: `llama3:latest`

---

## 🔧 **Troubleshooting:**

### Backend startet nicht:
```bash
cd backend
source venv/bin/activate
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
# Schaue auf Errors
```

### Frontend startet nicht:
```bash
cd frontend
rm -rf node_modules
yarn install
yarn start
```

### Port bereits belegt:
```bash
# Finde & stoppe alte Prozesse
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

---

## 📊 **Status Prüfen:**

```bash
# Backend
curl http://127.0.0.1:8000/api/ping

# Frontend
curl http://localhost:3000

# Ollama
curl http://127.0.0.1:11434/api/tags
```

---

## 💡 **Warum START-APP-MAC.sh?**

**Vorteile:**
✅ Kein komplizierter Build
✅ Sofortiger Start
✅ Hot Reload (Änderungen sofort sichtbar)
✅ Einfaches Debugging
✅ Backend + Frontend Logs sichtbar

**Nachteile:**
❌ Terminal muss offen bleiben
❌ Nicht als .app verpackt

**Für Deine Zwecke (Development/Testing):**
→ **START-APP-MAC.sh ist PERFEKT!**

---

## 🎉 **Next Steps:**

1. **Starte App:** `./START-APP-MAC.sh`
2. **Teste Scalping:** In Settings aktivieren
3. **Teste Ollama:** AI Chat nutzen
4. **Teste Trading:** Bitcoin Trade öffnen/schließen
5. **Sende Feedback:** Was funktioniert, was nicht?

---

**VIEL ERFOLG!** 🚀

Falls START-APP-MAC.sh nicht funktioniert, schick mir die Fehlermeldung!
