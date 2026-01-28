# PhonicFlow Dual Output API Contract

## Overview
The API now supports generating two independent LLM responses: phonetic coaching and conversational dialogue.

## Endpoints

### POST /process
Process user audio and generate both coaching feedback and conversational response.

**Request:**
```
POST /process HTTP/1.1
Content-Type: multipart/form-data

Parameters:
  file: <binary audio data> (required)
    Accepted formats: wav, mp3, m4a, flac
  session_id: <string> (optional)
    Unique session identifier. Auto-generated if omitted.
```

**Response (200 OK):**
```json
{
  "user_transcript": "I am very happy today and I want to share",
  "coaching_feedback": "Great effort! Try: 'I am very happy today and I want to share this with you.' The pronunciation was mostly clear, well done!",
  "conversational_response": "That's wonderful! I'm glad you're having such a great day. What made you so happy today?",
  "coaching_audio_path": "/home/jeff/dev/pg/english/app/feedback_storage/session_1234567890_coaching.mp3",
  "conversational_audio_path": "/home/jeff/dev/pg/english/app/feedback_storage/session_1234567890_conversational.mp3"
}
```

**Error Responses:**
```json
// 400 Bad Request - Invalid audio format
{
  "detail": "Unsupported audio format: xyz. Supported: wav, mp3, m4a, flac"
}

// 500 Internal Server Error - Processing failed
{
  "detail": "Processing error: <error message>"
}
```

### GET /audio/{session_id}
Retrieve synthesized audio for a specific session.

**Request:**
```
GET /audio/{session_id}?audio_type=TYPE HTTP/1.1

Parameters:
  session_id: <string> (required, in URL path)
    Session identifier from /process response
  audio_type: <string> (optional, default: "coaching")
    Either "coaching" or "conversational"
```

**Response (200 OK):**
```
Content-Type: audio/mpeg
Content-Disposition: attachment; filename="feedback_{session_id}_{audio_type}.mp3"

<binary MP3 audio data>
```

**Error Responses:**
```json
// 404 Not Found - Audio file doesn't exist yet
{
  "detail": "Audio not found for session <session_id> (type: <audio_type>)"
}
```

## Data Types

### FeedbackResponse
```python
{
  "user_transcript": str,           # User's spoken words (transcribed by Whisper)
  "coaching_feedback": str,         # Phonetic/grammatical feedback with corrections
  "conversational_response": str,   # Natural response as if replying to a friend
  "coaching_audio_path": str,       # Absolute path to coaching MP3 file
  "conversational_audio_path": str  # Absolute path to conversational MP3 file
}
```

## Processing Pipeline

```
1. User uploads audio file
   ↓
2. Backend saves audio temporarily
   ↓
3. Whisper transcribes to text
   ↓
4. LLM generates TWO responses:
   a) Coaching feedback
   b) Conversational response
   ↓
5. pyttsx3 synthesizes both to MP3
   a) {session_id}_coaching.mp3
   b) {session_id}_conversational.mp3
   ↓
6. Return FeedbackResponse with paths
   ↓
7. Frontend fetches both audio files via /audio endpoint
```

## Request Examples

### cURL - Process Audio
```bash
curl -X POST http://localhost:8000/process \
  -F "file=@my_audio.wav" \
  -F "session_id=my_session_123" | jq
```

### cURL - Get Coaching Audio
```bash
curl "http://localhost:8000/audio/my_session_123?audio_type=coaching" \
  --output coaching.mp3
```

### cURL - Get Conversational Audio
```bash
curl "http://localhost:8000/audio/my_session_123?audio_type=conversational" \
  --output conversation.mp3
```

### Python - Process Audio
```python
import requests

# Process audio
with open("audio.wav", "rb") as f:
    files = {"file": f}
    data = {"session_id": "session_123"}
    response = requests.post(
        "http://localhost:8000/process",
        files=files,
        data=data
    )

result = response.json()
print("Coaching:", result["coaching_feedback"])
print("Conversation:", result["conversational_response"])

# Get coaching audio
coaching_response = requests.get(
    f"http://localhost:8000/audio/{result['session_id']}?audio_type=coaching"
)
with open("coaching.mp3", "wb") as f:
    f.write(coaching_response.content)

# Get conversational audio
conv_response = requests.get(
    f"http://localhost:8000/audio/{result['session_id']}?audio_type=conversational"
)
with open("conversational.mp3", "wb") as f:
    f.write(conv_response.content)
```

