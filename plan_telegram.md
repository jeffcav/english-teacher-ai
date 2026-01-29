# Telegram Bot Integration Architecture for PhonicFlow

## Executive Summary

This document outlines the architectural design for integrating a Telegram bot with the PhonicFlow English pronunciation tutor backend. The bot will enable users to interact with the platform via Telegram, handling audio submissions, receiving coaching feedback, and managing conversation sessions—all through a private network connection.

---

## 1. Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEGRAM PLATFORM                        │
│              (Telegram Servers - Public Cloud)               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ HTTPS Webhook
                              │ (Incoming Updates)
                              │
                    ┌─────────▼─────────┐
                    │  Telegram Bot API │
                    │  (python-telegram-│
                    │      bot library) │
                    └────────┬──────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        │         PRIVATE NETWORK                 │
        │    (Secure Internal Connection)         │
        │                    │                    │
        │    ┌───────────────▼──────────────────┐ │
        │    │   Telegram Bot Service           │ │
        │    │   (Local Bot Handler)            │ │
        │    │  - Message Processing            │ │
        │    │  - Audio Handling                │ │
        │    │  - State Management              │ │
        │    └───────────────┬──────────────────┘ │
        │                    │                    │
        │    ┌───────────────▼──────────────────┐ │
        │    │   Backend API                    │ │
        │    │   (main.py - FastAPI)            │ │
        │    │  - /process (audio endpoint)     │ │
        │    │  - /conversation (history)       │ │
        │    │  - /audio (playback)             │ │
        │    │  - /feedback (responses)         │ │
        │    └───────────────┬──────────────────┘ │
        │                    │                    │
        │    ┌───────────────▼──────────────────┐ │
        │    │   Session Storage                │ │
        │    │   (feedback_storage/)            │ │
        │    └──────────────────────────────────┘ │
        │                                          │
        └──────────────────────────────────────────┘
