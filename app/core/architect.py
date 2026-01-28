"""
PhonicFlowArchitect: Core orchestration engine for the AI tutor pipeline.
Manages STT, LLM coaching, and TTS synthesis.
"""
import os
import asyncio
import whisper
import ollama
import pyttsx3
from pathlib import Path
from typing import Optional
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
    - Edge-TTS (TTS): Synthesizes audio feedback
    """

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

    async def get_linguistic_coaching(self, user_text: str) -> str:
        """
        Step 2: Use Ollama to analyze transcription and provide coaching.
        
        The LLM analyzes the transcribed text for:
        - Pronunciation errors (inferred from spelling)
        - Grammar and syntax issues
        - Idiomatic alternatives
        
        Args:
            user_text: Transcribed speech from user
            
        Returns:
            Linguistic coaching feedback (< 60 words)
        """
        if not user_text or user_text.strip() == "":
            return "No speech detected. Please try again with a clearer audio input."

        try:
            response = ollama.chat(
                model=self.llm_name,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': f"User said: {user_text}"}
                ],
                stream=False
            )
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error generating feedback: {str(e)}"

    async def synthesize_feedback(
        self,
        feedback_text: str,
        output_name: str
    ) -> str:
        """
        Step 3: Convert LLM feedback into audio for the user.
        
        Uses pyttsx3 for local, offline text-to-speech synthesis.
        
        Args:
            feedback_text: Text to synthesize into speech
            output_name: Session ID or unique identifier for output file
            
        Returns:
            Path to the generated MP3 file
        """
        output_path = self.feedback_dir / f"{output_name}.mp3"
        
        try:
            # Validate input
            if not feedback_text or len(feedback_text.strip()) == 0:
                raise ValueError("Feedback text cannot be empty")
            
            print(f"[TTS] Synthesizing feedback ({len(feedback_text)} chars) to {output_path}")
            
            # Run pyttsx3 in a thread pool to avoid blocking the async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._synthesize_with_pyttsx3, feedback_text, str(output_path))
            
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

    def _synthesize_with_pyttsx3(self, text: str, output_file: str) -> None:
        """
        Helper method to run pyttsx3 synthesis.
        Executed in a thread pool to avoid blocking.
        
        Args:
            text: Text to synthesize
            output_file: Output file path
        """
        import time
        
        engine = None
        try:
            print(f"[TTS] Initializing pyttsx3 engine...")
            
            # Create a fresh engine instance
            engine = pyttsx3.init()
            
            # Configure voice and speech parameters
            engine.setProperty('rate', 150)      # Speech rate (words per minute)
            engine.setProperty('volume', 1.0)    # Volume (0.0 to 1.0)
            
            # Try to set a voice (optional)
            try:
                voices = engine.getProperty('voices')
                if voices:
                    print(f"[TTS] Available voices: {len(voices)}")
                    engine.setProperty('voice', voices[0].id)
                    print(f"[TTS] Using voice: {voices[0].name}")
            except Exception as voice_error:
                print(f"[TTS] Warning: Could not set voice - {voice_error}")
            
            print(f"[TTS] Saving to file: {output_file}")
            
            # Save to file
            engine.save_to_file(text, output_file)
            
            print(f"[TTS] Running engine...")
            engine.runAndWait()
            
            # Give callbacks time to complete before cleaning up
            time.sleep(0.5)
            
            print(f"[TTS] Engine completed")
            
        except Exception as e:
            print(f"[TTS] Error in _synthesize_with_pyttsx3: {str(e)}")
            raise
        finally:
            # Ensure proper cleanup
            if engine is not None:
                try:
                    engine.stop()
                except:
                    pass

    async def process_user_input(
        self,
        input_audio_path: str,
        session_id: str
    ) -> FeedbackResponse:
        """
        Orchestration Pipeline: Coordinates STT -> LLM -> TTS.
        
        This is the main entry point for processing user audio input.
        
        Args:
            input_audio_path: Path to user's recorded audio
            session_id: Unique session identifier
            
        Returns:
            FeedbackResponse with transcript, coaching, and audio feedback
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        try:
            # Step 1: Speech to Text
            transcript = self.transcribe_speech(input_audio_path)
            
            # Step 2: Text to Coaching (LLM)
            coaching_text = await self.get_linguistic_coaching(transcript)
            
            # Step 3: Coaching to Speech (TTS)
            audio_path = await self.synthesize_feedback(coaching_text, session_id)
            
            return FeedbackResponse(
                user_transcript=transcript,
                native_feedback=coaching_text,
                audio_feedback_path=audio_path
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
