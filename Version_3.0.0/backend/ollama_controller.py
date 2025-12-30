"""
🤖 KI-Controller (Ollama / Llama 3.2) - V3.0.0

Übersetzt iMessage-Befehle in JSON-Aktionen und führt natürliche Konversationen.
Der Controller kann auf Deutsch antworten und versteht natürliche Sprache.

Konfiguration:
- Modell: Llama 3.2 (32k Context-Fenster)
- Lokal via Ollama API
"""

import os
import json
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

# V3.0.0: Verbesserter System-Prompt für natürliche Konversation
CONTROLLER_SYSTEM_PROMPT = """Du bist der intelligente Assistent einer autonomen Trading-App. 
Du kannst natürlich auf Deutsch kommunizieren und hilfst dem Benutzer bei allem rund ums Trading.

DEINE PERSÖNLICHKEIT:
- Freundlich und professionell
- Antworte kurz und präzise (max 3-4 Sätze)
- Verwende Emojis sparsam aber passend
- Sei hilfsbereit und proaktiv

DEIN WISSEN:
Das 4-Säulen-Konfidenzmodell:
1. Basis-Signal (25%): RSI, MACD, Bollinger Bänder
2. Trend-Konfluenz (25%): Multi-Timeframe Analyse  
3. Volatilität (25%): ATR-basierte Risikobewertung
4. Sentiment (25%): Nachrichten- und Marktsentiment

WICHTIG:
- Wenn der Benutzer nach einer AKTION fragt (Status, Balance, Trades, etc.), 
  antworte mit einem JSON-Objekt im Format:
  {"action": "AKTION", "response": "Deine freundliche Antwort"}
  
- Wenn der Benutzer nur PLAUDERT oder eine FRAGE hat, antworte direkt mit Text (kein JSON).

VERFÜGBARE AKTIONEN:
- GET_STATUS: Systemstatus
- GET_BALANCE: Kontostand beider Broker
- GET_TRADES: Offene Positionen
- CLOSE_PROFIT: Gewinn-Trades schließen
- STOP_TRADING: Trading pausieren
- START_TRADING: Trading fortsetzen
- ANALYZE_ASSET: Asset analysieren (z.B. "Wie steht Gold?")
- SET_MODE_CONSERVATIVE/NEUTRAL/AGGRESSIVE: Modus ändern
- HELP: Hilfe anzeigen

BEISPIELE:
Benutzer: "Guten Morgen, wie geht's?"
Du: "Guten Morgen! 👋 Mir geht's gut, ich überwache gerade 20 Assets für dich. Bitcoin sieht heute interessant aus mit 73% Konfidenz!"

Benutzer: "Balance"
Du: {"action": "GET_BALANCE", "response": "Hier sind deine Kontostände:"}

Benutzer: "Was ist der 4-Säulen-Score?"
Du: "Der 4-Säulen-Score ist unser Konfidenzmodell für Trades: Basis-Signal (technische Indikatoren), Trend (Multi-Timeframe), Volatilität (ATR) und Sentiment (News). Je höher der Score, desto sicherer das Signal! 📊"
"""

# Mapping für Aktions-Erkennung
ACTION_KEYWORDS = {
    "status": "GET_STATUS",
    "ampel": "GET_STATUS", 
    "balance": "GET_BALANCE",
    "kontostand": "GET_BALANCE",
    "guthaben": "GET_BALANCE",
    "konto": "GET_BALANCE",
    "trades": "GET_TRADES",
    "positionen": "GET_TRADES",
    "offen": "GET_TRADES",
    "stop": "STOP_TRADING",
    "pause": "STOP_TRADING",
    "start": "START_TRADING",
    "weiter": "START_TRADING",
    "hilfe": "HELP",
    "help": "HELP",
    "konservativ": "SET_MODE_CONSERVATIVE",
    "aggressiv": "SET_MODE_AGGRESSIVE",
    "standard": "SET_MODE_NEUTRAL",
}