```

### 1.2 Key Design Principles

- **Separation of Concerns**: Bot logic separated from backend API
- **Stateless Processing**: Each request can be processed independently
- **Private Network**: No public endpoints exposed for bot webhook
- **Polling Mechanism**: Uses Telegram getUpdates instead of webhooks
- **Session Management**: Maintains conversation context per user
- **Error Resilience**: Graceful degradation and retry logic

---

## 2. Component Architecture

### 2.1 Telegram Bot Service (`app/telegram_bot/`)

#### Directory Structure
```
app/telegram_bot/
├── __init__.py
├── bot.py                 # Main bot handler
├── handlers/
│   ├── __init__.py
│   ├── message_handler.py # Text message processing
│   ├── audio_handler.py   # Audio file processing
│   └── callback_handler.py # Button callbacks
├── utils/
│   ├── __init__.py
│   ├── audio_converter.py # OGG to WAV conversion
│   ├── session_manager.py # User session tracking
│   └── api_client.py      # Backend API communication
└── config.py              # Bot configuration
```

#### 2.1.1 Core Bot Handler (`bot.py`)

**Responsibilities:**
- Initialize Telegram bot client
- Start polling loop for incoming updates
- Route updates to appropriate handlers
- Manage bot lifecycle

**Key Methods:**
```python
- __init__(token, backend_url, poll_interval)
- start_polling()
- stop_polling()
- handle_message(update)
- handle_audio(update)
- handle_callback(update)
- _log_update(update)
```

#### 2.1.2 Message Handler (`message_handler.py`)

**Responsibilities:**
- Process text messages from users
- Handle commands (/start, /help, /status, /history)
- Validate message format
- Route to backend or respond locally

**Supported Commands:**
- `/start` - Initialize new conversation session
- `/help` - Display available commands
- `/status` - Show current session status
- `/history` - Retrieve conversation history
- `/new` - Start new conversation
- `/feedback` - Get last feedback
- `text input` - Send as conversational input

#### 2.1.3 Audio Handler (`audio_handler.py`)

**Responsibilities:**
- Intercept audio messages from Telegram
- Download OGG audio files from Telegram servers
- Convert OGG to WAV format
- Submit to backend `/process` endpoint
- Store audio metadata for session

**Flow:**
1. Receive audio message with file_id
2. Download from Telegram CDN
3. Convert OGG → WAV
4. Extract session_id from user state
5. POST to backend with /process endpoint
6. Return feedback to user

#### 2.1.4 API Client (`api_client.py`)

**Responsibilities:**
- Encapsulate all backend communication
- Handle HTTP requests with retry logic
- Timeout management
- Error parsing and conversion

**Methods:**
```python
- process_audio(session_id, audio_bytes) → response
- get_conversation_history(session_id) → history
- get_feedback_audio(session_id, audio_type) → bytes
- clear_session(session_id) → bool
- health_check() → bool
```

#### 2.1.5 Session Manager (`session_manager.py`)

**Responsibilities:**
- Track active user sessions
- Map Telegram user_id to backend session_id
- Persist session state (Redis or JSON file)
- Handle session expiration

**Data Structure:**
```python
{
  "telegram_user_id": {
    "session_id": "uuid",
    "created_at": timestamp,
    "last_activity": timestamp,
    "conversation_turns": int,
    "language": "en/pt",
    "state": "active/idle/archived"
  }
}
```

#### 2.1.6 Audio Converter (`audio_converter.py`)

**Responsibilities:**
- Convert Telegram OGG audio to WAV
- Handle various audio qualities
- Apply error handling for corrupted files
- Optimize file size if needed

**Dependencies:**
- `pydub` - Audio conversion
- `ffmpeg` - Backend codec support

---

### 2.2 Backend Integration Points

#### 2.2.1 Modified FastAPI Endpoints

**Existing Endpoints (No Changes Required):**
- `POST /process` - Already accepts audio files
- `GET /conversation/{session_id}` - History retrieval
- `GET /audio/{session_id}` - Audio playback
- `DELETE /conversation/{session_id}` - Session cleanup

**New Optional Endpoints for Bot:**
- `POST /bot/session` - Create new session
- `GET /bot/status` - Health check
- `POST /bot/metrics` - Log bot events

#### 2.2.2 Backend Configuration

Add to `requirements.txt`:
```
python-telegram-bot==20.0
pydub==0.25.1
requests==2.31.0
redis==5.0.0  # Optional: for distributed session management
```

Add to `app/core/config.py`:
```python
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_ENABLED = os.getenv("TELEGRAM_BOT_ENABLED", "false") == "true"
BOT_POLLING_INTERVAL = int(os.getenv("BOT_POLLING_INTERVAL", "1"))
BOT_TIMEOUT = int(os.getenv("BOT_TIMEOUT", "30"))
BOT_PRIVATE_KEY = os.getenv("BOT_PRIVATE_KEY", "")  # For security
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
```

---

## 3. Data Flow

### 3.1 Audio Submission Flow

```
User (Telegram)
    │
    ├─► Send audio message
    │
    └──► Telegram Bot API
         │
         ├─► Download OGG file
         │
         ├─► Convert OGG → WAV
         │
         ├─► Prepare multipart request
         │
         └──► Backend POST /process
              │
              ├─► STT (Whisper)
              │
              ├─► LLM (Ollama)
              │
              ├─► Translation (deep-translator)
              │
              ├─► TTS (gTTS) → Portuguese
              │
              └──► Store in feedback_storage/
                   │
                   └──► Return to bot
                        │
                        └──► Format message
                             │
                             └──► Send to user
```

### 3.2 Conversation History Flow

```
User requests /history
    │
    └──► Bot API Client
         │
         └──► Backend GET /conversation/{session_id}
              │
              └──► Return conversation turns
                   │
                   └──► Bot formats as message
                        │
                        └──► Send paginated to user
```

### 3.3 Audio Playback Flow

```
User requests feedback audio
    │
    └──► Bot API Client
         │
         └──► Backend GET /audio/{session_id}?audio_type=coaching
              │
              └──► Return WAV bytes
                   │
                   └──► Bot sends as audio file
                        │
                        └──► User receives playback
```

---

## 4. Implementation Details

### 4.1 Bot Initialization

**File: `app/telegram_bot/bot.py`**

```python
from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
import logging

