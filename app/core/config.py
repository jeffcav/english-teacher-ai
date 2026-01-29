"""
Configuration settings for PhonicFlow.
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = PROJECT_ROOT / "app"
FEEDBACK_DIR = APP_DIR / "feedback_storage"

# Create feedback directory if it doesn't exist
FEEDBACK_DIR.mkdir(exist_ok=True)

# Model configurations
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
DEFAULT_LLM_NAME = os.getenv("LLM_NAME", "gemma3:27b")
DEFAULT_TTS_VOICE = os.getenv("TTS_VOICE", "pyttsx3_default")  # Local pyttsx3 (no Edge-TTS needed)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Audio processing
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "m4a", "flac"]
MAX_AUDIO_DURATION = 300  # seconds (5 minutes)

# System prompt for LLM coaching
# Import the proactive curiosity prompt from prompts.py
from app.core.prompts import PROACTIVE_CURIOSITY_SYSTEM_PROMPT
SYSTEM_PROMPT = PROACTIVE_CURIOSITY_SYSTEM_PROMPT
