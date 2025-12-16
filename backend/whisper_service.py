"""
Whisper Speech-to-Text Service
Local transcription using OpenAI Whisper
"""
import logging
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if whisper is available
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
    logger.info("✅ Whisper verfügbar für lokale Spracherkennung")
except ImportError:
    logger.warning("⚠️ Whisper nicht installiert. Installieren Sie: pip install openai-whisper")


async def transcribe_audio(audio_file_path: str, language: str = "de") -> dict:
    """
    Transcribe audio file using Whisper
    
    Args:
        audio_file_path: Path to audio file (mp3, wav, m4a, etc.)
        language: Language code (de, en, etc.)
    
    Returns:
        dict with 'success', 'text', 'language'
    """
    if not WHISPER_AVAILABLE:
        return {
            "success": False,
            "error": "Whisper nicht installiert. Installieren Sie: pip install openai-whisper",
            "text": ""
        }
    
    try:
        logger.info(f"Transkribiere Audio-Datei: {audio_file_path}")
        
        # Load Whisper model (small model for balance between speed and accuracy)
        # Options: tiny, base, small, medium, large
        model = whisper.load_model("small")
        
        # Transcribe
        result = model.transcribe(
            audio_file_path,
            language=language,
            fp16=False  # CPU compatibility
        )
        
        text = result.get("text", "").strip()
        detected_language = result.get("language", language)
        
        logger.info(f"✅ Transkription erfolgreich: {len(text)} Zeichen, Sprache: {detected_language}")
        
        return {
            "success": True,
            "text": text,
            "language": detected_language
        }
        
    except Exception as e:
        logger.error(f"Whisper Transkriptions-Fehler: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": ""
        }


async def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.wav", language: str = "de") -> dict:
    """
    Transcribe audio from bytes
    
    Args:
        audio_bytes: Audio file as bytes
        filename: Original filename (for extension detection)
        language: Language code
    
    Returns:
        dict with 'success', 'text', 'language'
    """
    if not WHISPER_AVAILABLE:
        return {
            "success": False,
            "error": "Whisper nicht installiert",
            "text": ""
        }
    
    # Save to temporary file
    suffix = Path(filename).suffix or ".wav"
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        
        # Transcribe
        result = await transcribe_audio(temp_path, language)
        
        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing audio bytes: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": ""
        }