class PhonicFlowBot:
    def __init__(self, token: str, backend_url: str):
        self.token = token
        self.backend_url = backend_url
        self.bot = Bot(token=token)
        self.api_client = APIClient(backend_url)
        self.session_manager = SessionManager()
        self.logger = logging.getLogger(__name__)
    
    def start_polling(self):
        """Start long-polling for updates"""
        self.logger.info("Starting Telegram bot polling...")
        self.updater = Updater(token=self.token)
        
        # Register handlers
        dp = self.updater.dispatcher
        dp.add_handler(CommandHandler("start", self._handle_start))
        dp.add_handler(CommandHandler("help", self._handle_help))
        dp.add_handler(CommandHandler("history", self._handle_history))
        dp.add_handler(MessageHandler(Filters.audio, self._handle_audio))
        dp.add_handler(MessageHandler(Filters.text, self._handle_text))
        
        # Start polling
        self.updater.start_polling(poll_interval=1, timeout=30)
        self.logger.info("Bot polling started successfully")
    
    def stop_polling(self):
        """Stop bot polling gracefully"""
        self.logger.info("Stopping bot polling...")
        self.updater.stop()
```

### 4.2 Audio Handler Implementation

**File: `app/telegram_bot/handlers/audio_handler.py`**

```python
import io
from pydub import AudioSegment

async def handle_audio(self, update: Update, context):
    """Process audio file from Telegram"""
    user_id = update.effective_user.id
    audio_file = update.message.audio or update.message.voice
    
    try:
        # Get or create session for user
        session_id = self.session_manager.get_or_create_session(user_id)
        
        # Download audio from Telegram
        file = await self.bot.get_file(audio_file.file_id)
        audio_bytes = await file.download_as_bytearray()
        
        # Convert OGG to WAV
        audio_wav = self._convert_ogg_to_wav(audio_bytes)
        
        # Send to backend
        response = await self.api_client.process_audio(
            session_id=session_id,
            audio_bytes=audio_wav
        )
        
        # Format and send response
        feedback = response.get('coaching_feedback', '')
        portuguese = response.get('coaching_feedback_portuguese', '')
        
        message = f"📝 **Coaching Feedback**\n\n{feedback}"
        if portuguese:
            message += f"\n\n🇧🇷 **Portuguese**\n{portuguese}"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode="Markdown"
        )
        
        # Send audio files if available
        if response.get('coaching_audio_path'):
            with open(response['coaching_audio_path'], 'rb') as audio:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio,
                    caption="🔊 Coaching Audio"
                )
    
    except Exception as e:
        self.logger.error(f"Error processing audio: {str(e)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Error processing audio. Please try again."
        )

def _convert_ogg_to_wav(self, audio_bytes: bytes) -> bytes:
    """Convert OGG audio to WAV format"""
    audio = AudioSegment.from_ogg(io.BytesIO(audio_bytes))
    wav_buffer = io.BytesIO()
    audio.export(wav_buffer, format="wav")
    return wav_buffer.getvalue()
```

### 4.3 Session Management

**File: `app/telegram_bot/utils/session_manager.py`**

```python
import json
import os
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, storage_dir: str = "app/feedback_storage"):
        self.storage_dir = storage_dir
        self.sessions_file = os.path.join(storage_dir, "telegram_sessions.json")
        self.sessions = self._load_sessions()
    
    def get_or_create_session(self, telegram_user_id: int) -> str:
        """Get existing session or create new one"""
        if telegram_user_id in self.sessions:
            session = self.sessions[telegram_user_id]
            session['last_activity'] = datetime.now().isoformat()
            self._save_sessions()
            return session['session_id']
        
        # Create new session
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[telegram_user_id] = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'conversation_turns': 0,
            'state': 'active'
        }
        self._save_sessions()
        return session_id
    
    def _load_sessions(self) -> dict:
        """Load sessions from file"""
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_sessions(self):
        """Save sessions to file"""
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)
```

### 4.4 Configuration File

**File: `app/telegram_bot/config.py`**

```python
import os

