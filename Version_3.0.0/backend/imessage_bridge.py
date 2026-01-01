"""
📱 iMessage Command & Control Bridge - V3.0.0

Überwacht die macOS Messages-Datenbank für eingehende Befehle und 
führt entsprechende System-Aktionen aus.

WICHTIG: Erfordert "Full Disk Access" für den ausführenden Prozess auf macOS!

Funktionen:
1. Polling der chat.db für neue Nachrichten
2. Intent-Mapping für iOS 26 Kurzbefehl-Menü
3. NLP-Analyse via Ollama/Llama 3.2 für unbekannte Befehle
4. Automatische Antworten via AppleScript
"""

import os
import sqlite3
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import json
import subprocess

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Autorisierte Absender (Telefonnummern oder E-Mails)
AUTHORIZED_SENDERS = [
    "+4917677868993",
    "dj1dbr@yahoo.de"
]

# Pfad zur Messages-Datenbank (macOS Standard)
CHAT_DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")

# Polling-Intervall in Sekunden
POLL_INTERVAL = 5


# ═══════════════════════════════════════════════════════════════════════
# INTENT-MAPPING für iOS Kurzbefehl-Menü
# ═══════════════════════════════════════════════════════════════════════

INTENT_MAP = {
    # Deutsch
    "Status": "GET_STATUS",
    "Ampel": "GET_STATUS",
    "Balance": "GET_BALANCE",
    "Kontostand": "GET_BALANCE",
    "Gewinne sichern": "CLOSE_PROFIT",
    "offene Trades": "GET_TRADES",
    "Trades": "GET_TRADES",
    "Positionen": "GET_TRADES",
    "Stop": "STOP_TRADING",
    "Pause": "PAUSE_TRADING",
    "Start": "START_TRADING",
    "Weiter": "START_TRADING",
    "Hilfe": "HELP",
    "Help": "HELP",
    "Modus": "GET_MODE",
    "Konservativ": "SET_MODE_CONSERVATIVE",
    "Standard": "SET_MODE_NEUTRAL",
    "Aggressiv": "SET_MODE_AGGRESSIVE",
    # V3.0.0: Neustart-Befehl
    "Neustart": "RESTART_SYSTEM",
    "Restart": "RESTART_SYSTEM",
    "Reboot": "RESTART_SYSTEM",
    
    # English fallbacks
    "status": "GET_STATUS",
    "balance": "GET_BALANCE",
    "trades": "GET_TRADES",
    "stop": "STOP_TRADING",
    "start": "START_TRADING",
    "help": "HELP"
}


