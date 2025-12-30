"""
📱 Booner Trade V3.1.0 - iMessage Routes

Enthält alle iMessage-bezogenen API-Endpunkte:
- Command Processing
- Status
- Ollama Controller
- Neustart-Befehl
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
import subprocess
import sys
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

imessage_router = APIRouter(prefix="/imessage", tags=["iMessage Bridge"])


# ═══════════════════════════════════════════════════════════════════════
# V3.1.0: VERBESSERTER NEUSTART-MECHANISMUS
# ═══════════════════════════════════════════════════════════════════════

class SystemRestarter:
    """
    V3.1.0: Robuster System-Neustart-Handler für macOS.
    
    Dynamische Pfad-Erkennung und mehrere Neustart-Methoden.
    """
    
    @staticmethod
    def find_booner_app_path() -> Optional[str]:
        """Findet den Installationspfad der Booner Trade App."""
        possible_paths = [
            "/Applications/Booner Trade",
            os.path.expanduser("~/Applications/Booner Trade"),
            "/Applications/Booner-Trade",
            os.path.expanduser("~/Desktop/Booner Trade"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    @staticmethod
    def find_backend_path(app_path: str) -> Optional[str]:
        """Findet den Backend-Pfad innerhalb der App."""
        # Suche nach verschiedenen Version-Ordnern
        import glob
        
        patterns = [
            f"{app_path}/Booner-v.*/backend",
            f"{app_path}/backend",
            f"{app_path}/*/backend",
        ]
        
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                # Nehme den neuesten (höchste Versionsnummer)
                matches.sort(reverse=True)
                if os.path.exists(os.path.join(matches[0], "server.py")):
                    return matches[0]
        
        return None
    
    @staticmethod
    def create_restart_script(backend_path: str) -> str:
        """
        Erstellt ein Shell-Skript für den sicheren Neustart.
        V3.1.0: Verwendet separate Prozessgruppen für sauberen Neustart.
        """
        script = f'''#!/bin/bash
# Booner Trade V3.1.0 - System Neustart
# Generiert: {datetime.now().isoformat()}

echo "🔄 Booner Trade Neustart gestartet..."

# 1. Ollama neu starten (optional)
if pgrep -x "ollama" > /dev/null; then
    echo "  → Ollama wird neu gestartet..."
    pkill -x ollama
    sleep 2
    open -a Ollama 2>/dev/null || /usr/local/bin/ollama serve &
fi

# 2. Backend stoppen
echo "  → Backend wird gestoppt..."
pkill -f "python.*server.py" 2>/dev/null
sleep 2

# 3. Backend starten
echo "  → Backend wird gestartet..."
cd "{backend_path}"
nohup python3 server.py > logs/backend_restart.log 2>&1 &
BACKEND_PID=$!
echo "  → Backend PID: $BACKEND_PID"

# 4. Warte auf Backend-Start
sleep 3
if curl -s http://localhost:8001/api/health > /dev/null; then
    echo "✅ Backend läuft!"
else
    echo "⚠️ Backend noch nicht ready, warte..."
    sleep 5
fi

# 5. Booner Trade App öffnen (falls installiert)
if [ -d "/Applications/Booner Trade" ]; then
    echo "  → Booner Trade App wird geöffnet..."
    open -a "Booner Trade" 2>/dev/null
fi

echo "🎉 Neustart abgeschlossen!"
'''
        return script
    
    @classmethod
    async def execute_restart(cls) -> Dict[str, Any]:
        """
        V3.1.0: Führt den System-Neustart aus.
        
        Returns:
            Dict mit Neustart-Status und Details
        """
        result = {
            "success": False,
            "message": "",
            "platform": sys.platform,
            "app_path": None,
            "backend_path": None,
            "method": None
        }
        
        # Nur auf macOS
        if sys.platform != 'darwin':
            result["message"] = "Neustart nur auf macOS verfügbar"
            return result
        
        # Finde App-Pfad
        app_path = cls.find_booner_app_path()
        if not app_path:
            result["message"] = "Booner Trade App nicht gefunden"
            logger.warning(f"⚠️ RESTART: App-Pfad nicht gefunden")
            return result
        
        result["app_path"] = app_path
        
        # Finde Backend-Pfad
        backend_path = cls.find_backend_path(app_path)
        if not backend_path:
            # Fallback: Verwende aktuellen Pfad
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if os.path.exists(os.path.join(current_dir, "server.py")):
                backend_path = current_dir
            else:
                result["message"] = "Backend-Pfad nicht gefunden"
                return result
        
        result["backend_path"] = backend_path
        logger.info(f"🔄 RESTART: App={app_path}, Backend={backend_path}")
        
        # Methode 1: Direkter Shell-Befehl
        try:
            restart_script = cls.create_restart_script(backend_path)
            
            # Speichere Skript temporär
            script_path = "/tmp/booner_restart.sh"
            with open(script_path, 'w') as f:
                f.write(restart_script)
            os.chmod(script_path, 0o755)
            
            # Führe asynchron aus (damit die Response noch gesendet werden kann)
            subprocess.Popen(
                ["/bin/bash", script_path],
                start_new_session=True,  # Eigene Prozessgruppe
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            result["success"] = True
            result["method"] = "shell_script"
            result["message"] = "Neustart initiiert! System startet in wenigen Sekunden neu."
            logger.info("✅ RESTART: Shell-Skript ausgeführt")
            
        except Exception as e:
            logger.error(f"❌ RESTART Methode 1 fehlgeschlagen: {e}")
            
            # Methode 2: Einfacher pkill + open
            try:
                simple_cmd = f'''
                    pkill -f "python.*server.py";
                    sleep 2;
                    cd "{backend_path}" && nohup python3 server.py > /dev/null 2>&1 &
                    open -a "Booner Trade" 2>/dev/null
                '''
                subprocess.Popen(simple_cmd, shell=True, start_new_session=True)
                
                result["success"] = True
                result["method"] = "simple_restart"
                result["message"] = "Neustart mit Fallback-Methode initiiert."
                logger.info("✅ RESTART: Fallback-Methode ausgeführt")
                
            except Exception as e2:
                result["message"] = f"Neustart fehlgeschlagen: {e}, Fallback: {e2}"
                logger.error(f"❌ RESTART beide Methoden fehlgeschlagen: {e}, {e2}")
        
        return result


@imessage_router.get("/status")
async def get_imessage_status():
    """
    Liefert den Status der iMessage-Bridge.
    """
    try:
        from imessage_bridge import iMessageBridge
        
        bridge = iMessageBridge()
        db_check = bridge.check_database_access()
        
        return {
            "available": db_check.get("accessible", False),
            "database_path": db_check.get("path"),
            "requires_full_disk_access": db_check.get("requires_full_disk_access", True),
            "error": db_check.get("error"),
            "stats": bridge.stats,
            "authorized_senders": bridge.authorized_senders
        }
        
    except ImportError:
        return {
            "available": False,
            "error": "iMessage Bridge nicht installiert"
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


@imessage_router.post("/command")
async def process_imessage_command(text: str, sender: str = None):
    """
    Verarbeitet einen iMessage-Befehl (für Tests ohne echte iMessage).
    V3.2.0: VERBESSERTE Nachrichten-Erkennung mit Fuzzy-Matching.
    """
    from imessage_bridge import INTENT_MAP
    
    try:
        from ollama_controller import ACTION_KEYWORDS
    except ImportError:
        ACTION_KEYWORDS = {}
    
    text_clean = text.strip()
    text_lower = text_clean.lower()
    
    # V3.2.0: Erweiterte Keyword-Map für robustere Erkennung
    EXTENDED_KEYWORDS = {
        # Status-Varianten
        'status': 'GET_STATUS',
        'ampel': 'GET_STATUS',
        'wie gehts': 'GET_STATUS',
        'läufts': 'GET_STATUS',
        
        # Balance-Varianten
        'balance': 'GET_BALANCE',
        'kontostand': 'GET_BALANCE',
        'geld': 'GET_BALANCE',
        'kontostand': 'GET_BALANCE',
        'euro': 'GET_BALANCE',
        'wieviel': 'GET_BALANCE',
        
        # Trade-Varianten
        'trades': 'GET_TRADES',
        'positionen': 'GET_TRADES',
        'offen': 'GET_TRADES',
        
        # Neustart-Varianten (WICHTIG für den User!)
        'neustart': 'RESTART_SYSTEM',
        'restart': 'RESTART_SYSTEM',
        'reboot': 'RESTART_SYSTEM',
        'neustarten': 'RESTART_SYSTEM',
        'neu starten': 'RESTART_SYSTEM',
        
        # Start/Stop-Varianten
        'start': 'START_TRADING',
        'starten': 'START_TRADING',
        'weiter': 'START_TRADING',
        'stop': 'STOP_TRADING',
        'stopp': 'STOP_TRADING',
        'pause': 'PAUSE_TRADING',
        
        # Modus-Varianten
        'konservativ': 'SET_MODE_CONSERVATIVE',
        'standard': 'SET_MODE_NEUTRAL',
        'normal': 'SET_MODE_NEUTRAL',
        'aggressiv': 'SET_MODE_AGGRESSIVE',
        
        # Hilfe-Varianten
        'hilfe': 'HELP',
        'help': 'HELP',
        'befehle': 'HELP',
        '?': 'HELP',
    }
    
    result = {
        "type": None,
        "action": None,
        "response": None,
        "success": False,
        "debug": {
            "input": text_clean,
            "matched_intent": None
        }
    }
    
    direct_action = None
    
    # 1. Exakte Intent-Suche (case-insensitive)
    for intent, action in INTENT_MAP.items():
        if text_lower == intent.lower():
            direct_action = action
            result["debug"]["matched_intent"] = f"exact:{intent}"
            logger.info(f"📱 iMessage: Exakte Übereinstimmung '{intent}' → {action}")
            break
    
    # 2. V3.2.0: Erweiterte Keyword-Suche (enthält-Check)
    if not direct_action:
        for keyword, action in EXTENDED_KEYWORDS.items():
            if keyword in text_lower:
                direct_action = action
                result["debug"]["matched_intent"] = f"extended:{keyword}"
                logger.info(f"📱 iMessage: Keyword '{keyword}' in '{text_clean}' → {action}")
                break
    
    # 3. ACTION_KEYWORDS als Fallback
    if not direct_action:
        for keyword, action in ACTION_KEYWORDS.items():
            if keyword.lower() in text_lower:
                direct_action = action
                result["debug"]["matched_intent"] = f"keyword:{keyword}"
                logger.info(f"📱 iMessage: ACTION_KEYWORD '{keyword}' → {action}")
                break
    
    # 4. Aktion ausführen
    if direct_action:
        result["type"] = "action"
        result["action"] = direct_action
        logger.info(f"📱 iMessage: Führe Aktion aus: {direct_action}")
        
        # Handler für verschiedene Aktionen
        action_result = await _execute_imessage_action(direct_action, sender)
        result["response"] = action_result.get("summary", action_result.get("message", ""))
        result["success"] = action_result.get("success", False)
        
    else:
        # 5. Ollama für Konversation
        result["type"] = "conversation"
        result["action"] = None
        logger.info(f"📱 iMessage: Keine Aktion erkannt für '{text_clean}', leite an Ollama weiter")
        
        try:
            from ollama_controller import OllamaController
            controller = OllamaController()
            ollama_response = await controller.process_message(text_clean)
            result["response"] = ollama_response.get("response", "Ich verstehe deine Anfrage nicht.")
            result["success"] = True
        except Exception as e:
            result["response"] = f"Hallo! Wie kann ich dir helfen? (Ollama nicht verfügbar: {str(e)[:50]})"
            result["success"] = True
    
    return result


async def _execute_imessage_action(action: str, sender: str = None) -> Dict[str, Any]:
    """
    Führt eine erkannte iMessage-Aktion aus.
    V3.1.0: Verbesserter RESTART_SYSTEM Handler.
    """
    result = {
        "success": False,
        "summary": "",
        "message": ""
    }
    
    try:
        if action == "GET_STATUS":
            # Status abrufen
            try:
                # V3.2.0: Nutze database_v2 db_manager korrekt
                from database_v2 import db_manager
                settings = await db_manager.settings_db.get_settings()
                
                mode = settings.get('trading_mode', 'standard')
                enabled = len(settings.get('enabled_commodities', []))
                
                result["success"] = True
                result["summary"] = (
                    f"🤖 Booner Trade V3.2.0 Status\n"
                    f"• Modus: {mode}\n"
                    f"• Aktive Assets: {enabled}\n"
                    f"• System: Online"
                )
            except Exception as e:
                result["summary"] = f"Status nicht verfügbar: {e}"
        
        elif action == "GET_BALANCE":
            # Balance abrufen
            try:
                from multi_platform_connector import multi_platform
                
                balances = []
                for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                    try:
                        account = await multi_platform.get_account_info(platform_name)
                        if account:
                            name = platform_name.replace('MT5_', '').replace('_DEMO', '').replace('_REAL', '')
                            balance = account.get('balance', 0)
                            balances.append(f"• {name}: {balance:,.2f}€")
                    except:
                        pass
                
                if balances:
                    result["success"] = True
                    result["summary"] = "💰 Kontostand:\n" + "\n".join(balances)
                else:
                    result["summary"] = "Balance nicht verfügbar"
                    
            except Exception as e:
                result["summary"] = f"Balance-Fehler: {e}"
        
        elif action == "GET_TRADES":
            # Offene Trades
            try:
                from multi_platform_connector import multi_platform
                
                positions = []
                for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                    try:
                        pos = await multi_platform.get_open_positions(platform_name)
                        if pos:
                            positions.extend(pos)
                    except:
                        pass
                
                if positions:
                    result["success"] = True
                    result["summary"] = f"📊 {len(positions)} offene Position(en)"
                else:
                    result["success"] = True
                    result["summary"] = "📊 Keine offenen Positionen"
                    
            except Exception as e:
                result["summary"] = f"Trade-Fehler: {e}"
        
        elif action == "HELP":
            result["success"] = True
            result["summary"] = (
                "📱 Booner Trade Befehle:\n"
                "• Status - System-Status\n"
                "• Balance - Kontostand\n"
                "• Trades - Offene Positionen\n"
                "• Start - Trading starten\n"
                "• Stop - Trading pausieren\n"
                "• Konservativ/Standard/Aggressiv - Modus\n"
                "• Neustart - System neu starten\n"
                "• Hilfe - Diese Nachricht"
            )
        
        elif action == "RESTART_SYSTEM":
            # V3.1.0: Verbesserter Neustart
            result["success"] = True
            result["summary"] = "🔄 Neustart wird ausgeführt...\n\nDas System startet in wenigen Sekunden neu. Du erhältst eine Bestätigung wenn alles läuft."
            
            # Asynchron Neustart ausführen
            restart_result = await SystemRestarter.execute_restart()
            
            if restart_result["success"]:
                logger.info(f"✅ RESTART erfolgreich initiiert: {restart_result['method']}")
            else:
                logger.warning(f"⚠️ RESTART Problem: {restart_result['message']}")
                result["summary"] += f"\n\n⚠️ Hinweis: {restart_result['message']}"
        
        elif action == "START_TRADING":
            result["success"] = True
            result["summary"] = "▶️ Trading wird gestartet..."
            # TODO: Bot starten
        
        elif action == "STOP_TRADING":
            result["success"] = True
            result["summary"] = "⏸️ Trading wird pausiert..."
            # TODO: Bot stoppen
        
        elif action in ["SET_MODE_CONSERVATIVE", "SET_MODE_NEUTRAL", "SET_MODE_AGGRESSIVE"]:
            mode_map = {
                "SET_MODE_CONSERVATIVE": "conservative",
                "SET_MODE_NEUTRAL": "standard",
                "SET_MODE_AGGRESSIVE": "aggressive"
            }
            mode = mode_map.get(action, "standard")
            
            try:
                # V3.2.0: Nutze database_v2 db_manager korrekt
                from database_v2 import db_manager
                await db_manager.settings_db.update_settings({"trading_mode": mode})
                
                result["success"] = True
                result["summary"] = f"✅ Modus auf '{mode}' geändert"
            except Exception as e:
                result["summary"] = f"Modus-Fehler: {e}"
        
        else:
            result["message"] = f"Aktion '{action}' nicht implementiert"
    
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"❌ iMessage-Aktion {action} fehlgeschlagen: {e}")
    
    return result


@imessage_router.post("/restart")
async def trigger_restart():
    """
    V3.1.0: Direkter Neustart-Endpoint.
    """
    result = await SystemRestarter.execute_restart()
    return result


@imessage_router.get("/restart/status")
async def get_restart_status():
    """
    Prüft ob ein Neustart möglich ist und zeigt Pfade.
    """
    app_path = SystemRestarter.find_booner_app_path()
    backend_path = SystemRestarter.find_backend_path(app_path) if app_path else None
    
    return {
        "platform": sys.platform,
        "can_restart": sys.platform == 'darwin' and backend_path is not None,
        "app_path": app_path,
        "backend_path": backend_path,
        "current_path": os.path.dirname(os.path.abspath(__file__))
    }


# Export router
__all__ = ['imessage_router', 'SystemRestarter']
