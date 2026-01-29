"""
Main Telegram Bot Class
Coordinates bot lifecycle and message routing
"""
import logging
import signal
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import TelegramConfig
from .handlers import MessageHandler as MsgHandler, AudioHandler as AudioHandlerClass
from .utils import APIClient, SessionManager

logger = logging.getLogger(__name__)


class PhonicFlowBot:
    """Main Telegram bot for PhonicFlow"""
    
    def __init__(self, config: TelegramConfig = None):
        """
        Initialize bot
        
        Args:
            config: TelegramConfig instance (uses env vars if None)
        """
        self.config = config or TelegramConfig()
        self.config.validate()
        
        # Initialize components
        self.api_client = APIClient(
            self.config.BACKEND_URL,
            self.config.BACKEND_TIMEOUT
        )
        self.session_manager = SessionManager(self.config.SESSION_STORAGE_PATH)
        
        # Initialize handlers
        self.message_handler = MsgHandler(self.session_manager, self.api_client)
        self.audio_handler = AudioHandlerClass(
            self.session_manager,
            self.api_client,
            self.config
        )
        
        # Application will be created in start_polling
        self.application = None
        
        logger.info("PhonicFlowBot initialized")
    
    async def _setup_commands(self):
        """Setup bot commands"""
        commands = [
            BotCommand("start", "Start new session"),
            BotCommand("help", "Show help"),
            BotCommand("history", "View conversation history"),
            BotCommand("status", "Check session status"),
            BotCommand("new", "Start new conversation"),
            BotCommand("delete", "Delete all data"),
        ]
        await self.application.bot.set_my_commands(commands)
        logger.info("Bot commands configured")
    
    async def _on_startup(self, application: Application):
        """Called when bot starts"""
        logger.info("Bot starting up...")
        
        # Verify backend connectivity
        if not self.api_client.health_check():
            logger.warning("Backend health check failed - bot may not function correctly")
        else:
            logger.info("Backend connectivity verified")
        
        # Setup commands
        await self._setup_commands()
        
        # Log stats
        stats = self.session_manager.get_stats()
        logger.info(f"Session stats: {stats}")
    
    async def _on_shutdown(self):
        """Called when bot shuts down"""
        logger.info("Bot shutting down...")
        
        # Cleanup expired sessions
        expired = self.session_manager.cleanup_expired_sessions(
            self.config.SESSION_TIMEOUT_HOURS
        )
        logger.info(f"Cleaned up {expired} expired sessions")
    
    def start_polling(self):
        """Start bot in polling mode (pull updates from Telegram)"""
        try:
            logger.info(f"Starting bot with token {self.config.BOT_TOKEN[:10]}...")
            
            # Create application
            self.application = Application.builder() \
                .token(self.config.BOT_TOKEN) \
                .build()
            
            # Register handlers
            self._register_handlers()
            
            # Register startup/shutdown
            self.application.post_init = self._on_startup
            
            # Start polling
            logger.info(f"Starting polling (interval: {self.config.POLLING_INTERVAL}s, timeout: {self.config.POLLING_TIMEOUT}s)")
            self.application.run_polling(
                poll_interval=self.config.POLLING_INTERVAL,
                timeout=self.config.POLLING_TIMEOUT,
                allowed_updates=None
            )
        
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise
    
    def _register_handlers(self):
        """Register message handlers"""
        # Command handlers
        self.application.add_handler(
            CommandHandler("start", self.message_handler.handle_start)
        )
        self.application.add_handler(
            CommandHandler("help", self.message_handler.handle_help)
        )
        self.application.add_handler(
            CommandHandler("history", self.message_handler.handle_history)
        )
        self.application.add_handler(
            CommandHandler("status", self.message_handler.handle_status)
        )
        self.application.add_handler(
            CommandHandler("new", self.message_handler.handle_new_conversation)
        )
        self.application.add_handler(
            CommandHandler("delete", self.message_handler.handle_delete)
        )
        
        # Audio handler
        self.application.add_handler(
            MessageHandler(filters.AUDIO | filters.VOICE, self.audio_handler.handle_audio)
        )
        
        # Text message handler (fallback)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler.handle_text)
        )
        
        logger.info("Message handlers registered")
    
    def stop(self):
        """Stop the bot"""
        if self.application:
            logger.info("Stopping bot...")
            self.application.stop()


# Graceful shutdown
def setup_signal_handlers(bot: PhonicFlowBot):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down gracefully...")
        bot.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
