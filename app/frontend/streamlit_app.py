"""
PhonicFlow - AI English Tutor with Chat Interface
Main Streamlit application for interactive pronunciation feedback.
"""
import streamlit as st
import requests
import json
import time
import os
import re
from pathlib import Path

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
AUDIO_FORMAT = "audio/wav"

def strip_xml_tags(text: str) -> str:
    """
    Remove XML/HTML tags from text while preserving content.
    Handles various XML formats including nested tags and HTML entities.
    
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
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Clean up any extra whitespace that might result
    cleaned = ' '.join(text.split())
    
    return cleaned.strip()

# Streamlit page configuration
st.set_page_config(
    page_title="PhonicFlow - English Tutor",
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
    
    /* Chat-style messaging */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
        padding: 10px 0;
    }
    
    .chat-message {
        display: flex;
        gap: 10px;
        margin: 8px 0;
        padding: 12px;
        border-radius: 8px;
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background-color: #E3F2FD;
        margin-left: 20px;
        border-left: 4px solid #2196F3;
        color: #000000;
    }
    
    .ai-message {
        background-color: #F5F5F5;
        margin-right: 20px;
        border-left: 4px solid #4CAF50;
        color: #000000;
    }
    
    .message-label {
        font-weight: bold;
        font-size: 0.85em;
        margin-bottom: 4px;
        opacity: 0.8;
    }
    
    .message-content {
        font-size: 0.95em;
        line-height: 1.4;
    }
    
    .coaching-section {
        background-color: #FFF8E1;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #FBC02D;
        margin: 10px 0;
        color: #000000;
    }
    
    .coaching-title {
        font-weight: bold;
        color: #F57F17;
        margin-bottom: 8px;
        font-size: 0.95em;
    }
    
    .transcript-box {
        background-color: #FFF9E6;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #FFE082;
        margin: 10px 0;
        color: #000000;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time() * 1000)}"
    st.session_state.transcript = None
    st.session_state.coaching_feedback = None
    st.session_state.conversational_response = None
    st.session_state.coaching_audio_path = None
    st.session_state.conversational_audio_path = None
    st.session_state.speech_rate = 1.0
    st.session_state.speech_pitch = 1.0
    st.session_state.last_audio_id = None

# Helper functions
def get_feedback_audio(session_id: str, audio_type: str = "coaching"):
    """Retrieve synthesized audio from the backend."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/audio/{session_id}",
            params={"audio_type": audio_type},
            timeout=15
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.error(f"Error loading audio: {str(e)}")
        return None

