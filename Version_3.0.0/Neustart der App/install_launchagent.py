#!/usr/bin/env python3
"""
🔧 Installiert den Auto-Restart als macOS LaunchAgent

Dadurch wird das Auto-Restart Programm automatisch gestartet,
wenn Booner Trade gestartet wird.

Verwendung:
    python3 install_launchagent.py
"""

import os
import sys
import subprocess

# LaunchAgent Name
AGENT_NAME = "com.boonertrade.autorestart"

# Pfade
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(LAUNCH_AGENTS_DIR, f"{AGENT_NAME}.plist")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTO_RESTART_SCRIPT = os.path.join(SCRIPT_DIR, "auto_restart.py")
LOG_FILE = os.path.join(SCRIPT_DIR, "auto_restart.log")

# LaunchAgent Konfiguration
PLIST_CONTENT = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{AGENT_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{AUTO_RESTART_SCRIPT}</string>
    </array>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>WatchPaths</key>
    <array>
        <string>/Applications/Booner Trade.app</string>
    </array>
    
    <key>StandardOutPath</key>
    <string>{LOG_FILE}</string>
    
    <key>StandardErrorPath</key>
    <string>{LOG_FILE}</string>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
"""

def install():
    print("🔧 Booner Trade Auto-Restart LaunchAgent Installer")
    print("="*50)
    
    # Prüfe ob LaunchAgents Ordner existiert
    if not os.path.exists(LAUNCH_AGENTS_DIR):
        print(f"📁 Erstelle Ordner: {LAUNCH_AGENTS_DIR}")
        os.makedirs(LAUNCH_AGENTS_DIR)
    
    # Prüfe ob bereits installiert
    if os.path.exists(PLIST_PATH):
        print(f"⚠️  LaunchAgent existiert bereits: {PLIST_PATH}")
        response = input("   Überschreiben? (j/n): ").lower()
        if response != 'j':
            print("   Abgebrochen.")
            return
        
        # Entlade alten Agent
        print("   Entlade alten Agent...")
        subprocess.run(['launchctl', 'unload', PLIST_PATH], capture_output=True)
    
    # Schreibe plist Datei
    print(f"📝 Schreibe LaunchAgent: {PLIST_PATH}")
    with open(PLIST_PATH, 'w') as f:
        f.write(PLIST_CONTENT)
    
    # Setze Berechtigungen
    os.chmod(PLIST_PATH, 0o644)
    os.chmod(AUTO_RESTART_SCRIPT, 0o755)
    
    # Lade Agent
    print("🚀 Lade LaunchAgent...")
    result = subprocess.run(['launchctl', 'load', PLIST_PATH], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅ Installation erfolgreich!")
        print("\n📋 Der Auto-Restart Service wird jetzt automatisch gestartet,")
        print("   wenn Booner Trade geöffnet wird.")
        print(f"\n📄 Log-Datei: {LOG_FILE}")
    else:
        print(f"\n❌ Fehler beim Laden: {result.stderr}")
    
    print("\n" + "="*50)
    print("Befehle zur Verwaltung:")
    print(f"  Status prüfen:  launchctl list | grep {AGENT_NAME}")
    print(f"  Manuell starten: launchctl start {AGENT_NAME}")
    print(f"  Stoppen:         launchctl stop {AGENT_NAME}")
    print(f"  Deinstallieren:  launchctl unload {PLIST_PATH}")


def uninstall():
    print("🗑️  Deinstalliere LaunchAgent...")
    
    if os.path.exists(PLIST_PATH):
        subprocess.run(['launchctl', 'unload', PLIST_PATH], capture_output=True)
        os.remove(PLIST_PATH)
        print("✅ LaunchAgent entfernt.")
    else:
        print("⚠️  LaunchAgent war nicht installiert.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()
