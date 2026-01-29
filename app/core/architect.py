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
from pathlib import Path
import torch
import numpy as np
import wave
from typing import Optional, List, Dict, Tuple
import kokoro
import librosa
from app.models.schemas import FeedbackResponse
from app.core.config import (
    FEEDBACK_DIR,
    DEFAULT_WHISPER_MODEL,
    DEFAULT_LLM_NAME,
    DEFAULT_TTS_VOICE,
    SYSTEM_PROMPT,
    OLLAMA_BASE_URL,
)
from app.core.prompts import get_proactive_coaching_prompt, get_concise_feedback_prompt, PROACTIVE_CURIOSITY_SYSTEM_PROMPT, CONCISE_FEEDBACK_SYSTEM_PROMPT


class PhonicFlowArchitect:
    """
    Main orchestrator for the PhonicFlow AI tutor.
    
    Coordinates three AI engines:
    - Whisper (STT): Transcribes speech to text
    - Ollama (LLM): Analyzes and provides coaching
    - Kokoro (TTS): Synthesizes audio feedback with multilingual support
    """

    @staticmethod
    def _filter_english_only(text: str) -> str:
        """
        Filter text to keep only valid English and Brazilian Portuguese characters for TTS.
        Preserves letters, numbers, common punctuation, and safe Unicode characters.
        Removes HTML/XML tags and control characters.
        
        Args:
            text: Text potentially containing non-English or invalid characters
            
        Returns:
            Text with only valid English and Portuguese characters for TTS
        """
        if not text or not isinstance(text, str):
            return ""
        
        import unicodedata
        
        # Keep English letters, Brazilian Portuguese letters, numbers, spaces, and extended punctuation
        # Portuguese chars: ã, õ, ç, á, é, í, ó, ú, à, â, ô (and uppercase versions)
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "áéíóúàâôãõçÁÉÍÓÚÀÂÔÃÕÇ"
            "0123456789 .,;:!?'\"-()&\n\t"
        )
        
        # Also allow common Unicode punctuation and symbols that TTS can handle
        # Add: em-dash (—), en-dash (–), ellipsis (…), and curly quotes
        safe_unicode = {'—', '–', '…', '"', '"', ''', ''', '«', '»'}
        
        filtered = ""
        for char in text:
            if char in allowed_chars or char in safe_unicode:
                filtered += char
            elif char.isspace():  # Keep all whitespace
                filtered += char
        
        # Clean up multiple spaces and newlines
        filtered = re.sub(r'\s+', ' ', filtered)
        
        return filtered.strip()

    @staticmethod
    def _detect_speaker_gender(audio_file_path: str) -> str:
        """
        Estimate speaker gender from audio using fundamental frequency analysis.
        
        Male voices typically have lower fundamental frequency (80-180 Hz)
        Female voices typically have higher fundamental frequency (160-300 Hz)
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            'male' or 'female' based on estimated pitch
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_file_path, sr=None)
            
            # Extract fundamental frequency using piptrack algorithm
            # This is more robust than simple pitch detection
            f0 = librosa.yin(y, fmin=60, fmax=400, sr=sr)
            
            # Filter out unvoiced frames (f0 == 0)
            f0_voiced = f0[f0 > 0]
            
            if len(f0_voiced) == 0:
                print(f"[GENDER] No voiced frames detected, defaulting to female")
                return "female"
            
            # Calculate median fundamental frequency
            median_f0 = np.median(f0_voiced)
            mean_f0 = np.mean(f0_voiced)
            
            print(f"[GENDER] Median F0: {median_f0:.1f} Hz, Mean F0: {mean_f0:.1f} Hz")
            
            # Threshold: around 150 Hz separates male/female well
            # Below 150 Hz -> likely male, above 150 Hz -> likely female
            if median_f0 < 150:
                print(f"[GENDER] Detected as MALE (F0 < 150 Hz)")
                return "male"
            else:
                print(f"[GENDER] Detected as FEMALE (F0 >= 150 Hz)")
                return "female"
                
        except Exception as e:
            print(f"[GENDER] Error detecting gender: {str(e)}, defaulting to female")
            return "female"

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
            # Use concise, direct feedback prompt
            prompt = get_concise_feedback_prompt(user_text, conversation_history)
            
            response = ollama.chat(
                model=self.llm_name,
                messages=[
                    {'role': 'system', 'content': CONCISE_FEEDBACK_SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt}
                ],
                stream=False
            )
            
            response_text = response['message']['content'].strip()
            
            print(f"[LLM] Raw response from Ollama:\n{response_text[:200]}...\n")
            
            # Parse the two sections
            coaching_feedback = ""
            conversational_response = ""
            
            if "---COACHING---" in response_text and "---CONVERSATION---" in response_text:
                # Split by the markers
                coaching_section = response_text.split("---COACHING---")[1].split("---CONVERSATION---")[0].strip()
                conversation_section = response_text.split("---CONVERSATION---")[1].strip()
                
                print(f"[LLM] Coaching section extracted: {coaching_section[:100]}...")
                print(f"[LLM] Conversation section extracted: {conversation_section[:100]}...")
                
                # Clean XML tags from both responses
                coaching_feedback = self._strip_xml_tags(coaching_section)
                conversational_response = self._strip_xml_tags(conversation_section)
                
                print(f"[LLM] Coaching after XML cleanup: {coaching_feedback[:100]}...")
                print(f"[LLM] Conversation after XML cleanup: {conversational_response[:100]}...")
            else:
                # Fallback: treat entire response as coaching if markers not found
                print(f"[LLM] Markers not found. Response does not contain ---COACHING--- and ---CONVERSATION--- sections")
                coaching_feedback = self._strip_xml_tags(response_text)
                conversational_response = "Thank you for sharing that!"
            
            return (coaching_feedback, conversational_response)
            
        except Exception as e:
            return (f"Error generating feedback: {str(e)}", "")

    async def synthesize_feedback(
        self,
        feedback_text: str,
        output_name: str,
        feedback_type: str = "coaching",
        speaker_gender: str = "female"
    ) -> str:
        """
        Step 3: Convert LLM feedback into audio for the user.
        
        Uses Kokoro TTS for high-quality local text-to-speech synthesis with CUDA support.
        - Coaching feedback: Portuguese language
        - Conversational feedback: English language
        
        Selects gender-appropriate voices based on detected speaker gender.
        
        Args:
            feedback_text: Text to synthesize into speech
            output_name: Session ID or unique identifier for output file
            feedback_type: Type of feedback ("coaching" or "conversational")
            speaker_gender: Detected speaker gender ("male" or "female")
            
            Returns:
            Path to the generated WAV file
        """
        output_path = self.feedback_dir / f"{output_name}_{feedback_type}.wav"
        
        try:
            # Validate input
            if not feedback_text or len(feedback_text.strip()) == 0:
                raise ValueError("Feedback text cannot be empty")
            
            print(f"[TTS] Synthesizing {feedback_type} feedback ({len(feedback_text)} chars) to {output_path}")
            
            # Run Kokoro TTS in a thread pool to avoid blocking the async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._synthesize_with_kokoro, feedback_text, str(output_path), feedback_type, speaker_gender)
            
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

    def _synthesize_with_kokoro(self, text: str, output_file: str, feedback_type: str = "coaching", speaker_gender: str = "female") -> None:
        """
        Helper method to run Kokoro TTS synthesis with multilingual CUDA support.
        Executed in a thread pool to avoid blocking.
        - Coaching feedback: Portuguese language
        - Conversational feedback: English language
        - Voice selection: Male or female based on detected speaker gender
        
        Args:
            text: Text to synthesize
            output_file: Output file path
            feedback_type: Type of feedback ("coaching" for Portuguese, "conversational" for English)
            speaker_gender: Speaker gender ("male" or "female") for voice selection
        """
        try:
            print(f"[TTS] Original text: {text[:100]}...")
            print(f"[TTS] Original text length: {len(text)}")
            print(f"[TTS] Original text bytes: {text.encode('utf-8')[:100]}")
            
            # Filter out problematic characters (markdown, special chars, etc.)
            filtered_text = self._filter_english_only(text)
            
            if not filtered_text or len(filtered_text.strip()) == 0:
                raise ValueError(f"No valid characters found in text after filtering. Original: {text[:50]}")
            
            print(f"[TTS] Filtered text: {filtered_text[:100]}...")
            print(f"[TTS] Filtered text length: {len(filtered_text)}")
            
            if len(filtered_text) < len(text):
                print(f"[TTS] WARNING: Text was filtered from {len(text)} to {len(filtered_text)} chars")
                print(f"[TTS] Removed {len(text) - len(filtered_text)} characters")
            
            # Determine language code and voice based on feedback type and speaker gender
            if feedback_type == "coaching":
                lang_code = "p"      # Portuguese (Brazil)
                # Select Portuguese voice opposite to detected speaker gender
                if speaker_gender.lower() == "male":
                    voice = "pf_dora"     # Female voice (opposite of male speaker)
                    voice_name = "female (Dora)"
                else:
                    voice = "pm_alex"     # Male voice (opposite of female speaker)
                    voice_name = "male (Alex)"
                lang_name = "Portuguese"
            else:
                lang_code = "a"      # English (American)
                # Select English voice opposite to detected speaker gender
                if speaker_gender.lower() == "male":
                    voice = "af_heart"    # Female voice (opposite of male speaker)
                    voice_name = "female (Heart)"
                else:
                    voice = "am_michael"  # Male voice (opposite of female speaker)
                    voice_name = "male (Michael)"
                lang_name = "English"
            
            print(f"[TTS] Selected {lang_name} {voice_name} voice for {speaker_gender} speaker")
            
            print(f"[TTS] Initializing Kokoro TTS engine with CUDA support ({lang_name})...")
            
            # Check CUDA availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[TTS] Using device: {device}")
            if device == "cuda":
                print(f"[TTS] CUDA device: {torch.cuda.get_device_name(0)}")
            
            print(f"[TTS] Speaking text in {lang_name}: {filtered_text[:100]}...")
            
            # Create Kokoro pipeline and generate speech
            # Kokoro API: KPipeline(lang_code, device) returns generator of Results
            # Each result has .audio (torch tensor) and .phonemes
            pipeline = kokoro.KPipeline(lang_code=lang_code, device=device)
            
            # Collect audio from all results
            import wave
            with wave.open(output_file, "wb") as wav_file:
                wav_file.setnchannels(1)      # Mono audio
                wav_file.setsampwidth(2)      # 2 bytes per sample (16-bit audio)
                wav_file.setframerate(24000)  # Sample rate (Kokoro standard)
                
                # Generate speech - pipeline returns generator of results
                for result in pipeline(filtered_text, voice=voice, speed=1.0, split_pattern=r"\n+"):
                    if result.audio is None:
                        continue
                    # Convert torch tensor to numpy, then to 16-bit integer audio
                    audio_np = result.audio.numpy()
                    audio_int16 = (audio_np * 32767).astype(np.int16)
                    wav_file.writeframes(audio_int16.tobytes())
            
            print(f"[TTS] Speech synthesis completed successfully in {lang_name}")
            
        except Exception as e:
            print(f"[TTS] Error in _synthesize_with_kokoro: {str(e)}")
            print(f"[TTS] Attempted to synthesize: {text[:100]}")
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
        
        Automatically detects speaker gender from audio and selects appropriate
        male/female voices for TTS feedback synthesis.
        
        Args:
            input_audio_path: Path to user's recorded audio
            session_id: Unique session identifier
            
        Returns:
            FeedbackResponse with transcript, coaching, conversational, and audio paths
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        try:
            # Step 0: Detect speaker gender from audio
            speaker_gender = self._detect_speaker_gender(input_audio_path)
            print(f"[PIPELINE] Detected speaker gender: {speaker_gender}")
            
            # Step 1: Speech to Text
            transcript = self.transcribe_speech(input_audio_path)
            
            # Step 2: Load conversation history for context
            conversation_history = self.get_conversation_history(session_id)
            
            # Step 3: Text to Coaching + Conversational (LLM with context)
            coaching_text, conversational_text = await self.get_linguistic_coaching(
                transcript,
                conversation_history
            )
            
            # Step 4: Synthesize only the conversational response to speech (TTS in English)
            # Coaching feedback is provided as text only (in Portuguese)
            conversational_audio_path = await self.synthesize_feedback(conversational_text, session_id, "conversational", speaker_gender=speaker_gender)
            
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
