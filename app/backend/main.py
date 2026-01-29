"""
FastAPI backend for PhonicFlow.
Handles HTTP endpoints for audio processing, feedback generation, and health checks.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import uuid
import asyncio
from app.core.architect import PhonicFlowArchitect
from app.models.schemas import FeedbackResponse, ModelConfig
from app.core.config import (
    SERVER_HOST,
    SERVER_PORT,
    FEEDBACK_DIR,
    SUPPORTED_AUDIO_FORMATS,
)

# Initialize FastAPI app
app = FastAPI(
    title="PhonicFlow API",
    description="AI-powered English pronunciation and grammar tutor",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the PhonicFlow architect
architect = PhonicFlowArchitect()


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "PhonicFlow",
        "version": "1.0.0",
        "description": "AI English Tutor with Real-time Phonetic Analysis",
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
            "process": "/process"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Check the health of all AI components.
    
    Returns:
        - status: overall system status (operational/degraded/offline)
        - components: individual component status
    """
    component_health = await architect.health_check()
    
    # Determine overall status
    all_available = all(
        "available" in str(v) for v in component_health.values()
    )
    status = "operational" if all_available else "degraded"
    
    return {
        "status": status,
        "components": component_health
    }


@app.post("/process", tags=["Audio Processing"])
async def process_audio(
    file: UploadFile = File(...),
    session_id: str = None
):
    """
    Process user audio and generate phonetic coaching feedback.
    
    Args:
        file: Audio file (.wav, .mp3, .m4a, .flac)
        session_id: Optional session identifier (auto-generated if not provided)
        
    Returns:
        FeedbackResponse containing:
        - user_transcript: Transcribed speech
        - native_feedback: Coaching feedback from LLM
        - audio_feedback_path: Path to synthesized feedback audio
    """
    session_id = session_id or str(uuid.uuid4())
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lstrip(".").lower()
    if file_extension not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_extension}. "
                   f"Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
        )
    
    # Save uploaded file temporarily
    temp_audio_path = FEEDBACK_DIR / f"temp_{session_id}.{file_extension}"
    try:
        contents = await file.read()
        with open(temp_audio_path, "wb") as f:
            f.write(contents)
        
        # Process the audio through the pipeline
        feedback = await architect.process_user_input(
            str(temp_audio_path),
            session_id
        )
        
        return feedback
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Clean up temporary audio file
        if temp_audio_path.exists():
            try:
                os.remove(temp_audio_path)
            except:
                pass


@app.get("/audio/{session_id}", tags=["Audio Processing"])
async def get_feedback_audio(session_id: str, audio_type: str = "conversational"):
    """
    Retrieve synthesized audio for a session.
    
    Args:
        session_id: Session identifier
        audio_type: Type of audio to retrieve (only "conversational" is supported)
        
    Returns:
        WAV audio file with synthesized conversational feedback
    """
    # Only conversational audio is synthesized
    if audio_type != "conversational":
        raise HTTPException(
            status_code=400,
            detail=f"Only 'conversational' audio type is supported. Coaching feedback is provided as text only."
        )
    
    audio_path = FEEDBACK_DIR / f"{session_id}_{audio_type}.wav"
    
    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Audio not found for session {session_id}"
        )
    
    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=f"feedback_{session_id}_{audio_type}.wav"
    )


@app.get("/conversation/{session_id}", tags=["Conversation"])
async def get_conversation_history(session_id: str):
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of conversation turns with user input and AI responses
    """
    history = architect.get_conversation_history(session_id)
    return {
        "session_id": session_id,
        "conversation_count": len(history),
        "history": history
    }


@app.delete("/conversation/{session_id}", tags=["Conversation"])
async def clear_conversation_history(session_id: str):
    """
    Clear conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Confirmation of cleared history
    """
    success = architect.clear_conversation_history(session_id)
    return {
        "status": "success" if success else "failed",
        "session_id": session_id,
        "message": "Conversation history cleared"
    }


@app.post("/config", tags=["Configuration"])
async def update_config(config: ModelConfig):
    """
    Update model configuration (Whisper model, LLM, TTS voice).
    
    Args:
        config: ModelConfig with updated settings
        
    Returns:
        Confirmation of updated settings
    """
    architect.whisper_model = config.whisper_model
    architect.llm_name = config.llm_name
    architect.tts_voice = config.tts_voice
    
    # Reset cached models
    architect._stt_engine = None
    
    return {
        "status": "configuration updated",
        "settings": {
            "whisper_model": architect.whisper_model,
            "llm_name": architect.llm_name,
            "tts_voice": architect.tts_voice
        }
    }


@app.get("/config", tags=["Configuration"])
async def get_config():
    """Get current model configuration."""
    return {
        "whisper_model": architect.whisper_model,
        "llm_name": architect.llm_name,
        "tts_voice": architect.tts_voice
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True
    )
