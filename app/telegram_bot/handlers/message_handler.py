"""
Message Handler
Processes text commands and messages from Telegram
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
/level - Set your English level
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

Let's start! First, tell me your English level with /level, then send me an audio message.
        """
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_msg,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} started bot (session: {session_id})")
    
    async def handle_level(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /level command - show English level selection menu"""
        user_id = update.effective_user.id
        session = self.session_manager.get_session(user_id)
        
        if not session:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ No session found. Use /start to begin."
            )
            return
        
        current_level = session.get('english_level', 'intermediate')
        
        # Create inline keyboard with level options
        keyboard = [
            [
                InlineKeyboardButton("🟢 Entry Level", callback_data="level_entry_level"),
                InlineKeyboardButton("🟡 Intermediate", callback_data="level_intermediate"),
            ],
            [
                InlineKeyboardButton("🔴 Advanced", callback_data="level_advanced"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = f"""
**📊 Select Your English Level**

Current level: **{current_level.replace('_', ' ').title()}**

Choose the level that best describes your English proficiency:

🟢 **Entry Level** - Just starting out, learning basics
🟡 **Intermediate** - Can have conversations, learning to improve
🔴 **Advanced** - Near-native or fluent, focusing on nuance

The feedback will be tailored to your level!
        """
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        logger.info(f"User {user_id} opened level selection menu")
    
    async def handle_level_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle level selection button presses"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Extract level from callback data
        callback_data = query.data
        if callback_data.startswith("level_"):
            english_level = callback_data.replace("level_", "")
            
            # Update session with new level
            if self.session_manager.update_session(user_id, english_level=english_level):
                level_display = english_level.replace('_', ' ').title()
                
                await query.answer(f"✅ English level set to {level_display}")
                
                await query.edit_message_text(
                    text=f"✅ **English Level Updated**\n\nYour level is now: **{level_display}**\n\nFeedback will be tailored to your proficiency. Send an audio message to start!",
                    parse_mode="Markdown"
                )
                
                logger.info(f"User {user_id} changed English level to {english_level}")
            else:
                await query.answer("❌ Error updating level. Try again.", show_alert=True)
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
**Available Commands:**

🎤 **Audio Input**
Send an audio message (voice note or audio file) for pronunciation analysis

**Text Commands:**
/level - Set your English level (entry level, intermediate, advanced)
/start - Start new session
/help - Show this message
/history - View conversation history
/status - Check current session info
/new - Create a new conversation
/delete - Delete all your data

**Features:**
✅ Real-time pronunciation feedback
✅ Level-tailored coaching (Entry, Intermediate, Advanced)
✅ Portuguese translations 🇧🇷
✅ Coaching tips and corrections
✅ Audio playback examples
✅ Multi-turn conversations

**Tips:**
- Use /level to set your proficiency level
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
