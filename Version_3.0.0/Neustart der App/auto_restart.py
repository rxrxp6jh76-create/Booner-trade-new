#!/usr/bin/env python3
"""
🔄 Booner Trade Auto-Restart Programm
Version 1.0.0

Dieses Programm:
1. Wartet 1 Stunde nach dem Start
2. Beendet Booner Trade
3. Führt Kill Old Backend aus
4. Wartet 7 Sekunden
5. Führt Kill All Backend aus
6. Wartet 7 Sekunden
7. Startet Booner Trade neu
8. Wiederholt den Zyklus

Verwendung:
- Wird automatisch beim Start von Booner Trade gestartet
- Kann auch manuell gestartet werden: python3 auto_restart.py
"""

import subprocess
import time
import os
import sys
import logging
from datetime import datetime, timedelta
import signal

# Konfiguration
RESTART_INTERVAL_HOURS = 1  # Intervall in Stunden
KILL_WAIT_SECONDS = 7       # Wartezeit zwischen Kill-Befehlen
STARTUP_DELAY_SECONDS = 10  # Wartezeit nach App-Start bevor Zyklus beginnt

# Logging einrichten
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'auto_restart.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AutoRestart')

# Pfade (anpassen an Ihre Mac-Installation)
BOONER_TRADE_APP = '/Applications/Booner Trade.app'
KILL_OLD_BACKEND_SCRIPT = os.path.expanduser('~/Documents/BoonerTrade/Kill Old backend.command')
KILL_ALL_BACKEND_SCRIPT = os.path.expanduser('~/Documents/BoonerTrade/Kill all Backend.command')

# Alternative Pfade falls die obigen nicht existieren
ALT_KILL_OLD_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Kill Old backend.command')
ALT_KILL_ALL_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Kill all Backend.command')


def find_script(primary_path, alt_path, script_name):
    """Findet das richtige Script."""
    if os.path.exists(primary_path):
        return primary_path
    elif os.path.exists(alt_path):
        return alt_path
    else:
        logger.warning(f"{script_name} nicht gefunden. Versuche alternatives Verfahren.")
        return None


