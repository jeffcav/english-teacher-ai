# PhonicFlow API Documentation

## Overview

The PhonicFlow API is a RESTful service that provides audio processing and AI-powered linguistic coaching. It orchestrates three AI engines:

- **Whisper**: Transcribes speech to text
- **Ollama**: Analyzes text and provides coaching
- **Edge-TTS**: Synthesizes audio feedback

---

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication required (for development). For production, add API key validation.

---

## Endpoints

### 1. Root Endpoint

**GET** `/`

Returns API information and available endpoints.

**Response (200 OK):**
```json
{
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
```

**Example:**
```bash
curl http://localhost:8000/
```

---

### 2. Health Check

**GET** `/health`

Checks the health status of all AI components.

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

**Response (200 Degraded):**
```json
{
  "status": "degraded",
  "components": {
    "whisper": "available",
    "ollama": "error: connection refused",
    "tts": "available"
  }
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### 3. Process Audio

**POST** `/process`

Main endpoint for processing audio and generating coaching feedback.

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| file | file | form | Yes | Audio file (.wav, .mp3, .m4a, .flac) |
| session_id | string | query | No | Unique session identifier (auto-generated if omitted) |

**Request:**
```bash
curl -X POST \
  -F "file=@recording.wav" \
  -F "session_id=user_session_001" \
  http://localhost:8000/process
```

**Response (200 OK):**
```json
{
  "user_transcript": "I want to improve my English pronunciation",
  "native_feedback": "Your sentence is well-structured! For native fluency, consider: 'I'd like to improve my English pronunciation.' The contraction 'I'd' sounds more natural in conversation.",
  "audio_feedback_path": "/app/feedback_storage/user_session_001.mp3"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Unsupported audio format: ogg. Supported: wav, mp3, m4a, flac"
}
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Internal server error",
  "error": "CUDA out of memory"
}
```

**Supported Audio Formats:**
- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- FLAC (.flac)

**Processing Time:**
- Typical: 5-15 seconds
- Max: 60 seconds (timeout)
- Depends on: audio length, model size, hardware

---

### 4. Get Feedback Audio

**GET** `/audio/{session_id}`

Retrieves the synthesized audio feedback for a session.

**Parameters:**

| Name | Type | Location | Required | Description |
|------|------|----------|----------|-------------|
| session_id | string | path | Yes | Session identifier from /process response |

**Response (200 OK):**
- Content-Type: `audio/mpeg`
- Body: MP3 audio file

**Response (404 Not Found):**
```json
{
  "detail": "Audio not found for session: unknown_session"
}
```

**Example:**
```bash
# Retrieve and save audio
curl http://localhost:8000/audio/user_session_001 -o feedback.mp3

# Play with ffplay
ffplay feedback.mp3
```

---

### 5. Get Configuration

**GET** `/config`

Returns current model and voice configuration.

**Response (200 OK):**
```json
{
  "whisper_model": "base.en",
  "llm_name": "llama3",
  "tts_voice": "en-US-AndrewNeural"
}
```

**Example:**
```bash
curl http://localhost:8000/config
```

---

### 6. Update Configuration

**POST** `/config`

Updates model and voice settings at runtime.

**Request Body:**
```json
{
  "whisper_model": "medium.en",
  "llm_name": "mistral",
  "tts_voice": "en-GB-SoniaNeural"
}
```

**Response (200 OK):**
```json
{
  "status": "configuration updated",
  "settings": {
    "whisper_model": "medium.en",
    "llm_name": "mistral",
    "tts_voice": "en-GB-SoniaNeural"
  }
}
```

**Example:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"whisper_model": "large-v3", "llm_name": "mistral"}' \
  http://localhost:8000/config
```

---

## Request/Response Models

### FeedbackResponse

Response model from `/process` endpoint.

```python
{
  "user_transcript": str,           # Transcribed speech
  "native_feedback": str,            # Coaching feedback
  "audio_feedback_path": str         # Path to MP3 file
}
```

### ModelConfig

Configuration model for `/config` endpoint.

```python
{
  "whisper_model": str,    # Optional: whisper model name
  "llm_name": str,         # Optional: LLM model name
  "tts_voice": str         # Optional: TTS voice identifier
}
```

---

## Model Options

### Whisper STT Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny.en | 39MB | ⚡⚡⚡ | ⭐⭐ | Real-time, low latency |
| base.en | 140MB | ⚡⚡ | ⭐⭐⭐ | **Recommended** |
| small.en | 244MB | ⚡ | ⭐⭐⭐⭐ | Better accuracy |
| medium.en | 769MB | ⚠️ | ⭐⭐⭐⭐⭐ | High accuracy |
| large-v3 | 2.9GB | ⚠️⚠️ | ⭐⭐⭐⭐⭐ | Maximum accuracy |

