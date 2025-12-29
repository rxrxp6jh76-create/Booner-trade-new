"""
📊 Automatisiertes Reporting System - V3.0.0

Sendet automatisierte Berichte zu festgelegten Zeiten via AppleScript/iMessage:
- 07:00 Uhr: Morgen-Heartbeat
- 22:00 Uhr: Tages-Performance-Report
- Live: Signal-Alerts bei Ampelwechsel (GRÜN)

WICHTIG: Läuft nur auf macOS mit iMessage-Zugang!
"""

import os
import asyncio
import logging
import subprocess
from datetime import datetime, timezone, time as dt_time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Standard-Empfänger (kann überschrieben werden)
DEFAULT_RECIPIENT = "+4917677868993"

# Report-Zeiten (Stunde, Minute)
MORNING_HEARTBEAT_TIME = (7, 0)   # 07:00 Uhr
EVENING_REPORT_TIME = (22, 0)     # 22:00 Uhr

# Cooldown für Signal-Alerts in Sekunden (verhindert Spam)
SIGNAL_ALERT_COOLDOWN = 300  # 5 Minuten


@dataclass
class SignalState:
    """Speichert den letzten Signalzustand für jedes Asset."""
    last_signal: str = "HOLD"
    last_confidence: float = 0.0
    last_alert_time: Optional[datetime] = None
    alert_count: int = 0