def run_command(command, description):
    """Führt einen Befehl aus und loggt das Ergebnis."""
    try:
        logger.info(f"Starte: {description}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            logger.info(f"✅ {description} erfolgreich")
        else:
            logger.warning(f"⚠️ {description} beendet mit Code {result.returncode}")
            if result.stderr:
                logger.warning(f"   Fehler: {result.stderr[:200]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {description} Timeout nach 60 Sekunden")
        return False
    except Exception as e:
        logger.error(f"❌ {description} Fehler: {e}")
        return False


def kill_booner_trade():
    """Beendet die Booner Trade App."""
    logger.info("🛑 Beende Booner Trade...")
    
    # Methode 1: AppleScript (sanft)
    run_command(
        'osascript -e \'tell application "Booner Trade" to quit\'',
        "Booner Trade beenden (AppleScript)"
    )
    time.sleep(2)
    
    # Methode 2: pkill (falls noch läuft)
    run_command('pkill -f "Booner Trade"', "Booner Trade Prozesse beenden")
    
    # Methode 3: killall (Backup)
    run_command('killall "Booner Trade" 2>/dev/null || true', "killall Booner Trade")


def kill_old_backend():
    """Führt Kill Old Backend aus."""
    logger.info("🔪 Führe Kill Old Backend aus...")
    
    script_path = find_script(KILL_OLD_BACKEND_SCRIPT, ALT_KILL_OLD_BACKEND, "Kill Old Backend")
    
    if script_path and os.path.exists(script_path):
        run_command(f'bash "{script_path}"', "Kill Old Backend Script")
    else:
        # Fallback: Direktes Beenden der Backend-Prozesse
        logger.info("Verwende Fallback-Methode für Kill Old Backend")
        run_command('pkill -f "uvicorn.*server:app" 2>/dev/null || true', "Uvicorn Prozesse beenden")
        run_command('pkill -f "python.*server.py" 2>/dev/null || true', "Python Server Prozesse beenden")


def kill_all_backend():
    """Führt Kill All Backend aus."""
    logger.info("💀 Führe Kill All Backend aus...")
    
    script_path = find_script(KILL_ALL_BACKEND_SCRIPT, ALT_KILL_ALL_BACKEND, "Kill All Backend")
    
    if script_path and os.path.exists(script_path):
        run_command(f'bash "{script_path}"', "Kill All Backend Script")
    else:
        # Fallback: Alle Backend-Prozesse beenden
        logger.info("Verwende Fallback-Methode für Kill All Backend")
        run_command('pkill -9 -f "uvicorn" 2>/dev/null || true', "Alle Uvicorn beenden")
        run_command('pkill -9 -f "python.*backend" 2>/dev/null || true', "Alle Python Backend beenden")
        run_command('pkill -9 -f "node.*server" 2>/dev/null || true', "Alle Node Server beenden")


def start_booner_trade():
    """Startet die Booner Trade App."""
    logger.info("🚀 Starte Booner Trade...")
    
    if os.path.exists(BOONER_TRADE_APP):
        run_command(f'open "{BOONER_TRADE_APP}"', "Booner Trade starten")
    else:
        # Alternative: Versuche über Spotlight
        run_command(
            'osascript -e \'tell application "Booner Trade" to activate\'',
            "Booner Trade aktivieren (AppleScript)"
        )
    
    logger.info("✅ Booner Trade gestartet")


def perform_restart_cycle():
    """Führt einen kompletten Neustart-Zyklus durch."""
    logger.info("="*50)
    logger.info("🔄 STARTE NEUSTART-ZYKLUS")
    logger.info("="*50)
    
    # Schritt 1: Booner Trade beenden
    kill_booner_trade()
    time.sleep(3)
    
    # Schritt 2: Kill Old Backend
    kill_old_backend()
    logger.info(f"⏳ Warte {KILL_WAIT_SECONDS} Sekunden...")
    time.sleep(KILL_WAIT_SECONDS)
    
    # Schritt 3: Kill All Backend
    kill_all_backend()
    logger.info(f"⏳ Warte {KILL_WAIT_SECONDS} Sekunden...")
    time.sleep(KILL_WAIT_SECONDS)
    
    # Schritt 4: Booner Trade neu starten
    start_booner_trade()
    
    logger.info("="*50)
    logger.info("✅ NEUSTART-ZYKLUS ABGESCHLOSSEN")
    logger.info("="*50)


def main():
    """Hauptprogramm."""
    logger.info("🤖 Booner Trade Auto-Restart Programm gestartet")
    logger.info(f"   Neustart-Intervall: {RESTART_INTERVAL_HOURS} Stunde(n)")
    logger.info(f"   Kill-Wartezeit: {KILL_WAIT_SECONDS} Sekunden")
    logger.info(f"   Log-Datei: {log_file}")
    
    # Signal-Handler für sauberes Beenden
    def signal_handler(signum, frame):
        logger.info("\n🛑 Auto-Restart Programm wird beendet...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initiale Wartezeit (falls direkt nach App-Start gestartet)
    logger.info(f"⏳ Warte {STARTUP_DELAY_SECONDS} Sekunden vor erstem Zyklus...")
    time.sleep(STARTUP_DELAY_SECONDS)
    
    cycle_count = 0
    
    while True:
        try:
            # Berechne nächsten Neustart-Zeitpunkt
            next_restart = datetime.now() + timedelta(hours=RESTART_INTERVAL_HOURS)
            logger.info(f"⏰ Nächster Neustart um: {next_restart.strftime('%H:%M:%S')}")
            
            # Warte bis zum nächsten Neustart
            wait_seconds = RESTART_INTERVAL_HOURS * 3600
            time.sleep(wait_seconds)
            
            # Führe Neustart durch
            cycle_count += 1
            logger.info(f"\n🔄 Neustart-Zyklus #{cycle_count}")
            perform_restart_cycle()
            
            # Kurze Pause nach Neustart
            logger.info(f"⏳ Warte {STARTUP_DELAY_SECONDS} Sekunden nach Neustart...")
            time.sleep(STARTUP_DELAY_SECONDS)
            
        except Exception as e:
            logger.error(f"❌ Fehler im Hauptloop: {e}")
            time.sleep(60)  # Bei Fehler 1 Minute warten


if __name__ == "__main__":
    main()
