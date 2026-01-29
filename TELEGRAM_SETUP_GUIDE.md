# Telegram Bot Setup & Deployment Guide

## Overview

The Telegram bot integration for PhonicFlow enables users to interact with the pronunciation tutor directly through Telegram. This guide covers setup, testing, and deployment.

---

## Prerequisites

- ✅ PhonicFlow backend running
- ✅ Docker and Docker Compose installed
- ✅ Python 3.11+ (for local testing)
- ✅ Telegram account

---

## Step 1: Create Telegram Bot

### 1.1 Get Bot Token from BotFather

1. Open Telegram and find **@BotFather**
2. Send `/start`
3. Send `/newbot`
4. Follow prompts:
   - Bot name: `PhonicFlow`
   - Username: `phonic_flow_bot` (must be unique)
5. Copy the bot token (looks like: `123456789:ABCdefGHIjklmnoPQRstuvwxyzABCdefGH`)

### 1.2 Configure Bot Settings

In BotFather:
- Send `/setcommands`
- Select your bot
- Paste:
```
start - Start new session
help - Show help
history - View conversation history
status - Check session status
new - Start new conversation
delete - Delete all data
```

---

## Step 2: Environment Setup

### 2.1 Local Development

```bash
# Copy example env file
cp .env.telegram.example .env.telegram

# Edit with your bot token
nano .env.telegram
# Set: TELEGRAM_BOT_TOKEN=your_token_here

# Load environment
export $(cat .env.telegram | grep -v '^#' | xargs)
```

### 2.2 Docker Deployment

```bash
# Create .env file for docker-compose
cat > .env << EOF
TELEGRAM_BOT_TOKEN=your_token_here
BACKEND_URL=http://backend:8000
EOF
```

---

## Step 3: Install Dependencies

### 3.1 Local Testing

```bash
# Install bot dependencies
pip install python-telegram-bot==20.0
pip install pydub==0.25.1

# Install ffmpeg (required for audio conversion)
# On Ubuntu/Debian:
sudo apt-get install ffmpeg

# On macOS:
brew install ffmpeg

# On Windows:
# Download from https://ffmpeg.org/download.html
```

### 3.2 Docker Deployment

Dependencies are automatically installed by the Dockerfile.

---

## Step 4: Run the Bot

### 4.1 Local Testing

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN='your_token_here'
export BACKEND_URL='http://localhost:8000'

# Start backend first (in another terminal)
python -m uvicorn app.backend.main:app --reload

# Run bot (in another terminal)
python -m app.telegram_bot.main
```

You should see:
```
2026-01-28 12:00:00 - app.telegram_bot.main - INFO - ============================================================
2026-01-28 12:00:00 - app.telegram_bot.main - INFO - PhonicFlow Telegram Bot Starting
2026-01-28 12:00:00 - app.telegram_bot.main - INFO - ============================================================
2026-01-28 12:00:00 - app.telegram_bot.bot - INFO - PhonicFlowBot initialized
2026-01-28 12:00:00 - app.telegram_bot.bot - INFO - Starting bot with token 123456789:...
2026-01-28 12:00:00 - app.telegram_bot.bot - INFO - Bot is running. Press Ctrl+C to stop.
```

### 4.2 Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f telegram_bot

# Stop
docker-compose down
```

---

## Step 5: Test the Bot

### 5.1 Find Your Bot on Telegram

1. Open Telegram
2. Search for `@phonic_flow_bot` (or your bot username)
3. Start chat

### 5.2 Test Commands

```
/start              # Begin
/help               # See available commands
/status             # Check session info
/history            # View past conversations
/new                # Create new conversation
/delete             # Delete your data
```

### 5.3 Test Audio Submission

1. Click microphone icon
2. Hold and record: "Hello, how are you?"
3. Release and send
4. Wait for processing (15-30 seconds)
5. Receive feedback and audio examples

---

## Step 6: Verify Integration

### 6.1 Check Backend Connectivity

```bash
# From inside container
docker-compose exec telegram_bot curl http://backend:8000/docs

# From local
curl http://localhost:8000/docs
```

### 6.2 Check Session Storage

```bash
# View created sessions
cat app/feedback_storage/telegram_sessions.json

# Example output:
{
  "123456789": {
    "session_id": "uuid-here",
    "created_at": "2026-01-28T12:00:00.000000",
    "last_activity": "2026-01-28T12:05:00.000000",
    "conversation_turns": 3,
    "state": "active"
  }
}
```

