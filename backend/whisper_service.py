"""
Whisper Speech-to-Text Service
Local transcription using OpenAI Whisper
V2.3.34: Verbesserte Fehlermeldungen und ffmpeg Check
"""
import logging
import tempfile
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if ffmpeg is available (required for whisper)
FFMPEG_AVAILABLE = False
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    FFMPEG_AVAILABLE = result.returncode == 0
    if FFMPEG_AVAILABLE:
        logger.info("✅ ffmpeg verfügbar")
except FileNotFoundError:
    logger.warning("⚠️ ffmpeg nicht gefunden. Installieren Sie: brew install ffmpeg (Mac) oder apt install ffmpeg (Linux)")

# Check if whisper is available
WHISPER_AVAILABLE = False
WHISPER_ERROR = None
try:
    import whisper
    WHISPER_AVAILABLE = True
    logger.info("✅ Whisper verfügbar für lokale Spracherkennung")
except ImportError as e:
    WHISPER_ERROR = str(e)
    logger.warning(f"⚠️ Whisper nicht installiert: {e}")


async def transcribe_audio(audio_file_path: str, language: str = "de") -> dict:
    """
    Transcribe audio file using Whisper
    
    Args:
        audio_file_path: Path to audio file (mp3, wav, m4a, etc.)
        language: Language code (de, en, etc.)
    
    Returns:
        dict with 'success', 'text', 'language'
    """
    if not FFMPEG_AVAILABLE:
        return {
            "success": False,
            "error": "ffmpeg nicht gefunden. Auf Mac: 'brew install ffmpeg'. Auf Linux: 'apt install ffmpeg'",
            "text": ""
        }
    
    if not WHISPER_AVAILABLE:
        error_detail = f"Import-Fehler: {WHISPER_ERROR}" if WHISPER_ERROR else "Unbekannter Fehler"
        return {
            "success": False,
            "error": f"Whisper nicht verfügbar. {error_detail}\n\nInstallation:\npip3 install openai-whisper",
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
