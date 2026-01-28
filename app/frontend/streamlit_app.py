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
        color: #000000;
    }
    .success-feedback {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        color: #000000;
    }
    .error-feedback {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        color: #000000;
    }
    .transcript-box {
        background-color: #FFF9E6;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #FFE082;
        margin: 10px 0;
        color: #000000;
    }
    .speaking-indicator {
        animation: pulse 1s infinite;
        display: inline-block;
        margin-left: 10px;
        color: #FF6B6B;
        font-weight: bold;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# JavaScript for Text-to-Speech (separate from CSS to ensure it loads first)
st.markdown("""
<script>
    // Initialize global variables
    if (typeof window.isSpeaking === 'undefined') {
        window.isSpeaking = false;
        window.currentUtterance = null;
    }
    
    // Text-to-Speech functionality using Web Speech API
    window.speakText = function(text, rate, pitch) {
        console.log('speakText called');
        console.log('Input - text length:', text.length, 'rate:', rate, 'pitch:', pitch);
        
        // Get the speech API (handle different browser prefixes)
        const speechSynthesis = window.speechSynthesis;
        const SpeechSynthesisUtterance = window.SpeechSynthesisUtterance || window.webkitSpeechSynthesisUtterance;
        
        // Check support
        if (!speechSynthesis || !SpeechSynthesisUtterance) {
            console.error('Web Speech API not supported in this browser');
            return false;
        }
        
        try {
            // Ensure we're working with a string
            const safeText = String(text || '');
            
            if (!safeText.trim()) {
                console.warn('Empty text provided to speakText');
                return false;
            }
            
            // Stop any ongoing speech
            console.log('Cancelling any ongoing speech');
            speechSynthesis.cancel();
            
            // Create utterance object
            const utterance = new SpeechSynthesisUtterance(safeText);
            
            // Set parameters with safety checks
            utterance.rate = Math.max(0.1, Math.min(10, parseFloat(rate) || 1.0));
            utterance.pitch = Math.max(0, Math.min(2, parseFloat(pitch) || 1.0));
            utterance.volume = 1.0;
            utterance.lang = 'en-US';
            
            console.log('Utterance configured:', {
                rate: utterance.rate,
                pitch: utterance.pitch,
                textLength: safeText.length
            });
            
            // Set event handlers
            utterance.onstart = function() {
                window.isSpeaking = true;
                console.log('Speech synthesis started');
            };
            
            utterance.onend = function() {
                window.isSpeaking = false;
                console.log('Speech synthesis ended');
            };
            
            utterance.onerror = function(event) {
                window.isSpeaking = false;
                console.error('Speech synthesis error:', event.error);
            };
            
            utterance.onpause = function() {
                console.log('Speech paused');
            };
            
            utterance.onresume = function() {
                console.log('Speech resumed');
            };
            
            // Store reference
            window.currentUtterance = utterance;
            
            // Start speaking
            console.log('Calling speechSynthesis.speak()');
            speechSynthesis.speak(utterance);
            
            console.log('Speech synthesis initiated successfully');
            return true;
            
        } catch (e) {
            console.error('Error in speakText:', e.message);
            console.error('Stack trace:', e.stack);
            return false;
        }
    };
    
    window.stopSpeech = function() {
        console.log('stopSpeech called');
        try {
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
                window.isSpeaking = false;
                console.log('Speech stopped');
                return true;
            }
        } catch (e) {
            console.error('Error stopping speech:', e);
            return false;
        }
    };
    
    window.checkSpeechSupport = function() {
        return !!(window.speechSynthesis && (window.SpeechSynthesisUtterance || window.webkitSpeechSynthesisUtterance));
    };
    
    // Log support status on load
    window.speechSupported = window.checkSpeechSupport();
    console.log('Speech Support Available:', window.speechSupported);
    console.log('Browser:', navigator.userAgent.substring(0, 80));
</script>
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
if 'speaking' not in st.session_state:
    st.session_state.speaking = False
if 'speech_rate' not in st.session_state:
    st.session_state.speech_rate = 1.0
if 'speech_pitch' not in st.session_state:
    st.session_state.speech_pitch = 1.0
if 'should_speak' not in st.session_state:
    st.session_state.should_speak = False
if 'should_stop' not in st.session_state:
    st.session_state.should_stop = False
if 'speak_text' not in st.session_state:
    st.session_state.speak_text = ""
if 'speak_rate' not in st.session_state:
    st.session_state.speak_rate = 1.0
if 'speak_pitch' not in st.session_state:
    st.session_state.speak_pitch = 1.0


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
        # Build the API URL
        url = f"{API_BASE_URL}/audio/{session_id}"
        
        # Try to get audio with timeout
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 404:
            # Audio file not found yet - backend might still be processing
            return None
        else:
            # Other error
            st.error(f"Audio retrieval error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        st.warning(f"Timeout waiting for audio from {API_BASE_URL}/audio/{session_id}")
        return None
    except Exception as e:
        st.error(f"Could not retrieve audio feedback: {str(e)}")
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
    
    # Speech Settings
    st.subheader("🔊 Speech Settings")
    
    st.session_state.speech_rate = st.slider(
        "Speech Rate",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.speech_rate,
        step=0.05,
        help="Adjust how fast the AI coach speaks (0.5 = very slow, 2.0 = very fast)"
    )
    
    st.session_state.speech_pitch = st.slider(
        "Voice Pitch",
        min_value=0.5,
        max_value=2.0,
        value=st.session_state.speech_pitch,
        step=0.05,
        help="Adjust voice pitch (0.5 = low, 2.0 = high)"
    )
    
    st.info(f"Current: Rate={st.session_state.speech_rate}, Pitch={st.session_state.speech_pitch}")
    
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
    - **TTS**: pyttsx3 (Local, Offline)
    """)
    
    st.divider()
    
    # Browser Support
    st.subheader("ℹ️ Browser Support")
    st.write("""
    **Speak Feedback** works on:
    - ✅ Chrome (v14+)
    - ✅ Firefox (v49+)
    - ✅ Safari (v14.1+)
    - ✅ Edge (v79+)
    - ❌ Internet Explorer
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
            
            st.divider()
            
            # Audio Feedback Player
            st.subheader("🎵 Listen to Feedback")
            
            if st.session_state.session_id:
                # Try to get audio with retry logic
                feedback_audio = get_feedback_audio(st.session_state.session_id)
                
                if feedback_audio:
                    # Display audio player with controls
                    st.audio(feedback_audio, format="audio/mp3")
                    st.success("✅ Click the play button above to hear the AI coach's feedback")
                else:
                    # Audio not ready - show status and retry button
                    st.warning("⏳ Audio feedback is being generated by the backend...")
                    
                    col_retry1, col_retry2 = st.columns([2, 1])
                    with col_retry1:
                        st.info("This may take a few seconds. Try refreshing the page or clicking the button below.")
                    with col_retry2:
                        if st.button("🔄 Retry", use_container_width=True, key="retry_audio"):
                            # Force rerun to check again
                            st.rerun()
                    
                    # Also add debugging info in expandable section
                    with st.expander("🔧 Debug Info"):
                        st.code(f"Session ID: {st.session_state.session_id}")
                        st.code(f"Audio Path: {st.session_state.audio_path if hasattr(st.session_state, 'audio_path') else 'Not set'}")
            else:
                st.info("No audio feedback available yet.")
            
            st.divider()
            
            # Alternative: Browser Speech API option
            st.subheader("🔊 Alternative: Browser Text-to-Speech")
            
            col_speak1, col_speak2 = st.columns(2)
            with col_speak1:
                if st.button("🔊 Speak with Browser Voice", use_container_width=True, key="speak_btn"):
                    st.session_state.should_speak = True
                    st.session_state.speak_text = st.session_state.feedback
                    st.session_state.speak_rate = st.session_state.speech_rate
                    st.session_state.speak_pitch = st.session_state.speech_pitch
            with col_speak2:
                if st.button("⏹️ Stop Speaking", use_container_width=True, key="stop_btn"):
                    st.session_state.should_stop = True
            
            st.caption("Adjust speech rate and pitch in the sidebar if using browser voice.")
            
            # Execute speech after button is set
            if st.session_state.get('should_speak', False):
                text = st.session_state.speak_text
                rate = float(st.session_state.speak_rate)
                pitch = float(st.session_state.speak_pitch)
                
                # Use JSON serialization for safe text encoding
                text_json = json.dumps(text)
                
                # Create a unique trigger ID to ensure script executes
                trigger_id = f"speak_{int(time.time() * 1000)}"
                
                st.markdown(f"""
                <script>
                    // Use a small delay to ensure proper browser context
                    setTimeout(function() {{
                        try {{
                            var feedbackText = {text_json};
                            var rate = {rate};
                            var pitch = {pitch};
                            
                            console.log('[{trigger_id}] Starting speech synthesis');
                            console.log('Text:', feedbackText.substring(0, 50) + '...');
                            console.log('Rate:', rate, 'Pitch:', pitch);
                            
                            // Verify speech API exists
                            if (!window.speechSynthesis) {{
                                console.error('speechSynthesis API not available');
                                alert('Speech API not available in your browser');
                                return;
                            }}
                            
                            // Verify speakText function exists
                            if (typeof window.speakText === 'function') {{
                                console.log('[{trigger_id}] Calling window.speakText()');
                                var result = window.speakText(feedbackText, rate, pitch);
                                console.log('[{trigger_id}] speakText returned:', result);
                            }} else {{
                                console.error('[{trigger_id}] speakText function not found!');
                                console.log('Window keys:', Object.keys(window).filter(k => k.includes('speak')).slice(0, 5));
                            }}
                        }} catch (error) {{
                            console.error('[{trigger_id}] Error:', error.message);
                            console.error('Stack:', error.stack);
                        }}
                    }}, 100);
                </script>
                """, unsafe_allow_html=True)
                
                # Show status to user
                st.info("🔊 Speaking feedback... (adjust speech rate/pitch in sidebar)")
                st.session_state.should_speak = False
            
            if st.session_state.get('should_stop', False):
                st.markdown("""
                <script>
                    (function() {{
                        try {{
                            console.log('Stopping speech');
                            if (typeof window.stopSpeech === 'function') {{
                                window.stopSpeech();
                                console.log('Speech stopped successfully');
                            }} else {{
                                console.error('stopSpeech function not found');
                            }}
                        }} catch (error) {{
                            console.error('Error stopping speech:', error);
                        }}
                    }})();
                </script>
                """, unsafe_allow_html=True)
                
                st.info("⏹️ Speech stopped.")
                st.session_state.should_stop = False
            
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
