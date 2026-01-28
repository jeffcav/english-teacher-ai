# PhonicFlow - AI English Tutor
## Complete Implementation Guide

---

## 📋 Table of Contents
1. [Project Overview](#overview)
2. [System Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Application](#running)
7. [API Endpoints](#endpoints)
8. [Usage Guide](#usage)
9. [Troubleshooting](#troubleshooting)

---

## <a name="overview"></a>📖 Project Overview

**PhonicFlow** is a web-based AI English tutor that provides real-time phonetic analysis, grammatical refinement, and auditory feedback without relying on expensive cloud APIs. It uses three core AI components working in harmony:

- **OpenAI Whisper**: Converts speech to text with high accuracy
- **Ollama (Llama 3/Mistral)**: Analyzes transcriptions and provides linguistic coaching
- **Edge-TTS**: Synthesizes natural-sounding English feedback

The system operates on a **Request-Response Pipeline** coordinated by a Python FastAPI backend with a Streamlit web interface.

---

## <a name="architecture"></a>🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PHONIC FLOW ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           STREAMLIT FRONTEND (Web UI)                 │  │
│  │  - Audio recording & file upload                      │  │
│  │  - Real-time feedback display                         │  │
│  │  - Audio playback of synthesis                        │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                      │
│                        │ HTTP (REST API)                     │
│                        ↓                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           FASTAPI BACKEND (Python)                    │  │
│  │  - Audio file handling                                │  │
│  │  - Request orchestration                              │  │
│  │  - Response formatting                                │  │
│  └──┬──────────────────────┬──────────────────────┬──────┘  │
│     │                      │                      │          │
│  STT ENGINE           LLM ENGINE             TTS ENGINE     │
│     │                      │                      │          │
│     ↓                      ↓                      ↓          │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐    │
│  │ WHISPER  │         │  OLLAMA  │         │EDGE-TTS │    │
│  │(Speech)  │         │ (Text)   │         │(Synthesis)   │
│  │ to Text  │         │ Coaching │         │         │    │
│  └──────────┘         └──────────┘         └──────────┘    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Pipeline

1. **User Input**: User records or uploads audio via Streamlit frontend
2. **Audio Capture**: File sent to FastAPI backend via HTTP POST
3. **STT Processing**: Whisper transcribes audio to text
4. **LLM Analysis**: Ollama analyzes transcript for errors and coaching
5. **TTS Synthesis**: Edge-TTS converts feedback to audio
6. **Response Return**: All results (transcript, feedback, audio) sent to frontend
7. **Display**: Streamlit displays feedback and plays audio

---

## <a name="prerequisites"></a>✅ Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows
- **Python**: 3.10 or higher
- **RAM**: Minimum 8GB (16GB+ recommended for larger Whisper models)
- **GPU**: Optional (NVIDIA CUDA recommended for faster processing)

### Required Software
1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Ollama** (LLM inference engine)
   - Download from: https://ollama.ai
   - Or via Docker: `docker pull ollama/ollama`

3. **Git** (for cloning, optional)

### Python Virtual Environment
Use a Python virtual environment to avoid package conflicts:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

## <a name="installation"></a>⚙️ Installation

### Option 1: Manual Setup (Recommended for Development)

1. **Clone or navigate to project directory:**
   ```bash
   cd /home/jeff/dev/pg/english
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   
   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Create environment configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

### Option 2: Docker Setup (Recommended for Production)

1. **Build and start containers:**
   ```bash
   docker-compose up --build
   ```

2. **Initialize Ollama with a model:**
   ```bash
   docker exec phonic_flow_ollama ollama pull llama3
   ```

---

## <a name="configuration"></a>🔧 Configuration

### Environment Variables (.env file)

```env
# API Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=True

# Frontend Configuration
API_BASE_URL=http://localhost:8000

# Model Selection
# STT Models: tiny.en, base.en, small.en, medium.en, large-v3
WHISPER_MODEL=base.en

# LLM Models: llama3, mistral, llama2, neural-chat
LLM_NAME=llama3

# TTS Voices:
# US: en-US-AndrewNeural, en-US-AmberNeural, en-US-AriaNeural
# UK: en-GB-SoniaNeural, en-GB-RyanNeural
TTS_VOICE=en-US-AndrewNeural

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
```

### Model Selection Guide

**Whisper STT Models:**
- `tiny.en`: Fastest, least accurate (~39MB)
- `base.en`: Good balance (140MB) ⭐ **Recommended for most users**
- `medium.en`: Better accuracy (769MB)
- `large-v3`: Best accuracy (2.9GB)

**LLM Models (Ollama):**
- `llama3`: Most capable (8B parameters, ~4.7GB)
- `mistral`: Fast and efficient (7B parameters, ~4GB)
- `neural-chat`: Optimized for conversations (7B parameters)

---

## <a name="running"></a>🚀 Running the Application

### Start Ollama Service

**Option A: Local Installation**
```bash
# On macOS or Linux
ollama serve

# On Windows (WSL or native)
ollama serve
```

**Option B: Docker**
```bash
docker run -d -p 11434:11434 ollama/ollama
docker exec ollama ollama pull llama3
```

### Start the Backend API

In a new terminal:
```bash
source venv/bin/activate
cd /home/jeff/dev/pg/english
python -m uvicorn app.backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: **http://localhost:8000**

API documentation (Swagger UI) at: **http://localhost:8000/docs**

### Start the Frontend

In another new terminal:
```bash
source venv/bin/activate
cd /home/jeff/dev/pg/english
streamlit run app/frontend/streamlit_app.py
```

The frontend will open at: **http://localhost:8501**

---

## <a name="endpoints"></a>📡 API Endpoints

### 1. **GET `/`** - API Information
Returns basic API details and available endpoints.

```bash
curl http://localhost:8000/
```

### 2. **GET `/health`** - System Health Check
Checks the status of all AI components.

```bash
curl http://localhost:8000/health
```

**Response:**
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

### 3. **POST `/process`** - Process Audio
Main endpoint for audio processing and feedback generation.

**Parameters:**
- `file` (multipart): Audio file (.wav, .mp3, .m4a, .flac)
- `session_id` (query, optional): Unique session identifier

**Example:**
```bash
curl -X POST \
  -F "file=@recording.wav" \
  -F "session_id=user_session_123" \
  http://localhost:8000/process
```

**Response:**
```json
{
  "user_transcript": "I want to improve my English pronunciation",
  "native_feedback": "Your sentence is well-structured! For native fluency, consider: 'I'd like to improve my English pronunciation.' The contraction 'I'd' sounds more natural in conversation.",
  "audio_feedback_path": "/app/feedback_storage/user_session_123.mp3"
}
```

### 4. **GET `/audio/{session_id}`** - Retrieve Feedback Audio
Downloads the synthesized audio feedback.

```bash
curl http://localhost:8000/audio/user_session_123 -o feedback.mp3
```

### 5. **GET `/config`** - Get Current Configuration
Returns current model and voice settings.

```bash
curl http://localhost:8000/config
```

### 6. **POST `/config`** - Update Configuration
Changes model or voice settings at runtime.

**Body:**
```json
{
  "whisper_model": "medium.en",
  "llm_name": "mistral",
  "tts_voice": "en-GB-SoniaNeural"
}
```

---

## <a name="usage"></a>💡 Usage Guide

### Basic Workflow

1. **Open the Streamlit Interface**
   - Navigate to http://localhost:8501

2. **Record Your Speech**
   - Click the microphone icon
   - Speak clearly in English (5-30 seconds recommended)
   - Upload alternative: choose an audio file

3. **Analyze Audio**
   - Click "📤 Analyze Audio" button
   - Wait for processing (typically 5-15 seconds depending on audio length)

4. **Review Feedback**
   - **Your Speech**: See what was transcribed
   - **AI Coaching**: Read the linguistic feedback
   - **Listen**: Hear the AI coach's pronunciation via the audio player

5. **Clear & Retry**
   - Click "🔄 Clear & Retry" to start again
   - Record another phrase

### Tips for Best Results

1. **Audio Quality**
   - Use a good microphone in a quiet environment
   - Speak clearly with natural pace
   - Avoid background noise

2. **Session Management**
   - Each recording generates a unique session ID
   - Feedback audio is stored in `app/feedback_storage/`
   - Old files can be cleaned up periodically

3. **Model Selection**
   - Use `base.en` for faster feedback
   - Use `medium.en` or `large-v3` for better accuracy with accents
   - Try different Ollama models for varied coaching styles

---

## <a name="troubleshooting"></a>🔍 Troubleshooting

### Issue: "API is not accessible"

**Symptoms:** Streamlit shows "❌ API is not accessible"

**Solution:**
1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```
2. Check for errors in backend terminal
3. Ensure FastAPI is started with correct port
4. Check firewall settings

### Issue: "Model not found" Error

**Symptoms:** Backend returns error about Whisper or Ollama model

**Solution for Whisper:**
```bash
# Whisper will auto-download on first use
# But you can pre-download with:
python -c "import whisper; whisper.load_model('base.en')"
```

**Solution for Ollama:**
```bash
ollama list  # Check available models
ollama pull llama3  # Download llama3
ollama pull mistral  # Download mistral
```

### Issue: "Out of Memory" Error

**Symptoms:** Processing fails or system becomes unresponsive

**Solutions:**
1. Use smaller models:
   ```env
   WHISPER_MODEL=tiny.en  # Instead of large-v3
   LLM_NAME=mistral       # Instead of llama3
   ```

2. Reduce batch processing
3. Close other applications
4. Upgrade system RAM or GPU VRAM

### Issue: Slow Processing

**Symptoms:** Audio processing takes > 30 seconds

**Solutions:**
1. Use smaller models (tiny.en or base.en)
2. Enable GPU acceleration (if NVIDIA GPU available)
3. Reduce audio length (15 seconds max)
4. Check system resource usage with `top` or `htop`

### Issue: Frontend Won't Connect to Backend

**Symptoms:** Streamlit loads but shows persistent API errors

**Solution:**
1. Verify `API_BASE_URL` in .env:
   ```env
   API_BASE_URL=http://localhost:8000
   ```
2. Check if backend is accessible:
   ```bash
   curl http://localhost:8000/health
   ```
3. For remote deployment, update to proper URL:
   ```env
   API_BASE_URL=http://your-server.com:8000
   ```

### Issue: Audio File Not Supported

**Symptoms:** "Unsupported audio format" error

**Solution:**
Upload audio in supported formats: **WAV, MP3, M4A, FLAC**

Convert with ffmpeg if needed:
```bash
ffmpeg -i input.ogg -acodec libmp3lame -ab 192k output.mp3
```

---

## 📊 Project Structure

```
/home/jeff/dev/pg/english/
├── project.md                  # Original specification
├── requirements.txt            # Python dependencies
├── setup.sh                   # Automated setup script
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Multi-container orchestration
├── .env.example              # Environment template
├── README.md                 # This file
│
└── app/
    ├── backend/
    │   ├── __init__.py
    │   └── main.py           # FastAPI application
    │
    ├── frontend/
    │   ├── __init__.py
    │   └── streamlit_app.py  # Streamlit UI
    │
    ├── core/
    │   ├── __init__.py
    │   ├── config.py         # Configuration management
    │   └── architect.py      # Main orchestration logic
    │
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py        # Pydantic models
    │
    └── feedback_storage/     # Generated audio feedback files
```

---

## 🎓 Learning Resources

- **Whisper Documentation**: https://github.com/openai/whisper
- **Ollama Guide**: https://ollama.ai/library
- **FastAPI Tutorial**: https://fastapi.tiangolo.com/
- **Streamlit Docs**: https://docs.streamlit.io/

---

## 📝 License

This project is provided as-is for educational purposes.

---

## 🤝 Contributing

To improve PhonicFlow:
1. Identify issues or improvements
2. Create a test case
3. Implement the fix
4. Test thoroughly before committing

---

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs in backend terminal
3. Verify all prerequisites are installed
4. Check API health: http://localhost:8000/health

---

**Happy learning with PhonicFlow!** 🎤🚀
