"""
LLM Fallback Module für lokale Mac-Entwicklung
Ersetzt emergentintegrations wenn nicht verfügbar
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Check if emergentintegrations is available
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage as EmergentUserMessage
    EMERGENT_AVAILABLE = True
    logger.info("✅ emergentintegrations verfügbar (Emergent Platform)")
except ImportError:
    EMERGENT_AVAILABLE = False
    # This is EXPECTED in Desktop-Apps - emergentintegrations only works on Emergent Platform
    logger.info("ℹ️  Desktop-App Mode: Using Fallback (direct API keys) - emergentintegrations not available")


class UserMessage:
    """Fallback UserMessage class"""
    def __init__(self, text: str):
        self.text = text


class FallbackLlmChat:
    """
    Fallback LLM Chat für lokale Entwicklung ohne emergentintegrations
    Unterstützt: OpenAI, Anthropic, Google direkt
    """
    
    def __init__(self, api_key: str, session_id: str = "default", system_message: str = ""):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = None
        self.model = None
        self.conversation_history = []
        
        if system_message:
            self.conversation_history.append({
                "role": "system",
                "content": system_message
            })
    
    def with_model(self, provider: str, model: str):
        """Set the model provider and name"""
        self.provider = provider
        self.model = model
        logger.info(f"Fallback LLM configured: {provider}/{model}")
        return self
    
    async def send_message(self, user_message):
        """Send message to LLM - provider-agnostic"""
        
        # Extract text from UserMessage object
        if hasattr(user_message, 'text'):
            message_text = user_message.text
        else:
            message_text = str(user_message)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message_text
        })
        
        try:
            # Route to correct provider
            if self.provider == "openai":
                response = await self._call_openai(message_text)
            elif self.provider in ["anthropic", "claude"]:
                response = await self._call_anthropic(message_text)
            elif self.provider in ["google", "gemini"]:
                response = await self._call_google(message_text)
            else:
                response = f"Unbekannter Provider: {self.provider}"
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Fallback LLM error: {e}")
            return f"Fehler bei LLM-Anfrage: {str(e)}"
    
    async def _call_openai(self, message: str) -> str:
        """Call OpenAI API directly"""
        try:
            import openai
            
            # Check if this is an Emergent key (won't work with OpenAI SDK)
            if self.api_key and self.api_key.startswith("sk-emergent-"):
                return (
                    "⚠️ MAC-NUTZER: Der Emergent LLM Key funktioniert nur in der Emergent Cloud.\n\n"
                    "Für lokale Mac-Nutzung haben Sie 3 Optionen:\n\n"
                    "1. **OLLAMA (EMPFOHLEN - Kostenlos & Lokal)**\n"
                    "   brew install ollama\n"
                    "   ollama serve\n"
                    "   ollama pull llama3\n"
                    "   → In Settings: Provider='Ollama', Model='llama3'\n\n"
                    "2. **OpenAI API Key**\n"
                    "   → Ersetzen Sie EMERGENT_LLM_KEY mit echtem OpenAI-Key\n"
                    "   → https://platform.openai.com/api-keys\n\n"
                    "3. **Anthropic Claude API Key**\n"
                    "   → pip install anthropic\n"
                    "   → In Settings: Provider='Anthropic'\n\n"
                    "Details: /app/MAC_INSTALLATION.md"
                )
            
            client = openai.AsyncOpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.create(
                model=self.model or "gpt-4",
                messages=self.conversation_history,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            return "OpenAI SDK nicht installiert. Installieren Sie: pip install openai"
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Return user-friendly error
            error_str = str(e)
            if "invalid_api_key" in error_str or "401" in error_str:
                return (
                    "⚠️ Ungültiger API-Key!\n\n"
                    "Der Emergent LLM Key funktioniert nur in der Cloud.\n"
                    "Für Mac: Nutzen Sie Ollama (kostenlos) oder einen echten OpenAI-Key.\n\n"
                    "Details: /app/MAC_INSTALLATION.md"
                )
            raise
    
    async def _call_anthropic(self, message: str) -> str:
        """Call Anthropic (Claude) API directly"""
        try:
            import anthropic
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Anthropic uses different format - separate system message
            messages = [m for m in self.conversation_history if m["role"] != "system"]
            system = next((m["content"] for m in self.conversation_history if m["role"] == "system"), "")
            
            response = await client.messages.create(
                model=self.model or "claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system,
                messages=messages
            )
            
            return response.content[0].text
            
        except ImportError:
            return "Anthropic SDK nicht installiert. Installieren Sie: pip install anthropic"
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def _call_google(self, message: str) -> str:
        """Call Google Gemini API directly"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            
            model = genai.GenerativeModel(
                model_name=self.model or "gemini-1.5-pro",
                system_instruction=self.system_message
            )
            
            # Create chat with history
            chat = model.start_chat(history=[])
            
            response = await chat.send_message_async(message)
            
            return response.text
            
        except ImportError:
            return "Google SDK nicht installiert. Installieren Sie: pip install google-generativeai"
        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise


def get_llm_chat(api_key: str, session_id: str = "default", system_message: str = "") -> object:
    """
    Get LLM Chat instance - uses emergentintegrations if available, otherwise fallback
    """
    if EMERGENT_AVAILABLE:
        from emergentintegrations.llm.chat import LlmChat
        return LlmChat(api_key=api_key, session_id=session_id, system_message=system_message)
    else:
        return FallbackLlmChat(api_key=api_key, session_id=session_id, system_message=system_message)


def get_user_message(text: str) -> object:
    """Get UserMessage instance - uses emergentintegrations if available, otherwise fallback"""
    if EMERGENT_AVAILABLE:
        from emergentintegrations.llm.chat import UserMessage as EmergentUserMessage
        return EmergentUserMessage(text=text)
    else:
        return UserMessage(text=text)
