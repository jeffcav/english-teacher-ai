"""
Message Handler
Processes text commands and messages from Telegram
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles text messages and commands"""
    
    def __init__(self, session_manager, api_client):
        """
        Initialize message handler
        
        Args:
            session_manager: SessionManager instance
            api_client: APIClient instance
        """
        self.session_manager = session_manager
        self.api_client = api_client
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        # Get or create session
        session_id = self.session_manager.get_or_create_session(user_id)
        
        welcome_msg = f"""
👋 Welcome to **PhonicFlow**, {user_name}!

I'm your English pronunciation coach. Here's what I can do:

**Commands:**
🎤 Send an audio message to get pronunciation feedback
/help - Show available commands
/history - View your conversation history
/status - Check your current session
/new - Start a new conversation
/delete - Delete all your data (GDPR)

**How to use:**
1. Record an audio message with your speech
2. I'll analyze your pronunciation
3. You'll get feedback in English and Portuguese 🇧🇷
4. I'll provide coaching tips and audio examples

Let's start! Send me an audio message.
        """
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_msg,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} started bot (session: {session_id})")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
**Available Commands:**

🎤 **Audio Input**
Send an audio message (voice note or audio file) for pronunciation analysis

**Text Commands:**
/start - Start new session
/help - Show this message
/history - View conversation history
/status - Check current session info
/new - Create a new conversation
/delete - Delete all your data

**Features:**
✅ Real-time pronunciation feedback
✅ Portuguese translations 🇧🇷
✅ Coaching tips and corrections
✅ Audio playback examples
✅ Multi-turn conversations

**Tips:**
- Record clear audio for better accuracy
- Speak naturally and at a normal pace
- Use actual English sentences for practice
- Check your feedback carefully

Need help? Just send an audio message and I'll guide you!
        """
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_msg,
            parse_mode="Markdown"
        )
    
    async def handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if not session:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ No session found. Use /start to begin."
            )
            return
        
        session_id = session['session_id']
        history = self.api_client.get_conversation_history(session_id)
        
        if not history:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📝 No conversation history yet. Send an audio message to start!"
            )
            return
        
        # Format history message (limit to last 5 turns for readability)
        recent_history = history[-5:]
        
        msg = "📖 **Recent Conversation History:**\n\n"
        for i, turn in enumerate(recent_history, 1):
            user_text = turn.get('user', 'N/A')[:100]  # Truncate long text
            conversational = turn.get('conversational', 'N/A')[:100]
            
            msg += f"**Turn {len(history)-5+i}:**\n"
            msg += f"👤 You: {user_text}\n"
            msg += f"🤖 Me: {conversational}\n\n"
        
        # Add pagination info
        if len(history) > 5:
            msg += f"_Showing last 5 of {len(history)} turns_"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} viewed history ({len(history)} turns)")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if not session:
            status_msg = "❌ No active session. Use /start to begin."
        else:
            session_id = session['session_id']
            turns = session.get('conversation_turns', 0)
            created = session.get('created_at', 'Unknown')
            
            # Check backend health
            backend_ok = self.api_client.health_check()
            backend_status = "✅ Connected" if backend_ok else "⚠️ Offline"
            
            status_msg = f"""
**📊 Session Status**

🆔 Session ID: `{session_id[-8:]}`...
📊 Conversation Turns: {turns}
📅 Created: {created}
🌐 Backend: {backend_status}
            """
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=status_msg,
            parse_mode="Markdown"
        )
    
    async def handle_new_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new command - start fresh conversation"""
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if session:
            old_session_id = session['session_id']
            # Clear old session on backend
            self.api_client.clear_session(old_session_id)
            
            # Delete local session
            self.session_manager.delete_session(user_id)
        
        # Create new session
        session_id = self.session_manager.get_or_create_session(user_id)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✨ New conversation started! Session: `{session_id[-8:]}`...\n\nSend an audio message to begin.",
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} started new conversation (session: {session_id})")
    
    async def handle_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /delete command - GDPR compliance"""
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if session:
            session_id = session['session_id']
            
            # Delete from backend
            self.api_client.clear_session(session_id)
            
            # Delete local session
            self.session_manager.delete_session(user_id)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ All your data has been deleted (GDPR). You can start fresh with /start anytime."
            )
            
            logger.info(f"User {user_id} requested data deletion (session: {session_id})")
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="ℹ️ No data to delete. Use /start to create a session."
            )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Ignore if it's a command
        if text.startswith('/'):
            return
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💬 Thanks for your message!\n\nFor best results, please send an **audio message** with your spoken English. I'll analyze your pronunciation and provide feedback.\n\nUse /help to see all available commands."
        )