class OllamaController:
    """
    KI-Controller für NLP-Analyse und Signal-Begründungen.
    """
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url
        self.model = model
        self.is_available = False
        self.last_health_check = None
        
        logger.info(f"🤖 Ollama Controller initialisiert")
        logger.info(f"   URL: {self.base_url}")
        logger.info(f"   Modell: {self.model}")
    
    async def check_availability(self) -> Dict[str, Any]:
        """
        Prüft ob Ollama verfügbar ist und das Modell geladen ist.
        
        Returns:
            Dict mit status, available_models, etc.
        """
        result = {
            "available": False,
            "url": self.base_url,
            "model": self.model,
            "error": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Prüfe API-Verfügbarkeit
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        result["available_models"] = models
                        
                        # Prüfe ob unser Modell verfügbar ist
                        if any(self.model in m for m in models):
                            result["available"] = True
                            self.is_available = True
                            logger.info(f"✅ Ollama verfügbar mit Modell {self.model}")
                        else:
                            result["error"] = f"Modell {self.model} nicht gefunden. Verfügbar: {models}"
                    else:
                        result["error"] = f"API returned status {response.status}"
                        
        except aiohttp.ClientError as e:
            result["error"] = f"Verbindungsfehler: {str(e)}"
        except Exception as e:
            result["error"] = f"Unerwarteter Fehler: {str(e)}"
        
        self.last_health_check = datetime.utcnow().isoformat()
        return result
    
    async def analyze_command(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analysiert einen Befehlstext via Ollama und gibt eine strukturierte Antwort zurück.
        V3.0.0: Unterstützt natürliche Konversation UND Aktionen.
        
        Args:
            text: Der zu analysierende Befehlstext
            context: Optionaler Kontext (Marktdaten, Status, etc.)
            
        Returns:
            Dict mit action, response, und weiteren Feldern
        """
        text_lower = text.lower().strip()
        
        # V3.0.0: Schnelle Keyword-Erkennung für häufige Befehle
        for keyword, action in ACTION_KEYWORDS.items():
            if keyword in text_lower:
                logger.info(f"⚡ Schnelle Aktion erkannt: {action} (Keyword: {keyword})")
                return {
                    "action": action,
                    "confidence": 95,
                    "response": f"Führe {action} aus...",
                    "requires_ollama": False
                }
        
        # Wenn Ollama nicht verfügbar, nutze Fallback
        if not self.is_available:
            check = await self.check_availability()
            if not check["available"]:
                logger.warning(f"⚠️ Ollama nicht verfügbar, nutze Fallback")
                return self._fallback_response(text)
        
        # V3.0.0: Kontext-angereicherte Anfrage
        context_str = ""
        if context:
            context_str = f"""
AKTUELLER KONTEXT:
- Aktive Assets: {context.get('active_assets', 20)}
- Top Signal: {context.get('top_signal', 'Bitcoin 73%')}
- Modus: {context.get('mode', 'Standard')}
- Letzte Aktivität: {context.get('last_activity', 'Gerade aktiv')}
"""
        
        prompt = f"""{context_str}
BENUTZER-NACHRICHT: "{text}"

Analysiere diese Nachricht und antworte passend:
- Wenn es eine AKTION ist, antworte mit JSON: {{"action": "AKTION", "response": "Freundliche Bestätigung"}}
- Wenn es eine FRAGE oder Konversation ist, antworte direkt mit natürlichem Text.

Deine Antwort:"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": CONTROLLER_SYSTEM_PROMPT,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,  # Etwas höher für natürlichere Antworten
                        "num_predict": 300   # Mehr Platz für Konversation
                    }
                }
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get("response", "").strip()
                        
                        # Parse Antwort (JSON oder Text)
                        return self._parse_intelligent_response(response_text, text)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ollama API Fehler: {error_text}")
                        return self._fallback_response(text)
                        
        except Exception as e:
            logger.error(f"❌ Ollama Fehler: {e}")
            return self._fallback_response(text)
    
    def _fallback_response(self, text: str) -> Dict[str, Any]:
        """Generiert eine Fallback-Antwort wenn Ollama nicht verfügbar ist."""
        text_lower = text.lower()
        
        # Versuche Aktion zu erkennen
        for keyword, action in ACTION_KEYWORDS.items():
            if keyword in text_lower:
                return {
                    "action": action,
                    "confidence": 80,
                    "response": f"Verstanden! Führe {action} aus...",
                    "fallback": True
                }
        
        # Standard-Fallback für Konversation
        greetings = ["hallo", "hi", "guten", "morgen", "tag", "abend"]
        if any(g in text_lower for g in greetings):
            return {
                "action": "CONVERSATION",
                "response": "Hallo! 👋 Ich bin dein Trading-Assistent. Wie kann ich dir helfen? Frag mich nach Status, Balance oder Trades!",
                "fallback": True
            }
        
        # Fragen erkennen
        if "?" in text or text_lower.startswith(("wie", "was", "wann", "wo", "warum", "wer")):
            return {
                "action": "CONVERSATION", 
                "response": "Das ist eine gute Frage! Leider bin ich gerade offline. Versuche es mit: Status, Balance, oder Trades.",
                "fallback": True
            }
        
        return {
            "action": "UNKNOWN",
            "response": "Ich habe dich nicht ganz verstanden. Verfügbare Befehle: Status, Balance, Trades, Start, Stop, Hilfe",
            "fallback": True
        }
    
    def _parse_intelligent_response(self, response_text: str, original_text: str) -> Dict[str, Any]:
        """Parst die intelligente Antwort von Ollama (JSON oder Text)."""
        
        # Versuche JSON zu parsen
        try:
            # Direktes Parsing
            result = json.loads(response_text)
            if "action" in result:
                result["requires_ollama"] = True
                return result
        except json.JSONDecodeError:
            pass
        
        # Versuche JSON aus dem Text zu extrahieren
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                if "action" in result:
                    result["requires_ollama"] = True
                    return result
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Kein JSON gefunden - es ist eine Konversations-Antwort
        return {
            "action": "CONVERSATION",
            "response": response_text,
            "requires_ollama": True,
            "original_query": original_text
        }
    
    async def generate_signal_reasoning(
        self,
        asset: str,
        signal: str,
        pillar_scores: Dict[str, float],
        market_data: Dict
    ) -> str:
        """
        Generiert eine menschenlesbare Begründung für ein Trading-Signal.
        
        Args:
            asset: Das Asset (z.B. "GOLD")
            signal: Das Signal (BUY/SELL/HOLD)
            pillar_scores: Die Scores der 4 Säulen
            market_data: Zusätzliche Marktdaten
            
        Returns:
            String mit der Begründung
        """
        if not self.is_available:
            # Einfache Begründung ohne Ollama
            return self._generate_simple_reasoning(asset, signal, pillar_scores)
        
        prompt = f"""Generiere eine kurze, präzise Begründung (max 2 Sätze) für dieses Trading-Signal:

Asset: {asset}
Signal: {signal}
Säulen-Scores:
- Basis-Signal: {pillar_scores.get('base_signal', 0):.0f}%
- Trend-Konfluenz: {pillar_scores.get('trend_confluence', 0):.0f}%
- Volatilität: {pillar_scores.get('volatility', 0):.0f}%
- Sentiment: {pillar_scores.get('sentiment', 0):.0f}%

Aktueller Preis: {market_data.get('price', 'N/A')}
24h Änderung: {market_data.get('change_24h', 'N/A')}%

Antworte nur mit der Begründung, kein JSON."""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": "Du bist ein erfahrener Trading-Analyst. Erkläre Signale kurz und verständlich auf Deutsch.",
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 150
                    }
                }
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip()
                        
        except Exception as e:
            logger.error(f"❌ Fehler bei Signal-Reasoning: {e}")
        
        return self._generate_simple_reasoning(asset, signal, pillar_scores)
    
    def _generate_simple_reasoning(
        self,
        asset: str,
        signal: str,
        pillar_scores: Dict[str, float]
    ) -> str:
        """Generiert eine einfache Begründung ohne KI."""
        # Finde die stärkste Säule
        pillars = {
            "Basis-Signal": pillar_scores.get("base_signal", 0),
            "Trend-Konfluenz": pillar_scores.get("trend_confluence", 0),
            "Volatilität": pillar_scores.get("volatility", 0),
            "Sentiment": pillar_scores.get("sentiment", 0)
        }
        
        strongest = max(pillars, key=pillars.get)
        score = pillars[strongest]
        
        total = sum(pillar_scores.values()) / 4
        
        if signal == "BUY":
            return f"{asset}: Kaufsignal basiert primär auf {strongest} ({score:.0f}%). Gesamtscore: {total:.0f}%."
        elif signal == "SELL":
            return f"{asset}: Verkaufssignal durch {strongest} ({score:.0f}%) getriggert. Gesamtscore: {total:.0f}%."
        else:
            return f"{asset}: Kein klares Signal. Stärkste Säule: {strongest} ({score:.0f}%). Warte auf bessere Konfluenz."


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════

_controller_instance: Optional[OllamaController] = None


def get_ollama_controller() -> OllamaController:
    """Gibt die Singleton-Instanz des Controllers zurück."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = OllamaController()
    return _controller_instance


async def analyze_command(text: str) -> Dict[str, Any]:
    """Shortcut für Befehlsanalyse."""
    controller = get_ollama_controller()
    return await controller.analyze_command(text)


# ═══════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    async def test():
        controller = OllamaController()
        
        # Prüfe Verfügbarkeit
        print("Prüfe Ollama-Verfügbarkeit...")
        status = await controller.check_availability()
        print(f"Status: {status}")
        
        if status["available"]:
            # Teste Befehlsanalyse
            test_commands = [
                "Status",
                "Wie geht es Gold?",
                "Zeig mir den Bitcoin-Kurs",
                "Schließe alle Positionen mit Gewinn"
            ]
            
            for cmd in test_commands:
                print(f"\n📝 Befehl: {cmd}")
                result = await controller.analyze_command(cmd)
                print(f"   Ergebnis: {result}")
    
    asyncio.run(test())
