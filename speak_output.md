# PhonicFlow: Text-to-Speech Output Feature Development Plan

## 📋 Overview

This document outlines the development plan for implementing a "Speak Output" functionality that allows users to click a button and hear the coach's feedback spoken aloud through their browser/system audio.

---

## 🎯 Objective

Enable users to hear the AI coach's text feedback read aloud with natural speech synthesis, providing immediate auditory reinforcement of the coaching suggestions.

---

## 📊 Current State Analysis

### What Already Exists
1. **Backend TTS Synthesis** (`app/core/architect.py`)
   - Edge-TTS synthesizes coach feedback to MP3
   - Files stored in `app/feedback_storage/{session_id}.mp3`

2. **Frontend Audio Playback** (`app/frontend/streamlit_app.py`)
   - `st.audio()` widget displays audio player
   - Users can manually play/pause synthesized feedback

### Gap
- No dedicated "Speak Now" button
- Audio must be downloaded from backend first
- Dependency on Edge-TTS (requires internet for some voices)
- No browser-native fallback

---

## 🛠️ Implementation Approaches

### Option A: Browser Web Speech API (Recommended)
**Pros:**
- No backend dependency
- Instant speech synthesis
- Works offline
- Lower latency
- Customizable speech rate/pitch

**Cons:**
- Limited voice options
- Browser-dependent quality
- No persistent audio file

**Complexity:** ⭐⭐ (Low-Medium)

### Option B: Enhanced Backend Audio Playback
**Pros:**
- Consistent voice quality across users
- Professional audio output
- Can be cached/reused

**Cons:**
- Requires backend processing
- Network latency
- Higher resource usage

**Complexity:** ⭐⭐⭐ (Medium)

### Option C: Hybrid Approach
**Pros:**
- Use browser API as primary
- Fall back to backend audio if unavailable
- Best of both worlds

**Cons:**
- More complex implementation
- Requires error handling

**Complexity:** ⭐⭐⭐⭐ (Medium-High)

---

## 🔧 Recommended Solution: Option A + Hybrid

Implement browser Web Speech API as primary method with optional backend fallback.

---

## 📝 Detailed Development Plan

### Phase 1: Frontend Enhancement (Streamlit)

#### 1.1 Add JavaScript for Speech Synthesis
**File:** `app/frontend/streamlit_app.py`

**Changes:**
```python
# Add custom HTML/JavaScript for speech synthesis
st.markdown("""
<script>
    function speakText(text) {
        // Check if browser supports Web Speech API
        const SpeechSynthesisUtterance = window.SpeechSynthesisUtterance || 
                                         window.webkitSpeechSynthesisUtterance;
        
        if (!SpeechSynthesisUtterance) {
            alert('Text-to-Speech not supported in your browser');
            return;
        }
        
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();
        
        // Create utterance
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure speech parameters
        utterance.rate = 0.95;      // Slightly slower for clarity
        utterance.pitch = 1.0;       // Normal pitch
        utterance.volume = 1.0;      // Full volume
        utterance.lang = 'en-US';    // English US
        
        // Speak
        window.speechSynthesis.speak(utterance);
    }
</script>
""", unsafe_allow_html=True)
```

#### 1.2 Add "Speak Feedback" Button
**Location:** Right after feedback display section

**Implementation:**
```python
if st.session_state.feedback:
    col_speak_1, col_speak_2 = st.columns([1, 1])
    
    with col_speak_1:
        if st.button("🔊 Speak Feedback", use_container_width=True):
            st.session_state.speak_enabled = True
    
    with col_speak_2:
        if st.button("⏹️ Stop Speaking", use_container_width=True):
            # Add JavaScript to stop speech
            st.session_state.speak_enabled = False
```

#### 1.3 Integrate Speech Trigger
**Implementation:**
```python
# Add session state for speech control
if 'speak_enabled' not in st.session_state:
    st.session_state.speak_enabled = False

# Trigger speech synthesis when button clicked
if st.session_state.speak_enabled and st.session_state.feedback:
    # Use Streamlit components to call JavaScript
    st.markdown(f"""
    <script>
        speakText("{st.session_state.feedback.replace('"', '\\"')}");
    </script>
    """, unsafe_allow_html=True)
    
    st.session_state.speak_enabled = False  # Reset after trigger
```

### Phase 2: UI/UX Enhancements

#### 2.1 Add Speech Status Indicator
**Implementation:**
```python
if st.session_state.feedback:
    # Add visual feedback
    with st.expander("🔊 Audio Options", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔊 Play Coach Voice", key="play_coach"):
                # Play pre-synthesized audio
                pass
        
        with col2:
            if st.button("🎤 Speak Feedback", key="speak_feedback"):
                # Browser text-to-speech
                pass
        
        with col3:
            if st.button("⏹️ Stop", key="stop_speech"):
                # Stop any speech
                pass
```

