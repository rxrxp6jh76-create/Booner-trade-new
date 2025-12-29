"""
🤖 KI-Controller (Ollama / Llama 3.2) - V3.0.0

Übersetzt iMessage-Befehle in JSON-Aktionen und liefert Begründungen
für Trading-Signale basierend auf dem 4-Säulen-Modell.

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

# System-Prompt für den Controller
CONTROLLER_SYSTEM_PROMPT = """Du bist der Controller der Trading-App. 
Übersetze iMessage-Befehle in JSON-Aktionen. 
Nutze das 4-Säulen-Modell zur Begründung von Signalen. 
Antworte kurz und präzise.

Das 4-Säulen-Modell:
1. Basis-Signal: Technische Indikatoren (RSI, MACD, Bollinger)
2. Trend-Konfluenz: Multi-Timeframe Trendrichtung
3. Volatilität: ATR-basierte Risikobewertung
4. Sentiment: Nachrichten- und Marktsentiment

Output-Format: Immer JSON
{"action": "AKTION", "asset": "NAME", "confidence": SCORE, "reasoning": "BEGRÜNDUNG"}

Verfügbare Aktionen:
- GET_STATUS: Systemstatus abrufen
- GET_BALANCE: Kontostand abrufen
- GET_TRADES: Offene Trades zeigen
- CLOSE_PROFIT: Gewinne sichern
- STOP_TRADING: Trading pausieren
- START_TRADING: Trading fortsetzen
- ANALYZE_ASSET: Asset analysieren (braucht "asset" Parameter)
- SET_MODE_CONSERVATIVE: Konservativer Modus
- SET_MODE_NEUTRAL: Standard Modus
- SET_MODE_AGGRESSIVE: Aggressiver Modus
- UNKNOWN: Befehl nicht erkannt

Antworte NUR mit gültigem JSON, keine zusätzlichen Erklärungen außerhalb des JSON."""


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
    
    async def analyze_command(self, text: str) -> Dict[str, Any]:
        """
        Analysiert einen Befehlstext via Ollama und gibt eine strukturierte Aktion zurück.
        
        Args:
            text: Der zu analysierende Befehlstext
            
        Returns:
            Dict mit action, confidence, reasoning
        """
        if not self.is_available:
            check = await self.check_availability()
            if not check["available"]:
                logger.warning(f"⚠️ Ollama nicht verfügbar: {check.get('error')}")
                return {
                    "action": "UNKNOWN",
                    "confidence": 0,
                    "reasoning": "Ollama nicht verfügbar",
                    "error": check.get("error")
                }
        
        prompt = f"""Analysiere diesen Befehl und gib eine JSON-Aktion zurück:

Befehl: "{text}"

Antworte NUR mit gültigem JSON im Format:
{{"action": "AKTION", "asset": "NAME_ODER_NULL", "confidence": 0-100, "reasoning": "KURZE_BEGRÜNDUNG"}}"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": CONTROLLER_SYSTEM_PROMPT,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Niedrig für konsistente Antworten
                        "num_predict": 200   # Kurze Antworten
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
                        
                        # Parse JSON aus Antwort
                        return self._parse_response(response_text)
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ollama API Fehler: {error_text}")
                        return {
                            "action": "UNKNOWN",
                            "confidence": 0,
                            "reasoning": f"API Fehler: {response.status}",
                            "error": error_text
                        }
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ Verbindungsfehler zu Ollama: {e}")
            return {
                "action": "UNKNOWN",
                "confidence": 0,
                "reasoning": "Verbindungsfehler",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"❌ Unerwarteter Fehler: {e}")
            return {
                "action": "UNKNOWN",
                "confidence": 0,
                "reasoning": "Unerwarteter Fehler",
                "error": str(e)
            }
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parst die JSON-Antwort von Ollama."""
        try:
            # Versuche direktes Parsing
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Versuche JSON aus dem Text zu extrahieren
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback
        logger.warning(f"⚠️ Konnte JSON nicht parsen: {text[:100]}...")
        return {
            "action": "UNKNOWN",
            "confidence": 0,
            "reasoning": "Antwort konnte nicht geparst werden",
            "raw_response": text
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
