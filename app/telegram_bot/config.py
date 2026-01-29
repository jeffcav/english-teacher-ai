"""
Telegram Bot Configuration
"""
import os
from pathlib import Path

class TelegramConfig:
    """Configuration for Telegram Bot"""
    
    # Bot credentials
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Backend connection
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "30"))
    
    # Polling settings
    POLLING_INTERVAL = int(os.getenv("BOT_POLLING_INTERVAL", "1"))
    POLLING_TIMEOUT = int(os.getenv("BOT_POLLING_TIMEOUT", "30"))
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv("BOT_RATE_LIMIT", "true").lower() == "true"
    RATE_LIMIT_MESSAGES_PER_MINUTE = int(os.getenv("BOT_RATE_LIMIT_MPM", "30"))
    
    # Session management
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SESSION_STORAGE_PATH = os.getenv("SESSION_STORAGE_PATH", "app/feedback_storage")
    
    # Audio settings
    MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "20"))
    SUPPORTED_AUDIO_FORMATS = ["ogg", "wav", "mp3"]
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("BOT_LOG_FILE", "logs/telegram_bot.log")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        if not cls.BACKEND_URL:
            raise ValueError("BACKEND_URL environment variable not set")
        return True
