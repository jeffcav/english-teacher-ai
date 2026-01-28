# PhonicFlow v2.0 - Chat Interface | Quick Start Guide

## What's New in v2.0

✨ **Chat-like Conversation Interface**
- User inputs and AI responses displayed as alternating chat bubbles
- Natural conversation flow like a messaging app
- Color-coded: Blue for user, Gray for AI assistant

📋 **Separated Coaching Feedback**
- Coaching tips no longer interrupt conversation
- Expandable "Coaching & Learning" section
- Organized by turn number, latest expanded by default

🔊 **Dedicated Audio Players**
- Conversational audio and Coaching audio separated
- Clear labels and fallback messages
- Side-by-side layout for easy access

## Running PhonicFlow v2.0

### Prerequisites
```bash
# Python 3.9+ with virtual environment activated
source .venv/bin/activate

# Required packages
pip install fastapi uvicorn streamlit requests pydantic python-multipart
pip install openai-whisper pyttsx3 ollama
```

### Start Backend (Terminal 1)
```bash
cd /home/jeff/dev/pg/english
python app/backend/main.py
```
Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Start Streamlit Frontend (Terminal 2)
```bash
cd /home/jeff/dev/pg/english
streamlit run app/frontend/streamlit_app.py
```
Expected output:
```
  You can now view your Streamlit app in your browser.
  
  Local URL: http://localhost:8501
```

### Access the App
Open browser to: **http://localhost:8501**

## Using the Chat Interface

### Recording Your First Input

1. **Click "Click to record your speech"** in the left panel
2. **Speak your English practice phrase** (e.g., "Hello, my name is...")
3. **Stop recording** when done
4. **Wait for "Processing your speech..."** spinner to complete

### View Results

**Chat Thread (Right Side, Top)**
- Your message appears in blue bubble (labeled "You")
- AI's response appears in gray bubble (labeled "Assistant")
- New messages fade in smoothly

**Coaching Tips (Right Side, Middle)**
- Expandable section labeled "Turn 1 - Coaching Tips"
- Click to see pronunciation corrections and tips
- Latest turn automatically expanded

**Audio Playback (Right Side)**
- Two audio players side-by-side
- Left: "Conversational Response" - friendly reply audio
- Right: "Coaching Audio" - pronunciation tips audio
- Click play to listen

### Continue the Conversation

1. **Record next audio** using the microphone in left panel
2. **Chat thread grows** with new user/assistant message pair
3. **New coaching tips appear** in expanders below
4. **Repeat** as many times as you want

## Conversation Management

### Clear History
- Clears all previous messages
- Keeps same session ID
- All coaching and audio deleted

### New Chat
- Creates completely new session (new ID)
- Clears all history
- Starts fresh conversation

## Settings (Sidebar)

**Speech Rate** (0.5x - 2.0x)
- Controls audio playback speed
- Default: 1.0 (normal speed)
- Slower for better comprehension

**Speech Pitch** (0.5 - 2.0)
- Controls voice pitch
- Default: 1.0 (normal pitch)
- Higher for emphasis/emotion

**Session Info**
- Displays unique conversation ID
- Used for organizing conversation history
- Reset when starting new chat

## File Structure

```
app/
├── frontend/
│   └── streamlit_app.py          ← Chat interface (NEW v2.0)
├── backend/
│   └── main.py                   ← FastAPI server
├── core/
│   ├── architect.py              ← STT → LLM → TTS pipeline
│   └── config.py                 ← Configuration
├── models/
│   └── schemas.py                ← Data validation
└── feedback_storage/
    ├── conversations/            ← Conversation history (JSON)
    └── *.mp3                      ← Audio files
```

## How It Works (Under the Hood)

### Flow for Each Audio Input

```
1. FRONTEND: User records audio
   ↓
2. FRONTEND: Sends MP3 to backend `/process` endpoint
   ↓
3. BACKEND: Whisper transcribes audio → text
   ↓
4. BACKEND: Load previous conversation context (last 3 turns)
   ↓
5. BACKEND: Ollama LLM processes twice:
   a) Coaching prompt → phonetic corrections & tips
   b) Conversational prompt → friendly response
   ↓
6. BACKEND: pyttsx3 synthesizes two separate MP3 files
   a) coaching_audio.mp3
   b) conversational_audio.mp3
   ↓
7. BACKEND: Save conversation turn to JSON:
   {
     "user": "transcribed speech",
     "coaching": "phonetic feedback",
     "conversational": "friendly response"
   }
   ↓
8. BACKEND: Return FeedbackResponse with paths and text
   ↓
9. FRONTEND: Display chat message in thread
   ↓
10. FRONTEND: Update coaching tips expander
   ↓
11. FRONTEND: Load audio files into players
```

