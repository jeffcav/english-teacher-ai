"""
Audio Converter
Converts Telegram OGG audio to WAV format
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available - audio conversion will be limited")


class AudioConverter:
    """Converts audio formats for backend processing"""
    
    SUPPORTED_INPUT_FORMATS = ["ogg", "wav", "mp3", "m4a"]
    OUTPUT_FORMAT = "wav"
    
    @staticmethod
    def convert_ogg_to_wav(audio_bytes: bytes) -> Optional[bytes]:
        """
        Convert OGG audio to WAV format
        
        Args:
            audio_bytes: OGG audio data
            
        Returns:
            WAV audio bytes or None if conversion fails
            
        Raises:
            RuntimeError: If pydub is not available
        """
        if not PYDUB_AVAILABLE:
            raise RuntimeError("pydub required for audio conversion. Install: pip install pydub")
        
        try:
            # Load OGG file
            audio = AudioSegment.from_ogg(io.BytesIO(audio_bytes))
            
            # Export as WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            
            wav_bytes = wav_buffer.getvalue()
            logger.info(f"Converted audio: {len(audio_bytes)} bytes OGG → {len(wav_bytes)} bytes WAV")
            
            return wav_bytes
        
        except Exception as e:
            logger.error(f"Error converting OGG to WAV: {str(e)}")
            raise
    
    @staticmethod
    def convert_audio(audio_bytes: bytes, input_format: str = "ogg") -> Optional[bytes]:
        """
        Convert audio to WAV format (generic)
        
        Args:
            audio_bytes: Audio data
            input_format: Input audio format (ogg, mp3, m4a, wav)
            
        Returns:
            WAV audio bytes or None if conversion fails
        """
        if not PYDUB_AVAILABLE:
            logger.error("pydub not available for audio conversion")
            return None
        
        try:
            input_format = input_format.lower().strip('.')
            
            # If already WAV, return as-is
            if input_format == "wav":
                logger.debug("Audio already in WAV format")
                return audio_bytes
            
            # Load from specified format
            audio = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format=input_format
            )
            
            # Export as WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            
            wav_bytes = wav_buffer.getvalue()
            logger.info(f"Converted audio: {len(audio_bytes)} bytes {input_format.upper()} → {len(wav_bytes)} bytes WAV")
            
            return wav_bytes
        
        except Exception as e:
            logger.error(f"Error converting {input_format} to WAV: {str(e)}")
            return None
    
    @staticmethod
    def get_audio_duration(audio_bytes: bytes, format: str = "ogg") -> Optional[float]:
        """
        Get duration of audio file in seconds
        
        Args:
            audio_bytes: Audio data
            format: Audio format
            
        Returns:
            Duration in seconds or None if unavailable
        """
        if not PYDUB_AVAILABLE:
            return None
        
        try:
            audio = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format=format.lower().strip('.')
            )
            duration_seconds = len(audio) / 1000.0
            logger.debug(f"Audio duration: {duration_seconds:.1f} seconds")
            return duration_seconds
        
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return None