### JavaScript/Fetch - Process Audio
```javascript
const audio = new Blob([audioBuffer], { type: 'audio/wav' });
const formData = new FormData();
formData.append('file', audio, 'recording.wav');
formData.append('session_id', 'session_' + Date.now());

const response = await fetch('http://localhost:8000/process', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Coaching:', result.coaching_feedback);
console.log('Conversation:', result.conversational_response);

// Fetch both audio files
const coachingAudio = await fetch(
  `http://localhost:8000/audio/${result.session_id}?audio_type=coaching`
);
const coachingBlob = await coachingAudio.blob();

const convAudio = await fetch(
  `http://localhost:8000/audio/${result.session_id}?audio_type=conversational`
);
const convBlob = await convAudio.blob();
```

## File Storage

Audio files are stored in: `/home/jeff/dev/pg/english/app/feedback_storage/`

**File Naming Convention:**
```
{session_id}_coaching.mp3           ← Phonetic/grammatical feedback audio
{session_id}_conversational.mp3     ← Conversational response audio
temp_{session_id}.{extension}       ← Temporary file (cleaned up after processing)
```

**Example:**
```
session_1234567890_coaching.mp3
session_1234567890_conversational.mp3
```

## Response Characteristics

### Coaching Feedback
- **Purpose:** Identify pronunciation errors and suggest corrections
- **Tone:** Encouraging and constructive
- **Length:** Under 50 words
- **Content Examples:**
  - "Great effort! Try: 'I want to share this with you.' The /ə/ sound in 'with' was clear."
  - "Your intonation is natural. Remember: 'really' is pronounced 'REE-lee' not 'real-lee'."

### Conversational Response
- **Purpose:** Continue conversation naturally as a friend would
- **Tone:** Casual, engaging, warm
- **Length:** Under 50 words
- **Content Examples:**
  - "That sounds wonderful! I'm happy for you. What made your day so special?"
  - "Oh nice! That's great news. When is the event happening?"

## Error Handling

### Common Errors

**404 Not Found - Audio Processing Delay**
- Cause: Audio files not yet created by backend
- Solution: Wait a few seconds and retry
- Typical delay: 2-5 seconds

**500 Internal Server Error - TTS Synthesis Failed**
- Cause: pyttsx3 couldn't synthesize audio
- Solution: Check backend logs for `[TTS]` error messages
- Common causes:
  - Empty feedback text
  - System speech synthesis unavailable (Linux without espeak)
  - Disk space issues

**400 Bad Request - Unsupported Format**
- Cause: Audio file format not in [wav, mp3, m4a, flac]
- Solution: Convert audio to supported format first

## Response Time

- **Typical:** 5-15 seconds total
  - 2-3s: Whisper transcription
  - 2-4s: LLM generation
  - 2-8s: pyttsx3 synthesis (both files)
- **Maximum:** 30 seconds (timeout on /audio endpoint)

## API Version

- **Current:** v1.0.0 (with dual output support)
- **Backward Compatibility:** 
  - Old field names (`native_feedback`) no longer available
  - Use new field names: `coaching_feedback`, `conversational_response`
  - `/audio/{session_id}` defaults to `coaching` for compatibility

## Configuration

The API uses these settings (from `app/core/config.py`):

```python
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_LLM_NAME = "llama3"  # or "mistral", "gemma3", etc.
DEFAULT_WHISPER_MODEL = "base.en"
FEEDBACK_DIR = Path("app/feedback_storage")
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "m4a", "flac"]
```

## Health Check

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "operational",
  "components": {
    "whisper": "available",
    "ollama": "available",
    "tts": "available"
  }
}
```

## Rate Limiting

- **Current:** No rate limiting implemented
- **Concurrent Requests:** Depends on system resources
- **Recommended:** 1 request per 5-10 seconds per user

## Security Considerations

1. **No Authentication:** Currently no API key required
2. **CORS Enabled:** Accepts requests from all origins (`*`)
3. **File Upload:** Accept only audio formats specified
4. **File Storage:** Audio files stored with session IDs, no encryption

## Future API Changes

Planned enhancements:
- [ ] Parallel audio synthesis (reduce response time)
- [ ] Streaming audio responses
- [ ] User preference storage
- [ ] Response caching
- [ ] Batch processing support

---

**Last Updated:** January 28, 2026
**API Version:** 1.0.0 with Dual Output Support