class TelegramConfig:
    # Bot credentials
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Backend connection
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
    BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "30"))
    
    # Polling settings
    POLLING_INTERVAL = int(os.getenv("BOT_POLLING_INTERVAL", "1"))
    POLLING_TIMEOUT = int(os.getenv("BOT_POLLING_TIMEOUT", "30"))
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv("BOT_RATE_LIMIT", "true") == "true"
    RATE_LIMIT_MESSAGES_PER_MINUTE = int(os.getenv("BOT_RATE_LIMIT_MPM", "30"))
    
    # Session management
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SESSION_STORAGE_PATH = os.getenv("SESSION_STORAGE_PATH", "app/feedback_storage")
    
    # Audio settings
    MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "20"))
    SUPPORTED_AUDIO_FORMATS = ["ogg", "wav", "mp3"]
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("BOT_LOG_FILE", "logs/telegram_bot.log")
```

---

## 5. Deployment Architecture

### 5.1 Local Deployment (Private Network)

```
┌─────────────────────────────────────────────────────┐
│           Docker Compose Setup                      │
│                                                      │
│  services:                                          │
│    - backend (FastAPI on port 8000)                │
│    - telegram_bot (Polling service)                │
│    - streamlit_app (Streamlit on port 8501)        │
│    - ollama (LLM server on port 11434)             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 Docker Setup

**File: `docker-compose.yml` (Add Telegram Service)**

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_BASE_URL=http://localhost:8000
      - TELEGRAM_BOT_ENABLED=true
    networks:
      - backend

  telegram_bot:
    build:
      context: .
      dockerfile: Dockerfile.telegram_bot
    depends_on:
      - backend
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - BACKEND_URL=http://backend:8000
      - LOG_LEVEL=INFO
      - BOT_POLLING_INTERVAL=1
    networks:
      - backend
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    depends_on:
      - backend
    environment:
      - API_BASE_URL=http://backend:8000
    networks:
      - backend

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

**File: `Dockerfile.telegram_bot`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY logs/ ./logs/

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "app.telegram_bot.main"]
```

### 5.3 Environment Variables

**File: `.env.telegram`**

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_BOT_ENABLED=true

# Backend Configuration
BACKEND_URL=http://localhost:8000
BACKEND_TIMEOUT=30

# Bot Polling
BOT_POLLING_INTERVAL=1
BOT_POLLING_TIMEOUT=30

# Rate Limiting
BOT_RATE_LIMIT=true
BOT_RATE_LIMIT_MPM=30

# Session Management
SESSION_TIMEOUT_HOURS=24
SESSION_STORAGE_PATH=app/feedback_storage

# Audio Settings
MAX_AUDIO_SIZE_MB=20

# Logging
LOG_LEVEL=INFO
BOT_LOG_FILE=logs/telegram_bot.log
```

---

## 6. Security Architecture

### 6.1 Network Security

- **Private Network Isolation**: Bot and backend communicate on internal Docker network
- **No Public Endpoints**: Bot uses polling (pull) instead of webhook (push)
- **Encrypted Communication**: HTTPS for Telegram API, HTTP for internal backend (add TLS if needed)

### 6.2 Authentication & Authorization

**Bot Token Security:**
- Store in environment variables only
- Never commit to repository
- Rotate periodically
- Use `.env` files with git ignore

**Session Security:**
- Map Telegram user_id to backend session_id
- Expire sessions after 24 hours
- Validate session on every request
- Log all audio submissions

**Rate Limiting:**
- Implement per-user rate limits (30 messages/minute)
- Use Redis for distributed rate limiting (optional)
- Return 429 status for exceeded limits

### 6.3 Data Privacy

- Audio files deleted after processing
- Conversation history stored locally only
- No Telegram user data sent to third parties
- GDPR compliance: Implement `/delete` command
- Comply with Telegram Bot API terms

---

## 7. Error Handling & Resilience

### 7.1 Retry Strategy

```python
async def process_with_retry(self, func, max_retries=3, backoff=2):
    """Exponential backoff retry mechanism"""
    for attempt in range(max_retries):
        try:
            return await func()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = backoff ** attempt
                await asyncio.sleep(wait_time)
            else:
                raise
```

### 7.2 Graceful Degradation

- **Audio Conversion Failure**: Send text-only feedback
- **Backend Timeout**: Notify user with "Please try again"
- **Network Disconnection**: Queue messages, retry when connection restored
- **Session Expiry**: Create new session, notify user