def get_conversation_history(session_id: str):
    """Fetch conversation history from backend with retries."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/conversation/{session_id}",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            history = data.get("history", [])
            
            # Clean XML tags from all conversational responses
            for turn in history:
                if 'conversational' in turn:
                    turn['conversational'] = strip_xml_tags(turn['conversational'])
                if 'coaching' in turn:
                    turn['coaching'] = strip_xml_tags(turn['coaching'])
            
            print(f"[DEBUG] Backend returned {len(history)} history items")
            return history
        else:
            print(f"[DEBUG] Backend error: {response.status_code}")
            return []
    except Exception as e:
        print(f"[DEBUG] Error fetching conversation history: {str(e)}")
        return []

# Header
st.markdown('<div class="main-title">🎤 PhonicFlow</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Your Personal English Pronunciation Coach</div>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("📊 Speech Control")
    st.session_state.speech_rate = st.slider(
        "Speech Rate",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.speech_rate,
        step=0.1
    )
    st.session_state.speech_pitch = st.slider(
        "Speech Pitch",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.speech_pitch,
        step=0.1
    )
    
    st.subheader("ℹ️ About")
    st.info(
        "**PhonicFlow** uses AI to help you improve your English pronunciation. "
        "Record your speech, and get personalized coaching from your AI tutor!"
    )
    
    st.subheader("🔧 Session Info")
    st.code(st.session_state.session_id, language="")

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🎤 Record Audio")
    
    # Audio recording widget
    audio_data = st.audio_input("Click to record your speech", label_visibility="collapsed")
    
    # Track if we've already processed this audio to avoid loops
    if audio_data and not st.session_state.get("last_audio_id"):
        st.success("✅ Audio recorded!")
        
        # Process audio
        with st.spinner("Processing your speech... This may take 15-25 seconds"):
            try:
                # Handle audio_data properly (might be bytes or file-like object)
                if hasattr(audio_data, 'read'):
                    # File-like object
                    audio_bytes = audio_data.read()
                elif isinstance(audio_data, bytes):
                    # Raw bytes
                    audio_bytes = audio_data
                else:
                    # Try to convert to bytes
                    audio_bytes = bytes(audio_data)
                
                # Save audio to temporary file
                audio_path = "/tmp/user_audio.wav"
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                
                # Send to backend
                with open(audio_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    
                    # Send session_id as query parameter
                    response = requests.post(
                        f"{API_BASE_URL}/process",
                        params={"session_id": st.session_state.session_id},
                        files=files,
                        timeout=60
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Store results in session state (clean XML tags if present)
                    st.session_state.transcript = result.get("user_transcript", "")
                    st.session_state.coaching_feedback = strip_xml_tags(result.get("coaching_feedback", ""))
                    st.session_state.conversational_response = strip_xml_tags(result.get("conversational_response", ""))
                    st.session_state.coaching_audio_path = result.get("coaching_audio_path", "")
                    st.session_state.conversational_audio_path = result.get("conversational_audio_path", "")
                    
                    # Mark this audio as processed to prevent loop
                    st.session_state.last_audio_id = id(audio_data)
                    
                    st.success("✅ Feedback generated!")
                    st.info(f"Backend returned: {len(result)} fields")
                    
                    # Display results immediately in this run
                    with st.expander("📊 Current Results", expanded=True):
                        st.write("**Your Speech:**", st.session_state.transcript)
                        st.write("**Coaching Feedback:**", st.session_state.coaching_feedback)
                        st.write("**Conversational Response:**", st.session_state.conversational_response)
                    
                    time.sleep(1)  # Brief pause to show results
                    st.rerun()
                else:
                    st.error(f"Backend error: {response.status_code}")
                    st.error(response.text)
            
            except Exception as e:
                st.error(f"Error processing audio: {str(e)}")

with col2:
    st.subheader("💬 Conversation Thread")
    
    # Load and display conversation history as chat
    history = get_conversation_history(st.session_state.session_id)
    
    # Debug info
    st.caption(f"Session: {st.session_state.session_id[-8:]}... | History items: {len(history)}")
    
    if history:
        chat_html = '<div class="chat-container">'
        
        for turn in history:
            user_input = turn.get('user', 'N/A')
            conversational = strip_xml_tags(turn.get('conversational', 'N/A'))
            
            # User message
            chat_html += f'''
            <div class="chat-message user-message">
                <div style="flex: 1;">
                    <div class="message-label">You</div>
                    <div class="message-content">{user_input}</div>
                </div>
            </div>
            '''
            
            # AI conversational message
            if conversational and conversational != 'N/A':
                chat_html += f'''
                <div class="chat-message ai-message">
                    <div style="flex: 1;">
                        <div class="message-label">Assistant</div>
                        <div class="message-content">{conversational}</div>
                    </div>
                </div>
                '''
        
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.warning("⏳ No conversation history yet. If you just recorded audio, the backend may still be processing it.")
    
    st.divider()
    
    # Coaching feedback section
    st.subheader("📋 Coaching & Learning")
    
    if history:
        for i, turn in enumerate(history, 1):
            coaching = turn.get('coaching', None)
            if coaching:
                with st.expander(f"Turn {i} - Coaching Tips", expanded=i==len(history)):
                    st.markdown(f'''
                    <div class="coaching-section">
                    <div class="coaching-title">Phonetic Corrections & Pronunciation Tips</div>
                    {coaching}
                    </div>
                    ''', unsafe_allow_html=True)
    else:
        st.info("💡 Record audio to receive personalized coaching tips.")
    
    st.divider()
    
    # Audio playback section
    st.subheader("🔊 Audio Playback")
    
    col_audio1, col_audio2 = st.columns(2)
    
    with col_audio1:
        st.caption("💬 Conversational Response")
        try:
            conv_audio = get_feedback_audio(st.session_state.session_id, "conversational")
            if conv_audio:
                st.audio(conv_audio, format="audio/mp3")
            else:
                st.info("No conversational audio yet")
        except:
            st.info("Loading audio...")
    
    with col_audio2:
        st.caption("📝 Coaching Audio")
        try:
            coaching_audio = get_feedback_audio(st.session_state.session_id, "coaching")
            if coaching_audio:
                st.audio(coaching_audio, format="audio/mp3")
            else:
                st.info("No coaching audio yet")
        except:
            st.info("Loading audio...")
    
    st.divider()
    
    # Conversation management
    st.subheader("⚙️ Manage Conversation")
    
    col_manage1, col_manage2 = st.columns(2)
    
    with col_manage1:
        if st.button("🗑️ Clear History", use_container_width=True, key="clear_history"):
            try:
                response = requests.delete(
                    f"{API_BASE_URL}/conversation/{st.session_state.session_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    st.success("✅ History cleared!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with col_manage2:
        if st.button("🔄 New Chat", use_container_width=True, key="new_conversation"):
            st.session_state.session_id = f"session_{int(time.time() * 1000)}"
            st.session_state.transcript = None
            st.session_state.coaching_feedback = None
            st.session_state.conversational_response = None
            st.session_state.last_audio_id = None  # Reset audio ID to allow new recording
            st.success("✅ New conversation!")
            st.rerun()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9em; margin-top: 20px;">
    <p>PhonicFlow v2.0 | Chat Interface | Powered by OpenAI Whisper, Ollama, and pyttsx3</p>
    <p>Made with ❤️ for English learners worldwide</p>
</div>
""", unsafe_allow_html=True)