### 6.3 Check Logs

```bash
# Local testing
tail -f logs/telegram_bot.log

# Docker
docker-compose logs -f telegram_bot | grep -E "ERROR|INFO|User"
```

---

## Troubleshooting

### Issue: Bot not responding to messages

**Causes:**
- Invalid token
- Backend offline
- Bot not polling

**Solutions:**
```bash
# Verify token
echo $TELEGRAM_BOT_TOKEN

# Check backend
curl http://localhost:8000/docs

# Restart bot
python -m app.telegram_bot.main
```

### Issue: "Audio conversion fails"

**Cause:** Missing ffmpeg

**Solution:**
```bash
# Install ffmpeg
sudo apt-get install ffmpeg

# Verify
ffmpeg -version
```

### Issue: "Backend connection timeout"

**Cause:** Backend not running or wrong URL

**Solution:**
```bash
# Check backend is running
ps aux | grep uvicorn

# Check URL
export BACKEND_URL='http://localhost:8000'
curl http://localhost:8000/docs
```

### Issue: "Docker container exits immediately"

**Solution:**
```bash
# Check logs
docker-compose logs telegram_bot

# Rebuild
docker-compose build telegram_bot

# Run with logging
docker-compose up --no-detach telegram_bot
```

---

## File Structure

```
app/telegram_bot/
├── __init__.py                    # Package init
├── config.py                      # Configuration
├── bot.py                         # Main bot class
├── main.py                        # Entry point
├── handlers/
│   ├── __init__.py
│   ├── message_handler.py        # Command handling
│   └── audio_handler.py          # Audio processing
└── utils/
    ├── __init__.py
    ├── api_client.py             # Backend communication
    ├── session_manager.py        # Session tracking
    └── audio_converter.py        # Audio conversion
```

---

## Key Features Implemented

✅ **Commands:**
- `/start` - Initialize session
- `/help` - Show commands
- `/history` - View conversations
- `/status` - Session info
- `/new` - New conversation
- `/delete` - GDPR deletion

✅ **Audio Processing:**
- Accept OGG files from Telegram
- Convert to WAV
- Submit to backend
- Return feedback with audio

✅ **Session Management:**
- Map Telegram users to backend sessions
- Persist sessions locally
- Track conversation turns

✅ **Error Handling:**
- Graceful degradation
- Retry logic
- User-friendly error messages

✅ **Monitoring:**
- Comprehensive logging
- Health checks
- Session cleanup

---

## Configuration Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Required | Bot authentication token |
| `BACKEND_URL` | `http://localhost:8000` | Backend API URL |
| `BACKEND_TIMEOUT` | `30` | Request timeout (seconds) |
| `BOT_POLLING_INTERVAL` | `1` | Poll frequency (seconds) |
| `BOT_POLLING_TIMEOUT` | `30` | Long poll timeout (seconds) |
| `SESSION_TIMEOUT_HOURS` | `24` | Session expiry (hours) |
| `MAX_AUDIO_SIZE_MB` | `20` | Max audio file size |
| `LOG_LEVEL` | `INFO` | Logging level |
| `BOT_LOG_FILE` | `logs/telegram_bot.log` | Log file path |

---

## Production Checklist

- [ ] Bot token stored in secure environment
- [ ] Backend API running and accessible
- [ ] Docker Compose configured with bot service
- [ ] Volumes mounted for session storage
- [ ] Logging configured for monitoring
- [ ] ffmpeg installed in container
- [ ] Health checks passing
- [ ] Test audio submission working
- [ ] Session persistence verified
- [ ] Error handling tested

---

## Next Steps

1. **Monitor Performance:**
   ```bash
   docker-compose logs -f telegram_bot | grep -E "User|Error|submitted"
   ```

2. **Scale Users:**
   - Implement Redis for distributed sessions (optional)
   - Add message queuing for high load

3. **Enhance Features:**
   - User preferences (language, speed)
   - Performance analytics
   - Scheduled practice

4. **Integrate Other Platforms:**
   - WhatsApp bot
   - Discord bot
   - Web API

---

## Support

For issues:
1. Check logs: `docker-compose logs telegram_bot`
2. Verify backend: `curl http://localhost:8000/docs`
3. Test token: Get new one from @BotFather
4. Review plan_telegram.md for architecture details

---

## Related Documentation

- [plan_telegram.md](plan_telegram.md) - Full architecture
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Backend API
- [README.md](README.md) - Project overview