### Conversation Context

LLM receives context of last 3 turns:
- User inputs
- Conversational responses

This helps maintain natural multi-turn conversation while improving coaching consistency.

## Troubleshooting

### "Audio not found" message
- Audio files take 3-5 seconds to generate
- Click the audio player area to retry loading
- Check backend is running: `curl http://localhost:8000/health`

### "Processing error" on backend
- Verify Ollama is running: `ollama serve`
- Check audio format (WAV, MP3, M4A supported)
- Check available disk space for audio files

### Backend not starting
```bash
# Check if port 8000 is in use
lsof -i :8000

# If in use, kill process
kill -9 <PID>
```

### Streamlit not loading
```bash
# Clear cache
streamlit cache clear

# Restart with no cache
streamlit run app/frontend/streamlit_app.py --logger.level=debug
```

## API Endpoints Reference

### Process Audio
```bash
curl -X POST http://localhost:8000/process \
  -F "file=@audio.wav" \
  -F "session_id=session_123"

# Response:
{
  "user_transcript": "Hello my name is...",
  "coaching_feedback": "Great job with the...",
  "conversational_response": "Nice to meet you!",
  "coaching_audio_path": "session_123_coaching.mp3",
  "conversational_audio_path": "session_123_conversational.mp3"
}
```

### Get Conversation History
```bash
curl http://localhost:8000/conversation/session_123

# Response:
{
  "history": [
    {
      "user": "first input",
      "coaching": "coaching feedback",
      "conversational": "friendly response"
    },
    ...
  ]
}
```

### Get Audio File
```bash
curl http://localhost:8000/audio/session_123?audio_type=conversational \
  --output audio.mp3
```

### Clear Conversation
```bash
curl -X DELETE http://localhost:8000/conversation/session_123
```

## System Requirements

- **RAM:** 4GB minimum (for Ollama + Whisper)
- **Disk:** 2GB minimum (for models + audio files)
- **CPU:** Any modern processor (can run on Intel/AMD)
- **GPU:** Optional (faster processing if available)
- **Python:** 3.9+
- **OS:** Linux, macOS, Windows (WSL)

## Performance Notes

**Latency per turn:**
- Audio recording: User controls
- Whisper transcription: ~2-5 seconds
- Ollama LLM (2x): ~5-15 seconds
- pyttsx3 TTS (2x): ~2-3 seconds
- Total: ~10-25 seconds per turn

**Conversation history:**
- Stored as JSON in `app/feedback_storage/conversations/`
- One file per session
- Context window: Last 3 turns
- No limit on conversation length

## Tips for Best Results

1. **Clear Audio** - Speak clearly in a quiet environment
2. **Natural Pace** - Speak at natural English pace
3. **Longer Phrases** - 5-10 seconds of speech works best
4. **Focused Practice** - Record multiple turns on same topic
5. **Listen to Audio** - Pay attention to pronunciation audio

## What's Happening in Backend

**Ollama LLM Processing:**
- **Coaching Path:** Analyzes pronunciation, identifies errors, gives corrective tips
- **Conversational Path:** Responds naturally like a friend, maintains context
- Both processes use conversation history for consistency

**Context Awareness:**
- LLM knows previous exchanges
- Can reference earlier statements
- Builds on previous coaching feedback

## FAQ

**Q: Can I delete individual messages?**  
A: Not yet - clear history resets entire conversation

**Q: Can I export the conversation?**  
A: Yes - conversation stored in JSON at `app/feedback_storage/conversations/{session_id}.json`

**Q: Does it work offline?**  
A: Yes! All processing is local (Whisper, Ollama, pyttsx3)

**Q: Can I change the AI model?**  
A: Yes - edit `app/core/config.py` to use different Ollama models (Llama2, Mistral, etc.)

**Q: Is my data private?**  
A: Completely - all data stays on your machine

## Next Steps

1. **Start recording** and build your conversation
2. **Practice pronunciation** by listening to coached audio
3. **Review coaching tips** in the expandable sections
4. **Continue multi-turn** conversations to maintain context
5. **Try different topics** to expand vocabulary

Happy learning! 🚀

---

**Version:** PhonicFlow v2.0  
**Last Updated:** 2024  
**Status:** ✅ Production Ready
