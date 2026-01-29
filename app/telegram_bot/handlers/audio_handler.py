"""
Audio Handler
Processes audio files from Telegram
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from ..utils.audio_converter import AudioConverter

logger = logging.getLogger(__name__)


class AudioHandler:
    """Handles audio messages from Telegram users"""
    
    def __init__(self, session_manager, api_client, config):
        """
        Initialize audio handler
        
        Args:
            session_manager: SessionManager instance
            api_client: APIClient instance
            config: TelegramConfig instance
        """
        self.session_manager = session_manager
        self.api_client = api_client
        self.config = config
        self.audio_converter = AudioConverter()
    
    async def handle_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Process audio message from user
        
        Args:
            update: Telegram Update object
            context: Callback context
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Check for audio or voice message
        audio_file = update.message.audio or update.message.voice
        if not audio_file:
            logger.warning(f"No audio found in message from user {user_id}")
            return
        
        # Check file size
        file_size_mb = audio_file.file_size / (1024 * 1024) if audio_file.file_size else 0
        if file_size_mb > self.config.MAX_AUDIO_SIZE_MB:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Audio file too large ({file_size_mb:.1f} MB). Maximum: {self.config.MAX_AUDIO_SIZE_MB} MB"
            )
            return
        
        # Get or create session
        session_id = self.session_manager.get_or_create_session(user_id)
        
        try:
            # Send processing indicator
            processing_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ Processing audio... (this may take 15-30 seconds)"
            )
            
            # Download audio from Telegram
            logger.info(f"Downloading audio from user {user_id} (session: {session_id})")
            file = await context.bot.get_file(audio_file.file_id)
            audio_bytes = await file.download_as_bytearray()
            
            logger.info(f"Downloaded audio: {len(audio_bytes)} bytes")
            
            # Convert OGG to WAV
            try:
                audio_wav = self.audio_converter.convert_ogg_to_wav(bytes(audio_bytes))
            except Exception as e:
                logger.error(f"Conversion failed: {str(e)}")
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="❌ Error converting audio. Please try again."
                )
                return
            
            # Submit to backend
            logger.info(f"Submitting audio to backend for session {session_id}")
            try:
                response = await self._submit_to_backend(session_id, audio_wav)
            except Exception as e:
                logger.error(f"Backend submission failed: {str(e)}")
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="❌ Backend error. Please try again later."
                )
                return
            
            # Update session
            session = self.session_manager.get_session(user_id)
            if session:
                session['conversation_turns'] = session.get('conversation_turns', 0) + 1
                self.session_manager.update_session(user_id, **session)
            
            # Format response
            await self._send_response(
                context, chat_id, processing_msg.message_id, response
            )
            
            logger.info(f"Audio processed successfully for session {session_id}")
        
        except TelegramError as e:
            logger.error(f"Telegram error: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Telegram error. Please try again."
            )
        except Exception as e:
            logger.error(f"Unexpected error processing audio: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error processing audio. Please try again."
            )
    
    async def _submit_to_backend(self, session_id: str, audio_wav: bytes) -> dict:
        """
        Submit audio to backend API
        
        Args:
            session_id: Backend session ID
            audio_wav: WAV audio bytes
            
        Returns:
            Backend response dict
            
        Raises:
            Exception: If submission fails
        """
        response = self.api_client.process_audio(session_id, audio_wav)
        return response
    
    async def _send_response(self, context, chat_id: int, processing_msg_id: int, response: dict):
        """
        Send formatted response back to user
        
        Args:
            context: Callback context
            chat_id: Telegram chat ID
            processing_msg_id: Processing message ID to edit/delete
            response: Backend response dict
        """
        try:
            # Edit processing message to indicate completion
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg_id,
                text="✅ Processing complete"
            )
        except Exception:
            pass  # Message may have been deleted
        
        # Send transcript
        transcript = response.get('user_transcript', '')
        if transcript:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 **Your speech:**\n\n{transcript}",
                parse_mode="Markdown"
            )
        
        # Send coaching feedback
        coaching_feedback = response.get('coaching_feedback', '')
        coaching_portuguese = response.get('coaching_feedback_portuguese', '')
        
        if coaching_feedback:
            feedback_msg = f"📋 **Coaching Feedback:**\n\n{coaching_feedback}"
            if coaching_portuguese:
                feedback_msg += f"\n\n🇧🇷 **Portuguese:**\n{coaching_portuguese}"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=feedback_msg,
                parse_mode="Markdown"
            )
        
        # Send conversational response
        conversational = response.get('conversational_response', '')
        if conversational:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"💬 **Response:**\n\n{conversational}",
                parse_mode="Markdown"
            )
        
        # Send coaching audio if available
        coaching_audio_path = response.get('coaching_audio_path')
        if coaching_audio_path:
            try:
                with open(coaching_audio_path, 'rb') as audio:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio,
                        caption="🔊 Coaching Audio (Correct Pronunciation)",
                        title="Coaching Audio"
                    )
            except Exception as e:
                logger.warning(f"Could not send coaching audio: {str(e)}")
        
        # Send conversational audio if available
        conversational_audio_path = response.get('conversational_audio_path')
        if conversational_audio_path:
            try:
                with open(conversational_audio_path, 'rb') as audio:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio,
                        caption="🎙️ Conversational Response Audio",
                        title="Conversational Response"
                    )
            except Exception as e:
                logger.warning(f"Could not send conversational audio: {str(e)}")