#### 2.2 Add Speech Rate Control
**Implementation:**
```python
with st.sidebar:
    st.subheader("🔊 Speech Settings")
    
    speech_rate = st.slider(
        "Speech Rate",
        min_value=0.5,
        max_value=2.0,
        value=0.95,
        step=0.1,
        help="Adjust how fast the AI coach speaks"
    )
    
    speech_pitch = st.slider(
        "Voice Pitch",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Adjust voice pitch"
    )
```

#### 2.3 Add CSS for Button States
**Implementation:**
```python
st.markdown("""
<style>
    .speak-button {
        background-color: #2196F3;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        font-size: 1em;
    }
    
    .speak-button:hover {
        background-color: #0b7dda;
    }
    
    .speak-button:active {
        background-color: #0a5fc4;
    }
    
    .speaking-indicator {
        animation: pulse 1s infinite;
        display: inline-block;
        margin-left: 10px;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)
```

### Phase 3: Backend Enhancement (Optional)

#### 3.1 Create Speech Endpoint
**File:** `app/backend/main.py`

**New Endpoint:**
```python
@app.post("/speak", tags=["Audio"])
async def speak_text(request: SpeakRequest):
    """
    Convert text to speech on-demand.
    
    Args:
        text: Text to synthesize
        voice: TTS voice identifier
        session_id: Session identifier
    
    Returns:
        MP3 audio file
    """
    # Validate input
    if not request.text or len(request.text) > 1000:
        raise HTTPException(status_code=400, detail="Invalid text")
    
    # Use Edge-TTS to synthesize
    output_path = FEEDBACK_DIR / f"speak_{request.session_id}_{int(time.time())}.mp3"
    
    try:
        communicate = edge_tts.Communicate(
            request.text,
            request.voice or DEFAULT_TTS_VOICE
        )
        await communicate.save(str(output_path))
        
        return FileResponse(
            path=output_path,
            media_type="audio/mpeg",
            filename="speech.mp3"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**New Model:**
```python
class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    session_id: str
```

#### 3.2 Add Voice Selection Endpoint
**Implementation:**
```python
@app.get("/voices", tags=["Configuration"])
async def get_available_voices():
    """
    Return available TTS voices.
    
    Returns:
        List of voice options with descriptions
    """
    return {
        "voices": [
            {"id": "en-US-AndrewNeural", "name": "Andrew (US)", "gender": "male"},
            {"id": "en-US-AmberNeural", "name": "Amber (US)", "gender": "female"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "gender": "female"},
            # ... more voices
        ]
    }
```

### Phase 4: Browser Compatibility

#### 4.1 Detect Browser Support
**Implementation:**
```python
st.markdown("""
<script>
    function checkSpeechSupport() {
        const SpeechSynthesisUtterance = window.SpeechSynthesisUtterance || 
                                         window.webkitSpeechSynthesisUtterance;
        return SpeechSynthesisUtterance !== undefined;
    }
    
    window.speechSupported = checkSpeechSupport();
</script>
""", unsafe_allow_html=True)
```

#### 4.2 Provide Fallback
**Implementation:**
```python
# Check browser support and show appropriate controls
support_check = """
    <script>
        if (!window.speechSupported) {
            document.getElementById('speak-button').style.display = 'none';
            document.getElementById('fallback-message').style.display = 'block';
        }
    </script>
"""
```

---

## 📐 Technical Specifications

### Browser Web Speech API Parameters

| Parameter | Type | Default | Range | Purpose |
|-----------|------|---------|-------|---------|
| `rate` | float | 0.95 | 0.1 - 10.0 | Speech speed |
| `pitch` | float | 1.0 | 0.0 - 2.0 | Voice pitch |
| `volume` | float | 1.0 | 0.0 - 1.0 | Audio volume |
| `lang` | string | en-US | Various | Language/locale |

### Supported Browsers

| Browser | Support | Version |
|---------|---------|---------|
| Chrome | ✅ Full | 14+ |
| Firefox | ✅ Full | 49+ |
| Safari | ✅ Full | 14.1+ |
| Edge | ✅ Full | 79+ |
| Opera | ✅ Full | 27+ |
| IE | ❌ None | - |

---

## 🔄 Implementation Workflow

### Step 1: Basic Button & JavaScript
1. Add speak button to feedback section
2. Add JavaScript function to handle text-to-speech
3. Test in different browsers

### Step 2: UI Polish
1. Add speech rate/pitch controls
2. Add stop button
3. Add speaking indicator
4. Style buttons

### Step 3: State Management
1. Track speaking state in session
2. Handle pause/resume
3. Clear speech on new feedback

### Step 4: Optional Backend Integration
1. Create `/speak` endpoint (if needed)
2. Add voice selection
3. Cache synthesized audio

### Step 5: Testing & QA
1. Test on Chrome, Firefox, Safari, Edge
2. Test with long text
3. Test with special characters
4. Test error handling

---

## 📦 Files to Modify

### Primary
- **app/frontend/streamlit_app.py** - Add buttons, JavaScript, UI

### Secondary (Optional)
- **app/backend/main.py** - Add `/speak` endpoint
- **app/models/schemas.py** - Add `SpeakRequest` model

### Configuration
- **app/core/config.py** - Add speech parameters if needed

---

## ⚙️ Code Structure

### New Session State Variables
```python
if 'speaking' not in st.session_state:
    st.session_state.speaking = False

