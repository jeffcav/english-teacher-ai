# PhonicFlow Dual Output Feature

## Overview
Added dual-output functionality to PhonicFlow where the LLM generates two independent responses for every user input:
1. **Coaching Feedback** - Phonetic and grammatical corrections with constructive guidance
2. **Conversational Response** - Natural response as if replying to a friend

## Architecture Changes

### Backend (FastAPI)

#### 1. Schema Updates (`app/models/schemas.py`)
```python
class FeedbackResponse(BaseModel):
    user_transcript: str
    coaching_feedback: str              # NEW: Phonetic/grammatical feedback
    conversational_response: str        # NEW: Friendly conversational response
    coaching_audio_path: str            # NEW: Audio for coaching
    conversational_audio_path: str      # NEW: Audio for conversation
```

#### 2. LLM Integration (`app/core/architect.py`)

**Updated `get_linguistic_coaching()` method:**
- Returns `tuple[str, str]` instead of single string
- Sends structured prompt with two sections marked by `---COACHING---` and `---CONVERSATION---`
- Parses both responses separately
- Provides fallback if markers not found

**Updated `synthesize_feedback()` method:**
- Added `feedback_type` parameter ("coaching" or "conversational")
- Output files: `{session_id}_coaching.mp3` and `{session_id}_conversational.mp3`
- Same local pyttsx3 synthesis with improved thread-pool execution

**Updated `process_user_input()` orchestration:**
- Calls `get_linguistic_coaching()` once, gets both responses
- Synthesizes both to separate audio files
- Returns `FeedbackResponse` with all data

#### 3. API Endpoint Updates (`app/backend/main.py`)

**`POST /process` endpoint:**
- Returns updated `FeedbackResponse` with both feedback types and audio paths

**`GET /audio/{session_id}` endpoint:**
- Added `audio_type` query parameter (default: "coaching")
- Supports: `?audio_type=coaching` or `?audio_type=conversational`
- Returns appropriate MP3 file

### Frontend (Streamlit)

#### 1. Session State Updates
```python
st.session_state.coaching_feedback        # NEW
st.session_state.conversational_response  # NEW
st.session_state.coaching_audio_path      # NEW (from API)
st.session_state.conversational_audio_path # NEW (from API)
```

#### 2. UI Display Structure

**Layout:**
```
Your Speech (Transcribed)
├─ Coaching Feedback Section
│  ├─ Text feedback
│  └─ Audio player
├─ Conversational Response Section
│  ├─ Text feedback
│  └─ Audio player
└─ Browser Voice Alternative (for coaching)
```

**Display Components:**
- "📝 Coaching Feedback" - Shows phonetic/grammatical corrections with audio player
- "💬 AI Response (as a friend)" - Shows natural conversational reply with audio player
- "🔊 Alternative: Browser Text-to-Speech" - Speaks coaching feedback using Web Speech API

#### 3. Helper Function Updates

**`get_feedback_audio(session_id, audio_type="coaching")`:**
- Now accepts optional `audio_type` parameter
- Constructs URL: `{API_BASE_URL}/audio/{session_id}?audio_type={audio_type}`
- Retrieves correct audio file from backend

## Data Flow

```
User Recording
    ↓
[Whisper STT] → Transcription
    ↓
[LLM - Single Prompt]
    ├─ Coaching Feedback ───────────────→ [pyttsx3] → coaching_{session}.mp3
    └─ Conversational Response ─────────→ [pyttsx3] → conversational_{session}.mp3
    ↓
Frontend Displays:
    ├─ Coaching text + audio player
    └─ Conversational text + audio player
```

## LLM Prompt Structure

```
Analyze the user's speech and provide TWO separate responses:

USER SAID: "{user_text}"

RESPONSE FORMAT (clearly separate both parts):
---COACHING---
Provide feedback on pronunciation, grammar, and naturalness. 
Keep it under 50 words. Be encouraging.

---CONVERSATION---
Respond naturally to what the user said, as if you were their friend 
having a conversation. Keep it natural and conversational (under 50 words).
```

## Key Benefits

1. **Dual Learning Paths**
   - Users get correction (coaching) AND natural conversation flow
   - More engaging than pure correction

2. **Separate Audio Synthesis**
   - Each response has its own audio file
   - Users can choose which to listen to
   - Independent audio quality/pacing per type

3. **Fallback Parsing**
   - If markers not found, treats response as coaching
   - Conversational defaults to "Thank you for sharing that!"
   - Robust to different LLM response formats

4. **Session Isolation**
   - Two separate `.mp3` files per session
   - Clean file naming: `session_id_coaching.mp3`, `session_id_conversational.mp3`
   - No conflicts with existing file structure

## Configuration

**System Prompt for Dual Output (in `architect.py`):**
```python
"You are an English tutor and friendly conversationalist."
```

This prompt encourages the LLM to balance both teaching and engagement.

## Testing Checklist

- [ ] Record audio, verify both coaching and conversational text generated
- [ ] Verify two `.mp3` files created in `feedback_storage/`
- [ ] Click audio players, verify correct audio plays for each
- [ ] Check `[TTS]` backend logs show both synthesis operations
- [ ] Verify fallback behavior if LLM doesn't use markers
- [ ] Test on different browsers (Web Speech API for alternative voice)
- [ ] Verify Clear & Retry clears both feedback types
- [ ] Check API response format with `curl`:
  ```bash
  curl http://localhost:8000/audio/session_id?audio_type=coaching
  curl http://localhost:8000/audio/session_id?audio_type=conversational
  ```

## Files Modified

1. `app/models/schemas.py` - FeedbackResponse schema
2. `app/core/architect.py` - LLM and TTS logic (2 methods + 1 new helper)
3. `app/backend/main.py` - `/audio/{session_id}` endpoint
4. `app/frontend/streamlit_app.py` - UI display and state management

## Future Enhancements

1. **User Preferences**
   - Save which output users prefer
   - Auto-play only preferred type

2. **Pronunciation Playback**
   - Option to slow down audio playback
   - Pitch controls per output type

3. **Learning Analytics**
   - Track correction patterns
   - Generate progress reports

4. **Multi-turn Conversation**
   - Allow back-and-forth dialogue
   - Maintain conversation context

## Notes

- pyttsx3 synthesis runs in thread pool to prevent async context issues
- Both audio files synthesized concurrently (one after other, awaited)
- Fallback parsing handles imperfect LLM marker formatting
- Frontend gracefully handles missing audio files (shows retry button)
