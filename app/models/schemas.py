"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel
from typing import Optional


class FeedbackResponse(BaseModel):
    """Response model for phonetic coaching feedback."""
    user_transcript: str
    native_feedback: str
    audio_feedback_path: str


class ProcessingRequest(BaseModel):
    """Request model for audio processing."""
    session_id: str
    audio_file_path: str


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    components: dict


class ModelConfig(BaseModel):
    """Configuration for model selection."""
    whisper_model: str = "base.en"
    llm_name: str = "llama3"
    tts_voice: str = "en-US-AndrewNeural"
