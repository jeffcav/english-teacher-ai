# Quick Start: Testing the Dual Output Feature

## Setup

1. **Install Updated Dependencies**
   ```bash
   cd /home/jeff/dev/pg/english
   pip install -r requirements.txt
   ```

2. **Verify Backend Services**
   ```bash
   # Check Ollama is running
   curl http://localhost:11434/api/tags
   
   # Check a model is available (e.g., llama3, mistral, gemma3)
   # If not, pull one: ollama pull llama3
   ```

3. **Start the Backend**
   ```bash
   # In terminal 1
   cd /home/jeff/dev/pg/english
   python -m app.backend.main
   # Or use uvicorn directly:
   # uvicorn app.backend.main:app --reload --host localhost --port 8000
   ```

4. **Start the Frontend**
   ```bash
   # In terminal 2
   cd /home/jeff/dev/pg/english
   streamlit run app/frontend/streamlit_app.py
   ```

## Testing the Feature

### Test Flow

1. **Record Audio**
   - Use the recording widget on the left
   - Say something like: "I am very happy today and I want to share my joy with you"

2. **Click "Analyze Audio"**
   - Backend processes through pipeline
   - Monitor backend terminal for `[TTS]` logging messages

3. **View Results**
   - You should see:
     - ✅ Your transcription
     - ✅ Coaching feedback (corrections/suggestions)
     - ✅ Conversational response (as a friend)
     - ✅ Two audio players (one for each response)

### Expected Behavior

**Backend Logs:**
```
[TTS] Synthesizing coaching feedback (85 chars) to /path/to/session_coaching.mp3
[TTS] Successfully created audio file: ... (XXXX bytes)
[TTS] Synthesizing conversational feedback (92 chars) to /path/to/session_conversational.mp3
[TTS] Successfully created audio file: ... (XXXX bytes)
```

**Frontend Display:**
```
Your Speech (Transcribed):
[Yellow box with transcription]

📝 Coaching Feedback:
[Blue box with corrections]
[Audio player for coaching]
✅ Click to hear the coaching feedback

💬 AI Response (as a friend):
[Blue box with conversational reply]
[Audio player for conversational]
✅ Click to hear the conversational response
```

### Audio Files Generated

In `/home/jeff/dev/pg/english/app/feedback_storage/`:
```
session_1234567890_coaching.mp3          ← Coaching audio
session_1234567890_conversational.mp3    ← Conversational audio
```

## Debugging

### If coaching audio doesn't generate:
1. Check backend for `[TTS]` errors
2. Verify pyttsx3 is installed: `python -c "import pyttsx3; print('OK')"`
3. Check file permissions in `app/feedback_storage/`

### If conversational audio doesn't generate:
Same as above - pyttsx3 needs working system speech synthesis

### If LLM response doesn't have both parts:
- Check backend logs for LLM response
- Verify Ollama model is responsive: `ollama list`
- Check system prompt in `architect.py` for marker format: `---COACHING---` and `---CONVERSATION---`

### If audio players don't appear:
1. Verify both audio files exist in `feedback_storage/`
2. Check frontend made two `/audio/{session_id}?audio_type=X` requests
3. Browser console for JavaScript errors

## API Testing (curl)

```bash
# 1. Process audio and get feedback
curl -X POST http://localhost:8000/process \
  -F "file=@/path/to/audio.wav" \
  -F "session_id=test_123" | jq

# Expected response:
{
  "user_transcript": "...",
  "coaching_feedback": "...",
  "conversational_response": "...",
  "coaching_audio_path": "/path/to/session_123_coaching.mp3",
  "conversational_audio_path": "/path/to/session_123_conversational.mp3"
}

# 2. Get coaching audio
curl http://localhost:8000/audio/test_123?audio_type=coaching \
  --output coaching.mp3

# 3. Get conversational audio
curl http://localhost:8000/audio/test_123?audio_type=conversational \
  --output conversational.mp3

# 4. Verify audio files exist and have size > 0
file *.mp3
du -h *.mp3
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "ReferenceError: weakly-referenced object no longer exists" | Already fixed in updated code with 0.5s delay and cleanup |
| Audio files empty (0 bytes) | Check pyttsx3 error logs, verify text is not empty |
| Markers not found in LLM response | Check Ollama model formatting, fallback to simple coaching |
| Audio files created but not playing | Check format is valid MP3, try `mpg123 file.mp3` to test |
| "Audio not found" 404 error | Verify both files are generated, check session ID matches |

## Feature Validation

✅ Checklist:
- [ ] Both text outputs displayed correctly
- [ ] Both audio files created in feedback_storage
- [ ] Both audio players work independently
- [ ] Coaching feedback quality is good
- [ ] Conversational response sounds natural
- [ ] Clear & Retry button clears both feedbacks
- [ ] Frontend handles missing audio gracefully
- [ ] LLM uses appropriate language for each type

## Next Steps

1. **Test with different audio samples**
   - Short phrases
   - Long sentences
   - Different accents
   - Background noise

2. **Monitor pyttsx3 performance**
   - How long does synthesis take?
   - Audio quality on system voices
   - Memory usage with long texts

3. **Consider enhancements**
   - Save user preferences (prefer audio or text?)
   - Add playback speed control
   - Implement audio caching
   - Add multiple language support

## Files to Monitor

```
Backend logs:        ← Look for [TTS] markers
Terminal output:     ← Errors during synthesis

Audio storage:
app/feedback_storage/
├── session_*_coaching.mp3
└── session_*_conversational.mp3

Frontend logs:
Browser console (F12) ← JavaScript errors, API calls
```

---

**Ready to test!** Start with step 3 in Setup section.
