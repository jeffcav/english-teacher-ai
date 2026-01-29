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
    initial_sidebar_state="collapsed"
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
    
    /* Chat-style messaging - WhatsApp/Telegram style */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 15px 10px;
        max-width: 100%;
        background-color: #F0F2F5;
        border-radius: 10px;
        min-height: 300px;
        overflow-y: auto;
    }
    
    .chat-message {
        display: flex;
        margin: 5px 0;
        animation: fadeIn 0.3s ease-in;
        word-wrap: break-word;
        max-width: 85%;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        align-self: flex-end;
        margin-left: auto;
        margin-right: 0;
    }
    
    .user-message .message-bubble {
        background-color: #DCF8C6;
        color: #000000;
        border-radius: 18px 4px 18px 18px;
        padding: 10px 14px;
        box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
    }
    
    .ai-message {
        align-self: flex-start;
        margin-right: auto;
        margin-left: 0;
    }
    
    .ai-message .message-bubble {
        background-color: #FFFFFF;
        color: #000000;
        border-radius: 4px 18px 18px 18px;
        padding: 10px 14px;
        box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E0E0E0;
    }
    
    .message-bubble {
        font-size: 0.95em;
        line-height: 1.4;
        word-break: break-word;
    }
    
    .message-label {
        font-weight: 600;
        font-size: 0.8em;
        margin-bottom: 3px;
        opacity: 0.7;
        padding: 0 14px;
        margin-top: 5px;
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
    st.session_state.conversational_audio_path = None
    st.session_state.coaching_feedback_portuguese = None
    st.session_state.conversational_response_portuguese = None
    st.session_state.last_processed_audio_hash = None  # Track hash of last processed audio

def compute_audio_hash(audio_data) -> str:
    """Compute a hash of audio data to detect if it's new."""
    import hashlib
    try:
        # Convert to bytes if needed
        if hasattr(audio_data, 'read'):
            # File-like object - read bytes and seek back to beginning
            audio_bytes = audio_data.read()
            if hasattr(audio_data, 'seek'):
                audio_data.seek(0)  # Reset file pointer for later use
        elif isinstance(audio_data, bytes):
            audio_bytes = audio_data
        else:
            audio_bytes = bytes(audio_data)
        
        return hashlib.md5(audio_bytes).hexdigest()
    except Exception as e:
        print(f"[DEBUG] Error computing audio hash: {str(e)}")
        return None

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
            for i, turn in enumerate(history):
                if 'conversational' in turn:
                    original = turn['conversational']
                    cleaned = strip_xml_tags(original)
                    if original != cleaned:
                        print(f"[DEBUG] Turn {i} conversational: cleaned XML from {len(original)} to {len(cleaned)} chars")
                    turn['conversational'] = cleaned
                if 'coaching' in turn:
                    original = turn['coaching']
                    cleaned = strip_xml_tags(original)
                    if original != cleaned:
                        print(f"[DEBUG] Turn {i} coaching: cleaned XML from {len(original)} to {len(cleaned)} chars")
                    turn['coaching'] = cleaned
            
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

st.divider()

# Top section with recording and audio playback side by side
top_col1, top_col2 = st.columns([1, 1])

with top_col1:
    st.subheader("🎤 Record Audio")
    
    # Audio recording widget
    audio_data = st.audio_input("Click to record your speech", label_visibility="collapsed")
    
    # Check if we have NEW audio (different from the last one we processed)
    should_process = False
    current_audio_hash = None
    
    if audio_data:
        current_audio_hash = compute_audio_hash(audio_data)
        if current_audio_hash and current_audio_hash != st.session_state.last_processed_audio_hash:
            should_process = True
    
    if should_process:
        # Mark this audio as being processed IMMEDIATELY to prevent re-processing on rerun
        st.session_state.last_processed_audio_hash = current_audio_hash
        
        # Process audio silently in background
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
                st.session_state.conversational_audio_path = result.get("conversational_audio_path", "")
                st.session_state.coaching_feedback_portuguese = result.get("coaching_feedback_portuguese", "")
                st.session_state.conversational_response_portuguese = result.get("conversational_response_portuguese", "")
                
                st.rerun()
        
        except Exception as e:
            pass

with top_col2:
    st.subheader("🔊 Audio Playback")
    
    st.caption("💬 Conversational Response")
    conv_audio = get_feedback_audio(st.session_state.session_id, "conversational")
    if conv_audio:
        st.audio(conv_audio, format="audio/wav", autoplay=True)
    else:
        st.info("Audio not available yet")
    
    st.divider()
    
    # Conversation management buttons
    col_manage1, col_manage2 = st.columns(2)
    
    with col_manage1:
        if st.button("🗑️ Clear History", use_container_width=True, key="clear_history"):
            try:
                response = requests.delete(
                    f"{API_BASE_URL}/conversation/{st.session_state.session_id}",
                    timeout=5
                )
                if response.status_code == 200:
                    st.rerun()
            except:
                pass
    
    with col_manage2:
        if st.button("🔄 New Chat", use_container_width=True, key="new_conversation"):
            st.session_state.session_id = f"session_{int(time.time() * 1000)}"
            st.session_state.transcript = None
            st.session_state.coaching_feedback = None
            st.session_state.conversational_response = None
            st.session_state.last_processed_audio_hash = None
            st.rerun()

st.divider()

# Main content - conversation takes full width
st.subheader("💬 Conversation Thread")

# Load and display conversation history as chat
history = get_conversation_history(st.session_state.session_id)

if history:
    chat_html = '<div class="chat-container">'
    
    for i, turn in enumerate(history):
        user_input = turn.get('user', 'N/A')
        conversational = turn.get('conversational', 'N/A')
        
        # Clean XML tags from both messages
        user_input = strip_xml_tags(user_input) if user_input != 'N/A' else user_input
        conversational = strip_xml_tags(conversational) if conversational != 'N/A' else conversational
        
        # Escape HTML special characters to prevent rendering issues
        user_input_escaped = (user_input
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
        
        conversational_escaped = (conversational
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
        
        # User message (right-aligned bubble)
        chat_html += f'''<div class="chat-message user-message"><div class="message-bubble">{user_input_escaped}</div></div>'''
        
        # AI conversational message (left-aligned bubble)
        if conversational and conversational != 'N/A':
            chat_html += f'''<div class="chat-message ai-message"><div class="message-bubble">{conversational_escaped}</div></div>'''
    
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

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

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.9em; margin-top: 20px;">
    <p>PhonicFlow v2.0 | Chat Interface | Powered by OpenAI Whisper, Ollama, and pyttsx3</p>
    <p>Made with ❤️ for English learners worldwide</p>
</div>
""", unsafe_allow_html=True)
