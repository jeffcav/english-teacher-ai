"""
Streamlit frontend for PhonicFlow.
Provides user interface for recording audio, submitting for analysis, and receiving feedback.
"""
import streamlit as st
import requests
import os
import io
import json
from pathlib import Path
from datetime import datetime
import time

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="PhonicFlow - AI English Tutor",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-title {
        font-size: 3em;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 10px;
    }
    .subtitle {
        font-size: 1.2em;
        color: #666;
        text-align: center;
        margin-bottom: 30px;
    }
    .feedback-card {
        background-color: #F0F4F8;
        border-left: 4px solid #2E86AB;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-feedback {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
    }
    .error-feedback {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
    }
    .transcript-box {
        background-color: #FFF9E6;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #FFE082;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'api_status' not in st.session_state:
    st.session_state.api_status = None


def check_api_health():
    """Check if API is operational."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        st.session_state.api_status = response.json() if response.status_code == 200 else None
        return response.status_code == 200
    except Exception as e:
        st.session_state.api_status = None
        return False


def process_audio(audio_bytes, session_id):
    """Send audio file to backend for processing."""
    try:
        files = {
            "file": ("recording.wav", audio_bytes, "audio/wav")
        }
        params = {"session_id": session_id}
        
        response = requests.post(
            f"{API_BASE_URL}/process",
            files=files,
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.Timeout:
        st.error("Request timeout. Processing took too long. Try a shorter audio clip.")
        return None
    except Exception as e:
        st.error(f"Error processing audio: {str(e)}")
        return None


def get_feedback_audio(session_id):
    """Retrieve synthesized feedback audio from backend."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/audio/{session_id}",
            timeout=10
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.warning(f"Could not retrieve audio feedback: {str(e)}")
        return None


# Header
st.markdown('<div class="main-title">🎤 PhonicFlow</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Master English Pronunciation with AI Coaching</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Status
    if st.button("Check API Status", use_container_width=True):
        with st.spinner("Checking API status..."):
            is_healthy = check_api_health()
            if is_healthy:
                st.success("✅ API is operational")
                if st.session_state.api_status:
                    st.json(st.session_state.api_status)
            else:
                st.error("❌ API is not accessible")
                st.info(f"Make sure the backend is running at: {API_BASE_URL}")
    
    st.divider()
    
    # Information
    st.subheader("📖 About PhonicFlow")
    st.write("""
    PhonicFlow is an AI-powered English tutor that helps you master:
    - **Pronunciation**: Accurate phonetic analysis
    - **Grammar**: Real-time correction and suggestions
    - **Fluency**: Native-level expression patterns
    
    Simply record yourself speaking, and get instant AI coaching!
    """)
    
    st.divider()
    
    # Model Info
    st.subheader("🤖 AI Models")
    st.write("""
    - **STT**: OpenAI Whisper
    - **Coach**: Llama 3 / Mistral
    - **TTS**: Edge-TTS (Microsoft)
    """)

# Main content
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("🎙️ Record Your Voice")
    st.write("Speak a sentence or phrase in English. The AI will analyze your pronunciation and grammar.")
    
    # Audio input
    audio_data = st.audio_input(
        "Click the microphone to record (or upload an audio file)",
        label_visibility="collapsed"
    )
    
    if audio_data:
        st.success("✅ Audio captured!")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("📤 Analyze Audio", use_container_width=True, type="primary"):
                if not check_api_health():
                    st.error("❌ API is not accessible. Please ensure the backend is running.")
                else:
                    with st.spinner("Processing your speech..."):
                        # Generate session ID
                        session_id = f"session_{int(time.time() * 1000)}"
                        st.session_state.session_id = session_id
                        
                        # Get audio bytes
                        audio_bytes = audio_data.getvalue()
                        
                        # Process audio
                        result = process_audio(audio_bytes, session_id)
                        
                        if result:
                            st.session_state.transcript = result.get("user_transcript")
                            st.session_state.feedback = result.get("native_feedback")
                            st.session_state.audio_path = result.get("audio_feedback_path")
                            st.success("✅ Analysis complete!")
        
        with col_b:
            if st.button("🔄 Clear & Retry", use_container_width=True):
                st.session_state.transcript = None
                st.session_state.feedback = None
                st.session_state.session_id = None
                st.rerun()

with col2:
    st.subheader("💡 AI Coaching Feedback")
    
    if st.session_state.transcript is not None:
        st.write("**Your Speech (Transcribed):**")
        st.markdown(f'<div class="transcript-box">{st.session_state.transcript}</div>', unsafe_allow_html=True)
        
        if st.session_state.feedback:
            st.write("**Native Speaker Coaching:**")
            st.markdown(f'<div class="feedback-card success-feedback">{st.session_state.feedback}</div>', unsafe_allow_html=True)
            
            # Try to get and play audio feedback
            if st.session_state.session_id:
                feedback_audio = get_feedback_audio(st.session_state.session_id)
                if feedback_audio:
                    st.write("**Listen to Feedback (AI Voice):**")
                    st.audio(feedback_audio, format="audio/mp3")
        else:
            st.info("⏳ Generating coaching feedback...")
    else:
        st.info("👆 Record audio above to get started!")

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9em; margin-top: 20px;">
    <p>PhonicFlow v1.0 | Powered by OpenAI Whisper, Ollama, and Edge-TTS</p>
    <p>Made with ❤️ for English learners worldwide</p>
</div>
""", unsafe_allow_html=True)