### 7.3 Health Checks

```python
async def health_check(self):
    """Periodically verify backend connectivity"""
    try:
        response = await self.api_client.get_status()
        if response.status_code != 200:
            self.logger.error("Backend health check failed")
    except Exception as e:
        self.logger.error(f"Health check exception: {str(e)}")
```

---

## 8. Monitoring & Logging

### 8.1 Logging Strategy

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/telegram_bot.log'),
        logging.StreamHandler()
    ]
)

# Log events
logger.info(f"User {user_id} submitted audio")
logger.error(f"Audio processing failed: {error}")
logger.debug(f"Session {session_id} created")
```

### 8.2 Metrics to Track

- **Throughput**: Messages/audio processed per minute
- **Latency**: Response time per request (target: <5s)
- **Error Rate**: Failed requests / total requests (target: <1%)
- **Active Sessions**: Unique users in last 24 hours
- **Backend Health**: API availability percentage

### 8.3 Log Aggregation (Optional)

```yaml
# Example: ELK Stack integration
elasticsearch:
  hosts: ["localhost:9200"]

logstash:
  input:
    file:
      path: "logs/telegram_bot.log"
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**File: `tests/telegram_bot/test_audio_handler.py`**

```python
import pytest
from app.telegram_bot.handlers.audio_handler import AudioHandler

def test_convert_ogg_to_wav():
    handler = AudioHandler()
    # Load sample OGG file
    with open("tests/samples/sample.ogg", "rb") as f:
        ogg_bytes = f.read()
    
    wav_bytes = handler._convert_ogg_to_wav(ogg_bytes)
    assert wav_bytes is not None
    assert len(wav_bytes) > 0

def test_session_manager():
    manager = SessionManager()
    session_id = manager.get_or_create_session(user_id=123)
    assert session_id is not None
    
    session_id_2 = manager.get_or_create_session(user_id=123)
    assert session_id == session_id_2
```

### 9.2 Integration Tests

```python
@pytest.mark.asyncio
async def test_audio_submission_flow():
    """Test complete audio submission flow"""
    bot = PhonicFlowBot(token="test_token", backend_url="http://localhost:8000")
    
    # Create mock update with audio
    update = create_mock_audio_update()
    
    # Process audio
    response = await bot.handle_audio(update, context=None)
    
    # Verify response contains feedback
    assert "feedback" in response
```

### 9.3 Load Testing

```python
# Using locust for load testing
from locust import HttpUser, task

class TelegramBotLoadTest(HttpUser):
    @task
    def submit_audio(self):
        with open("sample_audio.wav", "rb") as f:
            self.client.post("/process", files={"file": f})
```

---

## 10. Implementation Roadmap

### Phase 1: Core Bot (Week 1)
- [x] Create bot service structure
- [x] Implement message handler
- [x] Implement audio handler
- [x] Connect to backend /process endpoint
- [x] Setup logging and error handling

### Phase 2: Features (Week 2)
- [ ] Implement /history command
- [ ] Implement /status command
- [ ] Add session management
- [ ] Add rate limiting
- [ ] Implement audio playback

### Phase 3: Integration (Week 3)
- [ ] Docker containerization
- [ ] Integrate into docker-compose
- [ ] Environment variable management
- [ ] Health checks

### Phase 4: Testing & Deployment (Week 4)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load testing
- [ ] Documentation
- [ ] Production deployment

---

## 11. API Contract Between Bot and Backend

### 11.1 Audio Processing Endpoint

**Request:**
```
POST /process
Content-Type: multipart/form-data

Headers:
  session_id: <uuid>

Body:
  file: <WAV binary data>
```

**Response:**
```json
{
  "user_transcript": "hello how are you",
  "coaching_feedback": "Your pronunciation is clear...",
  "coaching_feedback_portuguese": "Sua pronúncia está clara...",
  "conversational_response": "I'm doing well, thanks for asking...",
  "conversational_response_portuguese": "Estou bem, obrigado...",
  "coaching_audio_path": "/path/to/coaching_audio.wav",
  "conversational_audio_path": "/path/to/conversational_audio.wav"
}
```

### 11.2 Conversation History Endpoint