if 'speech_rate' not in st.session_state:
    st.session_state.speech_rate = 0.95

if 'speech_pitch' not in st.session_state:
    st.session_state.speech_pitch = 1.0
```

### New JavaScript Functions
```javascript
// Main speech function
function speakText(text, rate=0.95, pitch=1.0)

// Stop speech
function stopSpeech()

// Check if currently speaking
function isSpeaking()

// Check browser support
function checkSpeechSupport()
```

---

## 🧪 Testing Strategy

### Unit Tests
- JavaScript function calls
- Text validation
- Browser detection

### Integration Tests
- Button click triggers speech
- Multiple feedback items
- Stop button functionality

### User Acceptance Tests
- Clear audio output
- Appropriate speech rate
- Works across browsers
- Accessible controls

### Edge Cases
- Very long text (> 1000 chars)
- Special characters
- Multiple clicks
- Network issues

---

## 📈 Performance Considerations

- **Latency:** ~0.5-1.0 second (browser speech starts immediately)
- **CPU Usage:** Minimal (browser handles synthesis)
- **Memory:** ~10-20MB per utterance
- **Network:** None required (client-side)

---

## 🔐 Security Considerations

- Validate text length (max 1000 characters)
- Escape special characters in JavaScript
- Sanitize user input
- Rate limit speak endpoint (if added)

---

## 🎨 UI/UX Mockup

```
┌─────────────────────────────────────────┐
│  💡 AI Coaching Feedback                │
├─────────────────────────────────────────┤
│                                         │
│  Native Speaker Coaching:               │
│  ┌─────────────────────────────────┐   │
│  │ Your sentence is well-structured!│   │
│  │ For native fluency, consider...  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  [🔊 Speak] [⏹️ Stop] [🎧 Play Audio]   │
│                                         │
│  ┌─ Speech Settings ─────────────────┐ │
│  │ Speed: ▓▓▓░░ 0.95                 │ │
│  │ Pitch: ▓▓▓░░ 1.0                  │ │
│  └────────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

---

## 📋 Implementation Checklist

- [ ] Phase 1: Add speak button and JavaScript function
- [ ] Phase 2: Add UI controls and styling
- [ ] Phase 3: Add state management
- [ ] Phase 4: Test browser compatibility
- [ ] Phase 5: Add backend speak endpoint (optional)
- [ ] Phase 6: Testing & QA
- [ ] Phase 7: Documentation update

---

## 🚀 Rollout Plan

### Version 1.0 (MVP)
- Browser Web Speech API button
- Basic speech rate control
- Stop button
- Works on major browsers

### Version 1.1 (Enhancement)
- Backend audio synthesis option
- Voice selection
- Audio caching
- Analytics tracking

### Version 2.0 (Future)
- Multiple language support
- Advanced voice options
- Real-time speech processing
- User preferences storage

---

## 📚 References

### Browser Web Speech API
- [MDN Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)
- [Can I Use](https://caniuse.com/speech-synthesis)
- [W3C Spec](https://www.w3.org/TR/speech-synthesis/)

### Related Libraries
- [TTS.js](https://github.com/TrevorBlythe/MaryTTS) - Advanced TTS
- [Speak.js](https://github.com/matei-alex/speak-tts) - Wrapper library
- [ResponsiveVoice](https://responsivevoice.org/) - Cloud TTS service

---

## 💡 Alternative Approaches

### Approach 1: Native HTML5 Audio Tags
**Pros:** Simple, native
**Cons:** Limited control, less modern
**Status:** Not recommended

### Approach 2: Third-party TTS API
**Pros:** High quality, many voices
**Cons:** External dependency, cost, latency
**Status:** Consider for premium features

### Approach 3: WebRTC Peer Connection
**Pros:** Low latency, streaming
**Cons:** Complex, overkill for this use case
**Status:** Not recommended

---

## ✅ Success Criteria

- ✅ Users can click button to hear coach feedback spoken
- ✅ Speech synthesis is clear and intelligible
- ✅ Users can adjust speech rate
- ✅ Users can stop speaking mid-sentence
- ✅ Works on Chrome, Firefox, Safari, Edge
- ✅ No backend latency impact
- ✅ Graceful degradation for unsupported browsers

---

## 📞 Support & Questions

For implementation questions:
1. Refer to Web Speech API documentation
2. Check browser console for errors
3. Test with simple text first
4. Verify browser support before assuming features

---

**Document Version:** 1.0
**Last Updated:** January 28, 2026
**Status:** Ready for Implementation