class iMessageBridge:
    """
    Hauptklasse für die iMessage-Integration.
    
    Überwacht die chat.db und routet Befehle an die entsprechenden Handler.
    """
    
    def __init__(self, 
                 action_handler: Optional[Callable] = None,
                 ollama_handler: Optional[Callable] = None):
        """
        Initialisiert die iMessage-Bridge.
        
        Args:
            action_handler: Callback-Funktion für erkannte Aktionen
            ollama_handler: Callback-Funktion für NLP-Analyse via Ollama
        """
        self.db_path = CHAT_DB_PATH
        self.authorized_senders = AUTHORIZED_SENDERS
        self.last_processed_timestamp = self._get_current_timestamp_ns()
        self.action_handler = action_handler
        self.ollama_handler = ollama_handler
        self.is_running = False
        self._poll_task = None
        
        # V3.0.0 FIX: Anti-Loop Protection
        self.processed_rowids = set()  # Speichert bereits verarbeitete Nachrichten-IDs
        self.last_response_time = 0  # Timestamp der letzten Antwort
        self.response_cooldown = 30  # V3.2.1: Erhöht auf 30 Sekunden Cooldown zwischen Antworten
        self.max_processed_ids = 1000  # Max gespeicherte IDs (Memory-Schutz)
        
        # V3.2.1: Konversations-Tracking um Loops zu verhindern
        self.conversation_history = {}  # sender -> [timestamps]
        self.max_messages_per_minute = 3  # Max 3 Nachrichten pro Minute pro Sender
        
        # Statistiken
        self.stats = {
            "messages_processed": 0,
            "commands_executed": 0,
            "nlp_queries": 0,
            "errors": 0,
            "loops_prevented": 0
        }
        
        logger.info(f"📱 iMessage Bridge V3.2.1 initialisiert")
        logger.info(f"   Datenbank: {self.db_path}")
        logger.info(f"   Autorisierte Absender: {self.authorized_senders}")
        logger.info(f"   Anti-Loop Cooldown: {self.response_cooldown}s")
        logger.info(f"   Max Nachrichten/Minute: {self.max_messages_per_minute}")
    
    def _get_current_timestamp_ns(self) -> int:
        """Gibt den aktuellen Zeitstempel in Nanosekunden zurück (macOS Format)."""
        # macOS Messages verwendet Nanosekunden seit 2001-01-01
        # Wir konvertieren von Unix-Zeit
        now = datetime.now(timezone.utc)
        # 978307200 = Sekunden zwischen 1970-01-01 und 2001-01-01
        cocoa_epoch = 978307200
        return int((now.timestamp() - cocoa_epoch) * 1_000_000_000)
    
    def check_database_access(self) -> Dict[str, Any]:
        """
        Prüft ob die Datenbank zugänglich ist.
        
        Returns:
            Dict mit Status und ggf. Fehlermeldung
        """
        result = {
            "accessible": False,
            "path": self.db_path,
            "error": None,
            "requires_full_disk_access": False
        }
        
        # Prüfe ob die Datei existiert
        if not os.path.exists(self.db_path):
            result["error"] = f"Datenbank nicht gefunden: {self.db_path}"
            result["requires_full_disk_access"] = True
            return result
        
        # Versuche zu öffnen
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM message")
            count = cursor.fetchone()[0]
            conn.close()
            
            result["accessible"] = True
            result["message_count"] = count
            logger.info(f"✅ chat.db zugänglich: {count} Nachrichten")
            
        except sqlite3.OperationalError as e:
            result["error"] = str(e)
            if "unable to open" in str(e).lower() or "permission" in str(e).lower():
                result["requires_full_disk_access"] = True
                result["error"] = (
                    "Full Disk Access erforderlich! "
                    "Gehe zu: Systemeinstellungen > Datenschutz & Sicherheit > "
                    "Voller Festplattenzugriff und füge Terminal/Python hinzu."
                )
        
        return result
    
    async def poll_messages(self) -> List[Dict]:
        """
        Fragt die Datenbank nach neuen Nachrichten von autorisierten Absendern ab.
        V3.2.1: Verbesserter Anti-Loop-Schutz
        
        Returns:
            Liste von neuen Nachrichten
        """
        new_messages = []
        
        try:
            # V3.2.1: Rate-Limit für Polling - max 1 Nachricht pro 10 Sekunden verarbeiten
            import time as time_module
            current_time = time_module.time()
            if hasattr(self, '_last_poll_time') and current_time - self._last_poll_time < 10:
                return []  # Zu früh, überspringe
            self._last_poll_time = current_time
            
            # Nur-Lese-Verbindung
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Query für neue Nachrichten von autorisierten Absendern
            # WICHTIG: is_from_me = 0 filtert eigene Nachrichten aus
            placeholders = ",".join(["?" for _ in self.authorized_senders])
            query = f"""
                SELECT 
                    message.text,
                    message.date,
                    handle.id AS sender,
                    message.ROWID,
                    message.is_from_me
                FROM message
                JOIN handle ON message.handle_id = handle.ROWID
                WHERE handle.id IN ({placeholders})
                AND message.is_from_me = 0
                AND message.date > ?
                AND message.text IS NOT NULL
                AND message.text != ''
                ORDER BY message.date ASC
                LIMIT 1
            """
            
            cursor.execute(query, (*self.authorized_senders, self.last_processed_timestamp))
            rows = cursor.fetchall()
            
            for row in rows:
                text, date, sender, rowid, is_from_me = row
                
                # V3.0.0 FIX: Skip bereits verarbeitete Nachrichten (Anti-Loop)
                if rowid in self.processed_rowids:
                    logger.debug(f"⏭️ Nachricht #{rowid} bereits verarbeitet, überspringe")
                    self.stats["loops_prevented"] += 1
                    continue
                
                # V3.2.1: Ignoriere Bot-ähnliche Antworten (Anti-Loop)
                text_clean = text.strip()
                if text_clean.startswith("✅") or text_clean.startswith("💰") or text_clean.startswith("📊") or text_clean.startswith("🤖"):
                    logger.info(f"⏭️ Bot-Antwort erkannt, überspringe: {text_clean[:30]}...")
                    self.processed_rowids.add(rowid)
                    self.stats["loops_prevented"] += 1
                    continue
                
                # V3.2.1: Ignoriere wenn Nachricht älter als 60 Sekunden
                from datetime import datetime, timezone
                # macOS Messages timestamp ist in Nanosekunden seit 2001-01-01
                msg_timestamp = datetime(2001, 1, 1, tzinfo=timezone.utc).timestamp() + (date / 1000000000)
                age_seconds = current_time - msg_timestamp
                if age_seconds > 60:
                    logger.info(f"⏭️ Alte Nachricht ({age_seconds:.0f}s), überspringe: {text_clean[:30]}...")
                    self.processed_rowids.add(rowid)
                    continue
                
                # Update letzten Timestamp
                if date > self.last_processed_timestamp:
                    self.last_processed_timestamp = date
                
                # Markiere als verarbeitet
                self.processed_rowids.add(rowid)
                
                # Memory-Schutz: Alte IDs löschen wenn zu viele
                if len(self.processed_rowids) > self.max_processed_ids:
                    # Behalte nur die letzten 500
                    self.processed_rowids = set(list(self.processed_rowids)[-500:])
                
                new_messages.append({
                    "text": text_clean,
                    "date": date,
                    "sender": sender,
                    "rowid": rowid,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                logger.info(f"📨 Neue Nachricht von {sender}: {text[:50]}...")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abfragen der chat.db: {e}")
            self.stats["errors"] += 1
        
        return new_messages
    
    def parse_intent(self, text: str) -> Dict[str, Any]:
        """
        Analysiert den Nachrichtentext und ermittelt die Intention.
        
        Args:
            text: Der Nachrichtentext
            
        Returns:
            Dict mit action, confidence, requires_nlp
        """
        text_clean = text.strip()
        text_lower = text_clean.lower()
        
        # Exakter Match
        if text_clean in INTENT_MAP:
            return {
                "action": INTENT_MAP[text_clean],
                "confidence": 1.0,
                "requires_nlp": False,
                "original_text": text_clean
            }
        
        # Case-insensitive Match
        for key, action in INTENT_MAP.items():
            if key.lower() == text_lower:
                return {
                    "action": action,
                    "confidence": 0.95,
                    "requires_nlp": False,
                    "original_text": text_clean
                }
        
        # Partial Match (enthält das Keyword)
        for key, action in INTENT_MAP.items():
            if key.lower() in text_lower:
                return {
                    "action": action,
                    "confidence": 0.7,
                    "requires_nlp": False,
                    "original_text": text_clean
                }
        
        # Kein Match - NLP erforderlich
        return {
            "action": "NLP_ANALYSIS",
            "confidence": 0.0,
            "requires_nlp": True,
            "original_text": text_clean
        }
    
    async def process_message(self, message: Dict) -> Dict[str, Any]:
        """
        Verarbeitet eine einzelne Nachricht.
        V3.0.0: Unterstützt natürliche Konversation via Ollama.
        
        Args:
            message: Die zu verarbeitende Nachricht
            
        Returns:
            Dict mit Ergebnis der Verarbeitung
        """
        text = message["text"]
        sender = message["sender"]
        
        logger.info(f"🔄 Verarbeite Nachricht von {sender}: {text}")
        
        # Parse Intent (schnelle Keyword-Erkennung)
        intent = self.parse_intent(text)
        action = intent["action"]
        
        result = {
            "message": message,
            "intent": intent,
            "success": False,
            "response": None,
            "error": None
        }
        
        try:
            # V3.0.0: Immer Ollama für intelligente Antworten nutzen (wenn verfügbar)
            if self.ollama_handler:
                logger.info(f"🤖 Sende an Ollama für intelligente Analyse: {text}")
                self.stats["nlp_queries"] += 1
                
                nlp_result = await self.ollama_handler(text)
                result["nlp_result"] = nlp_result
                
                if nlp_result:
                    # Prüfe ob es eine Aktion oder Konversation ist
                    nlp_action = nlp_result.get("action", "UNKNOWN")
                    nlp_response = nlp_result.get("response", "")
                    
                    if nlp_action == "CONVERSATION":
                        # Reine Konversation - Antwort direkt senden
                        logger.info(f"💬 Konversations-Antwort: {nlp_response[:50]}...")
                        result["response"] = nlp_response
                        result["success"] = True
                        await self.send_response(sender, nlp_response)
                        self.stats["messages_processed"] += 1
                        return result
                    elif nlp_action not in ["UNKNOWN", "NLP_ANALYSIS"]:
                        # Es ist eine erkannte Aktion
                        action = nlp_action
                        intent["action"] = action
                        intent["nlp_processed"] = True
                        intent["nlp_response"] = nlp_response
            
            # Führe Aktion aus (wenn keine reine Konversation)
            if self.action_handler and action not in ["NLP_ANALYSIS", "CONVERSATION", "UNKNOWN"]:
                logger.info(f"⚡ Führe Aktion aus: {action}")
                self.stats["commands_executed"] += 1
                
                action_result = await self.action_handler(action, message)
                result["action_result"] = action_result
                result["success"] = True
                
                # V3.0.0: Kombiniere NLP-Antwort mit Aktion-Ergebnis
                nlp_intro = intent.get("nlp_response", "")
                action_response = self._format_response(action, action_result)
                
                if nlp_intro and nlp_intro != action_response:
                    response_text = f"{nlp_intro}\n\n{action_response}"
                else:
                    response_text = action_response
                
                result["response"] = response_text
                await self.send_response(sender, response_text)
            
            elif action == "UNKNOWN":
                # Unbekannter Befehl - hilfreiche Antwort senden
                help_response = (
                    "🤔 Das habe ich nicht verstanden.\n\n"
                    "Verfügbare Befehle:\n"
                    "• Status - Systemstatus\n"
                    "• Balance - Kontostände\n"
                    "• Trades - Offene Positionen\n"
                    "• Start/Stop - Trading steuern\n"
                    "• Hilfe - Alle Befehle"
                )
                result["response"] = help_response
                await self.send_response(sender, help_response)
            
            self.stats["messages_processed"] += 1
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Nachrichtenverarbeitung: {e}")
            result["error"] = str(e)
            self.stats["errors"] += 1
        
        return result
    
    def _format_response(self, action: str, result: Any) -> str:
        """Formatiert die Antwort für eine Aktion."""
        if action == "GET_STATUS":
            return f"✅ System aktiv\n{result.get('summary', '')}"
        elif action == "GET_BALANCE":
            # V3.0.0: Zeige alle Broker mit Balances
            summary = result.get('summary', '')
            if summary:
                return f"💰 Kontostand:\n{summary}"
            else:
                total = result.get('total', 0)
                return f"💰 Balance: {total:,.2f}€"
        elif action == "GET_TRADES":
            count = result.get('count', 0)
            return f"📊 {count} offene Trades\n{result.get('summary', '')}"
        elif action == "HELP":
            return (
                "📱 Verfügbare Befehle:\n"
                "• Status/Ampel - Systemstatus\n"
                "• Balance - Kontostand\n"
                "• Trades - Offene Positionen\n"
                "• Start/Stop - Trading steuern\n"
                "• Modus - Aktuellen Modus zeigen"
            )
        else:
            return f"✅ Befehl '{action}' ausgeführt"
    
    async def send_response(self, recipient: str, message: str) -> bool:
        """
        Sendet eine Antwort via AppleScript (nur auf macOS).
        
        Args:
            recipient: Telefonnummer oder E-Mail des Empfängers
            message: Die zu sendende Nachricht
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        import time as time_module
        
        # V3.0.0 FIX: Cooldown-Prüfung um Loops zu verhindern
        current_time = time_module.time()
        if current_time - self.last_response_time < self.response_cooldown:
            remaining = self.response_cooldown - (current_time - self.last_response_time)
            logger.warning(f"⏳ Antwort-Cooldown aktiv, noch {remaining:.1f}s warten")
            return False
        
        # Escape für AppleScript
        message_escaped = message.replace('"', '\\"').replace('\n', '\\n')
        
        applescript = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{recipient}" of targetService
            send "{message_escaped}" to targetBuddy
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # V3.0.0 FIX: Update last_response_time nach erfolgreicher Antwort
                self.last_response_time = time_module.time()
                logger.info(f"✅ Antwort gesendet an {recipient}")
                return True
            else:
                logger.error(f"❌ AppleScript Fehler: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ AppleScript Timeout")
            return False
        except FileNotFoundError:
            logger.warning("⚠️ osascript nicht gefunden - läuft nicht auf macOS")
            return False
        except Exception as e:
            logger.error(f"❌ Fehler beim Senden: {e}")
            return False
    
    async def _poll_loop(self):
        """Interne Polling-Schleife."""
        logger.info(f"🔄 Polling-Schleife gestartet (Intervall: {POLL_INTERVAL}s)")
        
        while self.is_running:
            try:
                messages = await self.poll_messages()
                
                for msg in messages:
                    await self.process_message(msg)
                
                await asyncio.sleep(POLL_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Polling-Schleife abgebrochen")
                break
            except Exception as e:
                logger.error(f"❌ Fehler in Polling-Schleife: {e}")
                await asyncio.sleep(POLL_INTERVAL)
    
    async def start(self):
        """Startet die iMessage-Bridge."""
        if self.is_running:
            logger.warning("iMessage Bridge läuft bereits")
            return
        
        # Prüfe Datenbankzugriff
        access_check = self.check_database_access()
        if not access_check["accessible"]:
            logger.error(f"❌ {access_check['error']}")
            return
        
        self.is_running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("✅ iMessage Bridge gestartet")
    
    async def stop(self):
        """Stoppt die iMessage-Bridge."""
        self.is_running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ iMessage Bridge gestoppt")
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zurück."""
        return {
            **self.stats,
            "is_running": self.is_running,
            "authorized_senders": self.authorized_senders,
            "last_processed": self.last_processed_timestamp
        }


# ═══════════════════════════════════════════════════════════════════════
# AUTOMATISIERTE REPORTS (Scheduled)
# ═══════════════════════════════════════════════════════════════════════

class AutomatedReporter:
    """
    Sendet automatisierte Berichte zu festgelegten Zeiten.
    
    - 07:00 Uhr: Morgen-Heartbeat
    - 22:00 Uhr: Abend-Performance-Report
    - Live: Signal-Alerts bei Ampelwechsel
    """
    
    def __init__(self, bridge: iMessageBridge, get_system_data: Callable):
        """
        Args:
            bridge: Die iMessage-Bridge für das Senden
            get_system_data: Funktion zum Abrufen von Systemdaten
        """
        self.bridge = bridge
        self.get_system_data = get_system_data
        self.recipient = AUTHORIZED_SENDERS[0]  # Primärer Empfänger
        self.is_running = False
        self._scheduler_task = None
        
    async def send_morning_heartbeat(self):
        """Sendet den Morgen-Heartbeat um 07:00 Uhr."""
        try:
            data = await self.get_system_data()
            
            message = (
                f"☀️ Guten Morgen! System online.\n"
                f"📊 {data.get('active_assets', 20)} Assets aktiv\n"
                f"💰 Gesamt-Balance: {data.get('total_balance', '?')}€\n"
                f"🎯 Modus: {data.get('mode', 'Konservativ')}\n"
                f"🚀 Bereit für Trading!"
            )
            
            await self.bridge.send_response(self.recipient, message)
            logger.info("☀️ Morgen-Heartbeat gesendet")
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Morgen-Heartbeat: {e}")
    
    async def send_evening_report(self):
        """Sendet den Abend-Performance-Report um 22:00 Uhr."""
        try:
            data = await self.get_system_data()
            
            pnl = data.get('daily_pnl', 0)
            pnl_emoji = "📈" if pnl >= 0 else "📉"
            
            message = (
                f"🌙 Tages-Report\n"
                f"{pnl_emoji} P&L: {pnl:+.2f}€\n"
                f"📊 Trades heute: {data.get('trades_today', 0)}\n"
                f"✅ Gewinner: {data.get('winners', 0)}\n"
                f"❌ Verlierer: {data.get('losers', 0)}\n"
                f"💰 Balance: {data.get('total_balance', '?')}€"
            )
            
            await self.bridge.send_response(self.recipient, message)
            logger.info("🌙 Abend-Report gesendet")
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Abend-Report: {e}")
    
    async def send_signal_alert(self, asset: str, signal: str, score: float, pillar: str):
        """
        Sendet einen Live-Alert bei Signal-Änderung.
        
        Args:
            asset: Das Asset (z.B. "GOLD")
            signal: Das Signal (BUY/SELL)
            score: Der Confidence-Score
            pillar: Die stärkste Säule
        """
        emoji = "🟢" if signal == "BUY" else "🔴"
        
        message = (
            f"{emoji} Signal {asset}\n"
            f"📊 Score: {score:.0f}%\n"
            f"📐 Stärkste Säule: {pillar}\n"
            f"⏱️ Cooldown: 5 Min"
        )
        
        await self.bridge.send_response(self.recipient, message)
        logger.info(f"🚨 Signal-Alert gesendet: {asset} {signal}")


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════

_bridge_instance: Optional[iMessageBridge] = None
_reporter_instance: Optional[AutomatedReporter] = None


def get_imessage_bridge() -> Optional[iMessageBridge]:
    """Gibt die Singleton-Instanz der iMessage-Bridge zurück."""
    return _bridge_instance


def init_imessage_bridge(action_handler: Callable, ollama_handler: Callable = None) -> iMessageBridge:
    """
    Initialisiert die iMessage-Bridge.
    
    Args:
        action_handler: Handler für erkannte Aktionen
        ollama_handler: Optional - Handler für NLP via Ollama
        
    Returns:
        Die initialisierte Bridge-Instanz
    """
    global _bridge_instance
    _bridge_instance = iMessageBridge(action_handler, ollama_handler)
    return _bridge_instance


# Für Tests auf nicht-macOS Systemen
def is_macos() -> bool:
    """Prüft ob das System macOS ist."""
    import platform
    return platform.system() == "Darwin"


if __name__ == "__main__":
    # Test-Modus
    logging.basicConfig(level=logging.INFO)
    
    if not is_macos():
        print("⚠️ iMessage Bridge ist nur auf macOS verfügbar!")
        print("   Dieser Code wird für die Nutzung auf Ihrem Mac vorbereitet.")
    else:
        bridge = iMessageBridge()
        result = bridge.check_database_access()
        print(f"\nDatenbank-Status: {result}")