### LLM Models (Ollama)

| Model | Size | Speed | Quality | Language |
|-------|------|-------|---------|----------|
| mistral | 4GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | English + 40+ languages |
| llama3 | 4.7GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | **Recommended** |
| neural-chat | 3.8GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Conversation optimized |
| llama2 | 3.8GB | ⚡⚡ | ⭐⭐⭐⭐ | General purpose |

### TTS Voices

**US English:**
- `en-US-AndrewNeural` - Male, neutral
- `en-US-AmberNeural` - Female, neutral
- `en-US-AriaNeural` - Female, warm
- `en-US-GuyNeural` - Male, warm
- `en-US-JennyNeural` - Female, friendly

**UK English:**
- `en-GB-SoniaNeural` - Female, formal
- `en-GB-RyanNeural` - Male, neutral

**Australian English:**
- `en-AU-NatashaNeural` - Female
- `en-AU-WilliamNeural` - Male

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid file format, missing parameters |
| 404 | Not Found | Session/audio not found |
| 500 | Internal Server Error | Processing error, OOM, connectivity |
| 503 | Service Unavailable | Ollama not responding |

### Error Response Format

```json
{
  "detail": "Error description",
  "error": "Technical details (if available)"
}
```

### Common Errors

**Unsupported Audio Format:**
```json
{
  "detail": "Unsupported audio format: ogg. Supported: wav, mp3, m4a, flac"
}
```

**Audio File Not Found:**
```json
{
  "detail": "Audio file not found: /path/to/file.wav"
}
```

**Ollama Connection Error:**
```json
{
  "detail": "Internal server error",
  "error": "Error connecting to Ollama: Connection refused"
}
```

---

## Rate Limiting & Timeouts

- **Request Timeout:** 60 seconds
- **Max Audio Duration:** 300 seconds (5 minutes)
- **Max File Size:** No hard limit (limited by system RAM)

---

## Examples

### Complete Workflow

```bash
#!/bin/bash

# 1. Check API status
echo "Checking API health..."
curl -s http://localhost:8000/health | jq .

# 2. Record audio (requires external recorder or file)
# ffmpeg -f alsa -i default -d 5 recording.wav

# 3. Process audio
echo "Processing audio..."
RESPONSE=$(curl -s -X POST \
  -F "file=@recording.wav" \
  -F "session_id=demo_001" \
  http://localhost:8000/process)

echo $RESPONSE | jq .

# 4. Extract session ID and get feedback audio
SESSION_ID=$(echo $RESPONSE | jq -r '.audio_feedback_path' | sed 's/.*\///' | sed 's/\.mp3//')
echo "Downloading feedback audio for session: $SESSION_ID"
curl http://localhost:8000/audio/demo_001 -o feedback.mp3

# 5. Play audio
ffplay feedback.mp3
```

### Python Client Example

```python
import requests

# Process audio
with open('recording.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/process',
        files={'file': f},
        params={'session_id': 'py_session_001'},
        timeout=60
    )

result = response.json()
print(f"Transcript: {result['user_transcript']}")
print(f"Feedback: {result['native_feedback']}")

# Get audio
audio = requests.get(
    'http://localhost:8000/audio/py_session_001'
)
with open('feedback.mp3', 'wb') as f:
    f.write(audio.content)
```

---

## Testing

### Using Swagger UI

Interactive API testing available at:
```
http://localhost:8000/docs
```

### Using ReDoc

Alternative API documentation at:
```
http://localhost:8000/redoc
```

### Command Line Testing

```bash
# Health check
curl -v http://localhost:8000/health

# Process with real audio
curl -X POST \
  -F "file=@test.wav" \
  -v \
  http://localhost:8000/process

# Get config
curl http://localhost:8000/config | jq .
```

---

## Performance Tips

1. **Use base.en Whisper model** for fastest processing
2. **Use mistral LLM** for faster responses than llama3
3. **Keep audio clips short** (5-15 seconds ideal)
4. **Run on GPU** for 3-5x faster processing
5. **Batch requests** for multiple transcriptions
6. **Cache feedback** to avoid reprocessing

---

## Troubleshooting API Issues

**Q: API returns 500 error**
A: Check backend logs for specific error. Likely causes:
- Ollama not running
- Out of GPU memory
- Model not downloaded

**Q: Processing takes > 30 seconds**
A: Try smaller models or shorter audio clips

**Q: Audio feedback not synthesizing**
A: Ensure TTS voice is valid. Check system audio permissions.

**Q: Session audio returns 404**
A: Verify session_id matches, check feedback_storage directory exists

---

## OpenAPI Specification

Full OpenAPI/Swagger specification available at:
```
http://localhost:8000/openapi.json
```

---

**Last Updated:** January 2026
**API Version:** 1.0.0
