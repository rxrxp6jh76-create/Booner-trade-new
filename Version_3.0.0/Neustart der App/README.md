# 🔄 Booner Trade Auto-Restart

Dieses Programm startet Booner Trade automatisch alle **1 Stunde** neu.

## 📋 Was macht das Programm?

1. Wartet 1 Stunde nach dem Start
2. Beendet Booner Trade
3. Führt "Kill Old Backend" aus
4. Wartet 7 Sekunden
5. Führt "Kill All Backend" aus  
6. Wartet 7 Sekunden
7. Startet Booner Trade neu
8. Wiederholt den Zyklus

## 🚀 Installation

### Option 1: Automatischer Start (empfohlen)

Führen Sie diesen Befehl im Terminal aus:

```bash
cd "Neustart der App"
python3 install_launchagent.py
```

Danach wird der Auto-Restart automatisch gestartet, wenn Sie Booner Trade öffnen.

### Option 2: Manueller Start

Doppelklicken Sie auf `start_auto_restart.command` oder führen Sie im Terminal aus:

```bash
python3 auto_restart.py
```

## ⚙️ Konfiguration

Öffnen Sie `auto_restart.py` und ändern Sie diese Werte:

```python
RESTART_INTERVAL_HOURS = 1  # Intervall in Stunden
KILL_WAIT_SECONDS = 7       # Wartezeit zwischen Kill-Befehlen
```

## 📁 Dateien

| Datei | Beschreibung |
|-------|-------------|
| `auto_restart.py` | Hauptprogramm |
| `start_auto_restart.command` | Doppelklick zum manuellen Starten |
| `install_launchagent.py` | Installiert automatischen Start |
| `auto_restart.log` | Log-Datei (wird erstellt) |

## 🔧 LaunchAgent Befehle

```bash
# Status prüfen
launchctl list | grep boonertrade

# Manuell starten
launchctl start com.boonertrade.autorestart

# Stoppen
launchctl stop com.boonertrade.autorestart

# Deinstallieren
python3 install_launchagent.py --uninstall
```

## 📋 Pfad-Anpassung

Falls Ihre Kill-Scripts an einem anderen Ort liegen, passen Sie diese Pfade in `auto_restart.py` an:

```python
KILL_OLD_BACKEND_SCRIPT = '~/Documents/BoonerTrade/Kill Old backend.command'
KILL_ALL_BACKEND_SCRIPT = '~/Documents/BoonerTrade/Kill all Backend.command'
```

## ❓ Fehlerbehebung

**Problem: Scripts werden nicht gefunden**
- Prüfen Sie die Pfade in `auto_restart.py`
- Das Programm hat Fallback-Methoden eingebaut

**Problem: Booner Trade startet nicht**
- Prüfen Sie ob `/Applications/Booner Trade.app` existiert
- Alternativ: App manuell in Anwendungen suchen

**Logs prüfen:**
```bash
cat "Neustart der App/auto_restart.log"
```
