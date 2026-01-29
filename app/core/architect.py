"""
PhonicFlowArchitect: Core orchestration engine for the AI tutor pipeline.
Manages STT, LLM coaching, and TTS synthesis with conversation context.
"""
import os
import asyncio
import json
import re
import whisper
import ollama
from TTS.api import TTS
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from app.models.schemas import FeedbackResponse
from app.core.config import (
    FEEDBACK_DIR,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_LLM_NAME,
    DEFAULT_TTS_VOICE,
    SYSTEM_PROMPT,
    OLLAMA_BASE_URL,
)


class PhonicFlowArchitect:
    """
    Main orchestrator for the PhonicFlow AI tutor.
    
    Coordinates three AI engines:
    - Whisper (STT): Transcribes speech to text
    - Ollama (LLM): Analyzes and provides coaching
    - CoquiTTS (TTS): Synthesizes audio feedback (English only)
    """

    @staticmethod
    def _filter_english_only(text: str) -> str:
        """
        Filter out non-English characters from text.
        Keeps only ASCII letters, numbers, common punctuation, and spaces.
        Non-English characters are silently discarded.
        
        Args:
            text: Text potentially containing non-English characters
            
        Returns:
            Text with only English characters preserved
        """
        if not text or not isinstance(text, str):
            return ""
        
        import unicodedata
        
        # Keep English letters, numbers, spaces, and common punctuation
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:!?'\"-()&"
        )
        
        filtered = ''.join(char for char in text if char in allowed_chars)
        
        # Clean up multiple spaces
        filtered = ' '.join(filtered.split())
        
        return filtered.strip()

    @staticmethod
    def _strip_xml_tags(text: str) -> str:
        """
        Remove XML/HTML tags from text while preserving content.
        Handles various XML formats including nested tags, declarations, and HTML entities.
        
        Args:
            text: Text potentially containing XML/HTML tags
            
        Returns:
            Text with XML/HTML tags removed
        """
        if not text or not isinstance(text, str):
            return text if isinstance(text, str) else ""
        
        # First, unescape HTML entities in case XML is HTML-encoded
        # e.g., &lt;tag&gt; becomes <tag>
        text = (text
            .replace('&amp;', '&')  # Must be first to avoid double-unescaping
            .replace('&lt;', '<')
            .replace('&gt;', '>')
            .replace('&quot;', '"')
            .replace('&#39;', "'"))
        
        # Add space between consecutive tags to preserve word boundaries
        # This handles cases like: </tag><tag> -> </tag> <tag>
        text = re.sub(r'><', '> <', text)
        
        # Remove all XML-style tags: <...any content...>
        # This handles: <tag>, </tag>, <tag/>, <?xml?>, <![CDATA[...]]>, etc.
        # Replace tags with spaces to preserve word boundaries
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Clean up any extra whitespace that might result
        cleaned = ' '.join(text.split())
        
        return cleaned.strip()

    def __init__(
        self,
        whisper_model: str = DEFAULT_WHISPER_MODEL,
        llm_name: str = DEFAULT_LLM_NAME,
        tts_voice: str = DEFAULT_TTS_VOICE,
    ):
        """
        Initialize the AI engines.
        
        Args:
            whisper_model: Whisper model name (base.en, medium.en, large-v3)
            llm_name: Ollama model name (llama3, mistral)
            tts_voice: Edge-TTS voice identifier
            
        Note:
            - base.en: Fast, suitable for real-time processing
            - large-v3: More accurate for accents and pronunciation
        """
        self.whisper_model = whisper_model
        self.llm_name = llm_name
        self.tts_voice = tts_voice
        self.feedback_dir = FEEDBACK_DIR
        self.conversation_dir = FEEDBACK_DIR / "conversations"
        
        # Create conversations directory
        self.conversation_dir.mkdir(parents=True, exist_ok=True)
        
        # Lazy-load models to avoid initialization overhead
        self._stt_engine = None
        self._ollama_client = None
        
    @property
    def stt_engine(self):
        """Lazy-load Whisper model on first use."""
        if self._stt_engine is None:
            self._stt_engine = whisper.load_model(
                self.whisper_model,
                device="cuda" if whisper.torch.cuda.is_available() else "cpu"
            )
        return self._stt_engine

    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """
        Retrieve conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation entries with user/coach/conversation turns
        """
        history_file = self.conversation_dir / f"{session_id}.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[HISTORY] Error loading conversation history: {str(e)}")
                return []
        return []

    def save_conversation_turn(
        self,
        session_id: str,
        user_transcript: str,
        coaching_feedback: str,
        conversational_response: str
    ) -> None:
        """
        Save a conversation turn to history.
        
        Args:
            session_id: Session identifier
            user_transcript: What user said
            coaching_feedback: Phonetic coaching
            conversational_response: Conversational reply
        """
        history_file = self.conversation_dir / f"{session_id}.json"
        
        # Load existing history or start new
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except:
                history = []
        else:
            history = []
        
        # Append new turn
        turn = {
            "user": user_transcript,
            "coaching": coaching_feedback,
            "conversational": conversational_response
        }
        history.append(turn)
        
        # Save updated history
        try:
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
            print(f"[HISTORY] Saved conversation turn {len(history)} for session {session_id}")
        except Exception as e:
            print(f"[HISTORY] Error saving conversation history: {str(e)}")

    def clear_conversation_history(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        history_file = self.conversation_dir / f"{session_id}.json"
        if history_file.exists():
            try:
                os.remove(history_file)
                print(f"[HISTORY] Cleared conversation history for session {session_id}")
                return True
            except Exception as e:
                print(f"[HISTORY] Error clearing history: {str(e)}")
                return False
        return True

    def transcribe_speech(self, audio_file_path: str) -> str:
        """
        Step 1: Convert user audio to text.
        
        Uses Whisper to transcribe speech with minimal post-processing
        to preserve pronunciation errors and colloquialisms.
        
        Args:
            audio_file_path: Path to audio file (.wav, .mp3, .m4a, .flac)
            
        Returns:
            Transcribed text from the audio
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        # Use fp16=False for CPU compatibility; set to True for GPU
        has_gpu = False
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except:
            has_gpu = False

        result = self.stt_engine.transcribe(
            audio_file_path,
            task="transcribe",
            fp16=has_gpu,
            language="en"
        )
        return result['text'].strip()

    async def get_linguistic_coaching(
        self,
        user_text: str,
        conversation_history: List[Dict] = None
    ) -> tuple[str, str]:
        """
        Step 2: Use Ollama to analyze transcription and provide TWO outputs:
        1. Coaching feedback about correctness and naturality
        2. Conversational response as if responding to a friend
        
        Uses conversation history for context to enable natural multi-turn dialogue.
        
        The LLM analyzes the transcribed text for:
        - Pronunciation errors (inferred from spelling)
        - Grammar and syntax issues
        - Idiomatic alternatives
        - Natural conversational response
        - Context from previous exchanges
        
        Args:
            user_text: Transcribed speech from user
            conversation_history: Previous turns in conversation (optional)
            
        Returns:
            Tuple of (coaching_feedback, conversational_response)
        """
        if not user_text or user_text.strip() == "":
            return ("No speech detected. Please try again with a clearer audio input.", "")

        try:
            # Build conversation context if history exists
            context_text = ""
            if conversation_history:
                context_text = "\n\nCONVERSATION CONTEXT (previous exchanges):\n"
                for i, turn in enumerate(conversation_history[-3:], 1):  # Last 3 turns for context
                    context_text += f"Turn {i}:\n"
                    context_text += f"  User: {turn['user']}\n"
                    context_text += f"  Your conversational response: {turn['conversational']}\n"
            
            prompt = f"""Analyze the user's speech and provide TWO separate responses.{context_text}

CURRENT USER INPUT: "{user_text}"

RESPONSE FORMAT (clearly separate both parts):
---COACHING---
Provide feedback on pronunciation, grammar, and naturalness. Keep it under 50 words. Be encouraging. Reference context if relevant.

---CONVERSATION---
Respond naturally to what the user said, as if you were their friend having a conversation. Use context from previous exchanges. Keep it natural and conversational (under 50 words).
"""
            
            response = ollama.chat(
                model=self.llm_name,
                messages=[
                    {'role': 'system', 'content': "You are an English tutor and friendly conversationalist. Maintain conversation continuity by referring to previous exchanges when relevant."},
                    {'role': 'user', 'content': prompt}
                ],
                stream=False
            )
            
            response_text = response['message']['content'].strip()
            
            # Parse the two sections
            coaching_feedback = ""
            conversational_response = ""
            
            if "---COACHING---" in response_text and "---CONVERSATION---" in response_text:
                # Split by the markers
                coaching_section = response_text.split("---COACHING---")[1].split("---CONVERSATION---")[0].strip()
                conversation_section = response_text.split("---CONVERSATION---")[1].strip()
                
                # Clean XML tags from both responses
                coaching_feedback = self._strip_xml_tags(coaching_section)
                conversational_response = self._strip_xml_tags(conversation_section)
            else:
                # Fallback: treat entire response as coaching if markers not found
                coaching_feedback = self._strip_xml_tags(response_text)
                conversational_response = "Thank you for sharing that!"
            
            return (coaching_feedback, conversational_response)
            
        except Exception as e:
            return (f"Error generating feedback: {str(e)}", "")

    async def synthesize_feedback(
        self,
        feedback_text: str,
        output_name: str,
        feedback_type: str = "coaching"
    ) -> str:
        """
        Step 3: Convert LLM feedback into audio for the user.
        
        Uses CoquiTTS for local, offline text-to-speech synthesis.
        
        Args:
            feedback_text: Text to synthesize into speech
            output_name: Session ID or unique identifier for output file
            feedback_type: Type of feedback ("coaching" or "conversational")
            
        Returns:
            Path to the generated WAV file
        """
        output_path = self.feedback_dir / f"{output_name}_{feedback_type}.wav"
        
        try:
            # Validate input
            if not feedback_text or len(feedback_text.strip()) == 0:
                raise ValueError("Feedback text cannot be empty")
            
            print(f"[TTS] Synthesizing {feedback_type} feedback ({len(feedback_text)} chars) to {output_path}")
            
            # Run CoquiTTS in a thread pool to avoid blocking the async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._synthesize_with_coqui, feedback_text, str(output_path))
            
            # Verify file was created
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"[TTS] Successfully created audio file: {output_path} ({output_path.stat().st_size} bytes)")
                return str(output_path)
            else:
                print(f"[TTS] ERROR: Audio file not created or empty at {output_path}")
                raise Exception("Audio file creation failed - file not written")
                
        except Exception as e:
            print(f"[TTS] ERROR: {str(e)}")
            raise Exception(f"TTS synthesis failed: {str(e)}")

    def _synthesize_with_coqui(self, text: str, output_file: str) -> None:
        """
        Helper method to run CoquiTTS synthesis with English-only configuration.
        Executed in a thread pool to avoid blocking.
        Non-English characters are filtered out before synthesis.
        
        Args:
            text: Text to synthesize
            output_file: Output file path
        """
        try:
            print(f"[TTS] Filtering text for English-only characters...")
            
            # Filter out non-English characters
            filtered_text = self._filter_english_only(text)
            
            if not filtered_text or len(filtered_text.strip()) == 0:
                raise ValueError("No English characters found in text after filtering")
            
            print(f"[TTS] Original length: {len(text)} | Filtered length: {len(filtered_text)}")
            print(f"[TTS] Initializing CoquiTTS engine (English model)...")
            
            # Initialize TTS model with English-only configuration
            # Using ljspeech model: English female voice, high quality
            tts = TTS(
                model_name="tts_models/en/ljspeech/glow-tts",
                gpu=False  # Set gpu=True if CUDA is available
            )
            
            print(f"[TTS] Speaking text: {filtered_text[:100]}...")
            
            # Generate speech with English-specific settings
            # Speed 1.5 = 50% faster than normal (speeds up TTS output)
            tts.tts_to_file(
                text=filtered_text,
                file_path=output_file,
                speed=1.5
            )
            
            print(f"[TTS] Speech synthesis completed (English-only mode)")
            
        except Exception as e:
            print(f"[TTS] Error in _synthesize_with_coqui: {str(e)}")
            raise

    async def process_user_input(
        self,
        input_audio_path: str,
        session_id: str
    ) -> FeedbackResponse:
        """
        Orchestration Pipeline: Coordinates STT -> LLM -> TTS.
        
        This is the main entry point for processing user audio input.
        Generates two types of responses:
        1. Coaching feedback on correctness and naturality
        2. Conversational response as if responding to a friend
        
        Args:
            input_audio_path: Path to user's recorded audio
            session_id: Unique session identifier
            
        Returns:
            FeedbackResponse with transcript, coaching, conversational, and audio paths
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        try:
            # Step 1: Speech to Text
            transcript = self.transcribe_speech(input_audio_path)
            
            # Step 2: Load conversation history for context
            conversation_history = self.get_conversation_history(session_id)
            
            # Step 3: Text to Coaching + Conversational (LLM with context)
            coaching_text, conversational_text = await self.get_linguistic_coaching(
                transcript,
                conversation_history
            )
            
            # Step 4: Both responses to Speech (TTS)
            coaching_audio_path = await self.synthesize_feedback(coaching_text, session_id, "coaching")
            conversational_audio_path = await self.synthesize_feedback(conversational_text, session_id, "conversational")
            
            # Step 5: Save this turn to conversation history
            self.save_conversation_turn(
                session_id,
                transcript,
                coaching_text,
                conversational_text
            )
            
            return FeedbackResponse(
                user_transcript=transcript,
                coaching_feedback=coaching_text,
                conversational_response=conversational_text,
                coaching_audio_path=coaching_audio_path,
                conversational_audio_path=conversational_audio_path
            )
        except FileNotFoundError as e:
            raise
        except Exception as e:
            raise Exception(f"Error processing user input: {str(e)}")

    async def health_check(self) -> dict:
        """
        Check the health and availability of all AI engines.
        
        Returns:
            Dictionary with status of each component
        """
        health = {
            "whisper": "unknown",
            "ollama": "unknown",
            "tts": "available"  # Edge-TTS doesn't require external service
        }
        
        # Check Whisper
        try:
            self.stt_engine  # Trigger lazy loading
            health["whisper"] = "available"
        except Exception as e:
            health["whisper"] = f"error: {str(e)}"
        
        # Check Ollama
        try:
            test_response = ollama.chat(
                model=self.llm_name,
                messages=[{'role': 'user', 'content': 'test'}],
                stream=False
            )
            health["ollama"] = "available"
        except Exception as e:
            health["ollama"] = f"error: {str(e)}"
        
        return health