class AppleScriptMessenger:
    """
    Sendet Nachrichten via AppleScript (osascript) an iMessage.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Prüft ob osascript verfügbar ist (nur macOS)."""
        try:
            result = subprocess.run(
                ["which", "osascript"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    async def send_message(recipient: str, message: str) -> bool:
        """
        Sendet eine Nachricht via iMessage/AppleScript.
        
        Args:
            recipient: Telefonnummer oder E-Mail des Empfängers
            message: Die zu sendende Nachricht
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        # Escape für AppleScript
        message_escaped = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        
        applescript = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{recipient}" of targetService
            send "{message_escaped}" to targetBuddy
        end tell
        '''
        
        try:
            # Führe asynchron aus
            process = await asyncio.create_subprocess_exec(
                "osascript", "-e", applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
            
            if process.returncode == 0:
                logger.info(f"✅ iMessage gesendet an {recipient}")
                return True
            else:
                logger.error(f"❌ AppleScript Fehler: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("❌ AppleScript Timeout")
            return False
        except FileNotFoundError:
            logger.warning("⚠️ osascript nicht gefunden - läuft nicht auf macOS")
            return False
        except Exception as e:
            logger.error(f"❌ Fehler beim Senden: {e}")
            return False


class AutomatedReportingSystem:
    """
    Hauptklasse für das automatisierte Reporting-System.
    """
    
    def __init__(
        self,
        data_provider: Callable,
        recipient: str = DEFAULT_RECIPIENT
    ):
        """
        Args:
            data_provider: Async-Funktion die System-Daten liefert
            recipient: Telefonnummer/E-Mail des Empfängers
        """
        self.data_provider = data_provider
        self.recipient = recipient
        self.messenger = AppleScriptMessenger()
        
        self.is_running = False
        self._scheduler_task = None
        self._signal_monitor_task = None
        
        # Signal-Tracking für Alert-Cooldown
        self.signal_states: Dict[str, SignalState] = {}
        
        # Statistiken
        self.stats = {
            "heartbeats_sent": 0,
            "evening_reports_sent": 0,
            "signal_alerts_sent": 0,
            "errors": 0,
            "last_heartbeat": None,
            "last_evening_report": None,
            "last_signal_alert": None
        }
        
        logger.info(f"📊 Automated Reporting System initialisiert")
        logger.info(f"   Empfänger: {self.recipient}")
        logger.info(f"   Heartbeat: {MORNING_HEARTBEAT_TIME[0]:02d}:{MORNING_HEARTBEAT_TIME[1]:02d}")
        logger.info(f"   Tagesreport: {EVENING_REPORT_TIME[0]:02d}:{EVENING_REPORT_TIME[1]:02d}")
    
    # ═══════════════════════════════════════════════════════════════════
    # REPORT-GENERATOREN
    # ═══════════════════════════════════════════════════════════════════
    
    async def generate_morning_heartbeat(self) -> str:
        """
        Generiert den Morgen-Heartbeat (07:00 Uhr).
        
        Format:
        "☀️ Guten Morgen! System online.
        📊 20 Assets aktiv
        💰 Gesamt-Balance: 88,933.81€
        🎯 Modus: Konservativ
        🚀 Bereit für Trading!"
        """
        try:
            data = await self.data_provider()
            
            total_balance = data.get('total_balance', 0)
            active_assets = data.get('active_assets', 20)
            mode = data.get('mode', 'Konservativ')
            
            # Modus-Emoji
            mode_emoji = {
                'conservative': '🛡️ Konservativ',
                'neutral': '⚖️ Standard',
                'aggressive': '🔥 Aggressiv'
            }.get(mode.lower(), f'🎯 {mode}')
            
            message = (
                f"☀️ Guten Morgen! System online.\n"
                f"📊 {active_assets} Assets aktiv\n"
                f"💰 Gesamt-Balance: {total_balance:,.2f}€\n"
                f"{mode_emoji}\n"
                f"🚀 Bereit für Trading!"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Generieren des Heartbeats: {e}")
            return f"☀️ Guten Morgen! System online.\n⚠️ Details nicht verfügbar: {e}"
    
    async def generate_evening_report(self) -> str:
        """
        Generiert den Abend-Performance-Report (22:00 Uhr).
        
        Format:
        "🌙 Tages-Report
        📈 P&L: +123.45€
        📊 Trades heute: 5
        ✅ Gewinner: 3
        ❌ Verlierer: 2
        💰 Balance: 88,933.81€"
        """
        try:
            data = await self.data_provider()
            
            daily_pnl = data.get('daily_pnl', 0)
            trades_today = data.get('trades_today', 0)
            winners = data.get('winners', 0)
            losers = data.get('losers', 0)
            total_balance = data.get('total_balance', 0)
            
            # P&L Emoji
            pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
            
            message = (
                f"🌙 Tages-Report\n"
                f"{pnl_emoji} P&L: {daily_pnl:+,.2f}€\n"
                f"📊 Trades heute: {trades_today}\n"
                f"✅ Gewinner: {winners}\n"
                f"❌ Verlierer: {losers}\n"
                f"💰 Balance: {total_balance:,.2f}€"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Generieren des Abendreports: {e}")
            return f"🌙 Tages-Report\n⚠️ Details nicht verfügbar: {e}"
    
    def generate_signal_alert(
        self,
        asset: str,
        signal: str,
        confidence: float,
        strongest_pillar: str
    ) -> str:
        """
        Generiert einen Live-Signal-Alert bei Ampelwechsel auf GRÜN.
        
        Format:
        "🟢 Signal GOLD
        📊 Score: 78%
        📐 Stärkste Säule: Trend-Konfluenz
        ⏱️ Cooldown: 5 Min"
        """
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
        
        message = (
            f"{emoji} Signal {asset}\n"
            f"📊 Score: {confidence:.0f}%\n"
            f"📐 Stärkste Säule: {strongest_pillar}\n"
            f"⏱️ Cooldown: 5 Min"
        )
        
        return message
    
    # ═══════════════════════════════════════════════════════════════════
    # SEND-METHODEN
    # ═══════════════════════════════════════════════════════════════════
    
    async def send_morning_heartbeat(self) -> bool:
        """Sendet den Morgen-Heartbeat."""
        message = await self.generate_morning_heartbeat()
        success = await self.messenger.send_message(self.recipient, message)
        
        if success:
            self.stats["heartbeats_sent"] += 1
            self.stats["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
            logger.info("☀️ Morgen-Heartbeat gesendet")
        else:
            self.stats["errors"] += 1
            
        return success
    
    async def send_evening_report(self) -> bool:
        """Sendet den Abend-Performance-Report."""
        message = await self.generate_evening_report()
        success = await self.messenger.send_message(self.recipient, message)
        
        if success:
            self.stats["evening_reports_sent"] += 1
            self.stats["last_evening_report"] = datetime.now(timezone.utc).isoformat()
            logger.info("🌙 Abend-Report gesendet")
        else:
            self.stats["errors"] += 1
            
        return success
    
    async def send_signal_alert(
        self,
        asset: str,
        signal: str,
        confidence: float,
        strongest_pillar: str = "Unbekannt"
    ) -> bool:
        """
        Sendet einen Signal-Alert mit Cooldown-Prüfung.
        
        Returns:
            True wenn gesendet, False wenn im Cooldown oder Fehler
        """
        now = datetime.now(timezone.utc)
        
        # Hole oder erstelle Signal-State
        if asset not in self.signal_states:
            self.signal_states[asset] = SignalState()
        
        state = self.signal_states[asset]
        
        # Prüfe Cooldown
        if state.last_alert_time:
            elapsed = (now - state.last_alert_time).total_seconds()
            if elapsed < SIGNAL_ALERT_COOLDOWN:
                logger.debug(f"⏱️ Signal-Alert für {asset} im Cooldown ({elapsed:.0f}s)")
                return False
        
        # Prüfe ob sich das Signal geändert hat
        if state.last_signal == signal and abs(state.last_confidence - confidence) < 5:
            logger.debug(f"⏸️ Signal für {asset} unverändert")
            return False
        
        # Generiere und sende Alert
        message = self.generate_signal_alert(asset, signal, confidence, strongest_pillar)
        success = await self.messenger.send_message(self.recipient, message)
        
        if success:
            # Update State
            state.last_signal = signal
            state.last_confidence = confidence
            state.last_alert_time = now
            state.alert_count += 1
            
            self.stats["signal_alerts_sent"] += 1
            self.stats["last_signal_alert"] = now.isoformat()
            logger.info(f"🚨 Signal-Alert gesendet: {asset} {signal}")
        else:
            self.stats["errors"] += 1
            
        return success
    
    # ═══════════════════════════════════════════════════════════════════
    # SCHEDULER
    # ═══════════════════════════════════════════════════════════════════
    
    async def _scheduler_loop(self):
        """Interne Scheduler-Schleife für tägliche Reports."""
        logger.info("📅 Report-Scheduler gestartet")
        
        last_heartbeat_date = None
        last_report_date = None
        
        while self.is_running:
            try:
                now = datetime.now()
                current_time = (now.hour, now.minute)
                current_date = now.date()
                
                # Morgen-Heartbeat (07:00)
                if (current_time == MORNING_HEARTBEAT_TIME and 
                    last_heartbeat_date != current_date):
                    await self.send_morning_heartbeat()
                    last_heartbeat_date = current_date
                
                # Abend-Report (22:00)
                if (current_time == EVENING_REPORT_TIME and 
                    last_report_date != current_date):
                    await self.send_evening_report()
                    last_report_date = current_date
                
                # Warte 30 Sekunden bis zur nächsten Prüfung
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("📅 Scheduler-Schleife abgebrochen")
                break
            except Exception as e:
                logger.error(f"❌ Fehler im Scheduler: {e}")
                await asyncio.sleep(60)
    
    async def check_and_alert_signals(self, market_data: Dict[str, Any]):
        """
        Prüft Market-Daten und sendet Alerts bei relevanten Signalen.
        
        Args:
            market_data: Dict mit Asset-Daten (signal, confidence, etc.)
        """
        for asset, data in market_data.items():
            signal = data.get('signal', 'HOLD')
            confidence = data.get('confidence', 0)
            
            # Nur alertieren wenn Confidence über Threshold UND Signal BUY/SELL
            if signal in ['BUY', 'SELL'] and confidence >= 70:
                # Finde stärkste Säule
                pillar_scores = data.get('pillar_scores', {})
                if pillar_scores:
                    strongest = max(pillar_scores, key=pillar_scores.get)
                    pillar_names = {
                        'base_signal': 'Basis-Signal',
                        'trend_confluence': 'Trend-Konfluenz',
                        'volatility': 'Volatilität',
                        'sentiment': 'Sentiment'
                    }
                    strongest_pillar = pillar_names.get(strongest, strongest)
                else:
                    strongest_pillar = "Unbekannt"
                
                await self.send_signal_alert(asset, signal, confidence, strongest_pillar)
    
    # ═══════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════
    
    async def start(self):
        """Startet das Reporting-System."""
        if self.is_running:
            logger.warning("Reporting-System läuft bereits")
            return
        
        if not self.messenger.is_available():
            logger.warning("⚠️ AppleScript nicht verfügbar - Reporting wird simuliert")
        
        self.is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("✅ Automated Reporting System gestartet")
    
    async def stop(self):
        """Stoppt das Reporting-System."""
        self.is_running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ Automated Reporting System gestoppt")
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zurück."""
        return {
            **self.stats,
            "is_running": self.is_running,
            "recipient": self.recipient,
            "signal_states_count": len(self.signal_states)
        }


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════

_reporting_instance: Optional[AutomatedReportingSystem] = None


def get_reporting_system() -> Optional[AutomatedReportingSystem]:
    """Gibt die Singleton-Instanz zurück."""
    return _reporting_instance


def init_reporting_system(
    data_provider: Callable,
    recipient: str = DEFAULT_RECIPIENT
) -> AutomatedReportingSystem:
    """
    Initialisiert das Reporting-System.
    
    Args:
        data_provider: Async-Funktion die System-Daten liefert
        recipient: Telefonnummer/E-Mail des Empfängers
    """
    global _reporting_instance
    _reporting_instance = AutomatedReportingSystem(data_provider, recipient)
    return _reporting_instance


# ═══════════════════════════════════════════════════════════════════════
# QUICK TEST
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def mock_data_provider():
        return {
            "total_balance": 88933.81,
            "active_assets": 20,
            "mode": "conservative",
            "daily_pnl": 234.56,
            "trades_today": 3,
            "winners": 2,
            "losers": 1
        }
    
    async def test():
        system = AutomatedReportingSystem(mock_data_provider)
        
        print("=== Morgen-Heartbeat ===")
        msg = await system.generate_morning_heartbeat()
        print(msg)
        
        print("\n=== Abend-Report ===")
        msg = await system.generate_evening_report()
        print(msg)
        
        print("\n=== Signal-Alert ===")
        msg = system.generate_signal_alert("GOLD", "BUY", 78, "Trend-Konfluenz")
        print(msg)
        
        print(f"\n=== AppleScript verfügbar: {AppleScriptMessenger.is_available()} ===")
    
    asyncio.run(test())
