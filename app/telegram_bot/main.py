"""
Telegram Bot Main Entry Point
Run with: python -m app.telegram_bot.main
"""
import sys
import logging
from pathlib import Path

# Setup logging
log_file = Path("logs/telegram_bot.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import bot
try:
    from .bot import PhonicFlowBot, setup_signal_handlers
    from .config import TelegramConfig
except ImportError as e:
    logger.error(f"Failed to import bot modules: {str(e)}")
    sys.exit(1)


def main():
    """Main entry point"""
    try:
        logger.info("="*60)
        logger.info("PhonicFlow Telegram Bot Starting")
        logger.info("="*60)
        
        # Initialize config
        config = TelegramConfig()
        
        # Initialize bot
        bot = PhonicFlowBot(config)
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(bot)
        
        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        bot.start_polling()
    
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        logger.error("Please set TELEGRAM_BOT_TOKEN and BACKEND_URL environment variables")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