**Request:**
```
GET /conversation/{session_id}

Headers:
  session_id: <uuid>
```

**Response:**
```json
{
  "session_id": "uuid",
  "history": [
    {
      "user": "transcript text",
      "conversational": "response text",
      "coaching": "coaching feedback",
      "timestamp": "2026-01-28T12:00:00"
    }
  ]
}
```

### 11.3 Audio Retrieval Endpoint

**Request:**
```
GET /audio/{session_id}?audio_type=coaching

Parameters:
  audio_type: coaching | conversational
```

**Response:**
```
Content-Type: audio/wav
Body: <WAV binary data>
```

---

## 12. Configuration Examples

### 12.1 Development Environment

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmnoPQRstuvwxyzABCdefGH
BACKEND_URL=http://localhost:8000
BOT_POLLING_INTERVAL=1
LOG_LEVEL=DEBUG
```

### 12.2 Production Environment

```bash
TELEGRAM_BOT_TOKEN=${SECURE_TOKEN_FROM_VAULT}
BACKEND_URL=http://backend:8000
BOT_POLLING_INTERVAL=1
BOT_POLLING_TIMEOUT=30
LOG_LEVEL=INFO
SESSION_TIMEOUT_HOURS=24
BOT_RATE_LIMIT=true
BOT_RATE_LIMIT_MPM=30
```

---

## 13. Troubleshooting Guide

### 13.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Bot not responding | Token invalid | Verify token in `.env` |
| Backend connection timeout | Network issue | Check private network connectivity |
| Audio conversion fails | Missing ffmpeg | Install ffmpeg: `apt-get install ffmpeg` |
| Rate limit exceeded | Too many messages | Implement backoff in client |
| Session expired | 24-hour timeout | User calls `/start` to create new session |

### 13.2 Debug Commands

```bash
# Check bot connectivity
python -m app.telegram_bot.health_check

# View recent logs
tail -f logs/telegram_bot.log

# Test backend connectivity
curl http://localhost:8000/docs

# Monitor active sessions
python -m app.telegram_bot.session_monitor
```

---

## 14. Future Enhancements

### 14.1 Advanced Features
- [ ] Multi-language support
- [ ] User preferences (language, speaking pace)
- [ ] Scheduled practice sessions
- [ ] Performance analytics dashboard
- [ ] Integration with other messaging platforms (WhatsApp, Discord)

### 14.2 Scalability Improvements
- [ ] Redis session caching
- [ ] Distributed rate limiting
- [ ] Message queuing (RabbitMQ, Kafka)
- [ ] Horizontal scaling with load balancer
- [ ] Database migration from JSON files

### 14.3 AI Enhancements
- [ ] Custom pronunciation error detection
- [ ] Personalized learning recommendations
- [ ] Accent-specific coaching
- [ ] Real-time phonetic analysis

---

## 15. References & Dependencies

### 15.1 Key Libraries

```
python-telegram-bot==20.0       # Telegram Bot API client
pydub==0.25.1                   # Audio conversion
requests==2.31.0                # HTTP client
fastapi==0.104.0                # Backend framework (existing)
asyncio                          # Async support (Python stdlib)
redis==5.0.0                     # Session caching (optional)
```

### 15.2 External Services

- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Telegram Client Library**: https://github.com/python-telegram-bot/python-telegram-bot
- **Docker**: https://docs.docker.com

### 15.3 Related Documentation

- Backend API: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Audio Processing: See [SPEAK_IMPLEMENTATION_NOTES.md](SPEAK_IMPLEMENTATION_NOTES.md)
- Deployment: See [README.md](README.md)

---

## Conclusion

This architecture provides a robust, secure, and scalable integration between the PhonicFlow backend and Telegram. The bot operates entirely within a private network, ensuring data privacy while leveraging Telegram's massive user base. The modular design allows for easy extension and maintenance, with clear separation of concerns between bot logic and backend API operations.

**Key Takeaways:**
- ✅ Polling-based architecture (no public webhooks)
- ✅ Private network communication
- ✅ Stateless processing with session management
- ✅ Comprehensive error handling and resilience
- ✅ Production-ready monitoring and logging
- ✅ Extensible for future platforms and features
