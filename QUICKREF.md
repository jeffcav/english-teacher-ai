# PhonicFlow - Quick Reference

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.10+
- Ollama installed (https://ollama.ai)

### Setup
```bash
cd /home/jeff/dev/pg/english
./setup.sh  # or python quickstart.py
```

### Run
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Download model
ollama pull llama3

# Terminal 3: Start Backend
source venv/bin/activate
python -m uvicorn app.backend.main:app --reload

# Terminal 4: Start Frontend
source venv/bin/activate
streamlit run app/frontend/streamlit_app.py
```

Visit: http://localhost:8501

---

## 📝 Common Tasks

### Check API Status
```bash
curl http://localhost:8000/health
```

### Process Audio File
```bash
curl -X POST \
  -F "file=@audio.wav" \
  -F "session_id=test_001" \
  http://localhost:8000/process
```

### Change Models
Edit `.env`:
```env
WHISPER_MODEL=medium.en     # For better accuracy
LLM_NAME=mistral            # For faster responses
```

### Use Different TTS Voice
```env
TTS_VOICE=en-GB-SoniaNeural  # British accent
TTS_VOICE=en-AU-NatashaNeural # Australian accent
```

---

## 🔧 Architecture Quick Reference

```
User (Streamlit UI)
    ↓ (HTTP POST - audio file)
FastAPI Backend
    ├→ Whisper (STT) - speech to text
    ├→ Ollama (LLM) - text analysis & coaching
    └→ Edge-TTS (TTS) - text to speech
    ↓ (HTTP Response)
User (feedback display)
```

---

## 📁 Project Structure

```
app/
  ├── backend/       → FastAPI server
  ├── frontend/      → Streamlit UI
  ├── core/          → Orchestration logic
  │   ├── architect.py   → Main pipeline
  │   └── config.py      → Settings
  ├── models/        → Pydantic schemas
  └── feedback_storage/  → Generated audio
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| API not found | Check: `curl http://localhost:8000/health` |
| Model not downloading | Run: `ollama pull llama3` |
| Out of memory | Use: `WHISPER_MODEL=tiny.en` |
| Slow processing | Try: `LLM_NAME=mistral` |
| Audio format error | Convert to WAV: `ffmpeg -i input.ogg -acodec pcm_s16le -ar 16000 output.wav` |

---

## 📚 Documentation Files

- **README.md** - Full documentation
- **project.md** - Original specification
- **example_client.py** - Python API client
- **quickstart.py** - Interactive setup
- **.env.example** - Configuration template

---

## 🎯 Key Features

✅ Local AI processing (no API keys needed)
✅ Real-time phonetic analysis
✅ Grammar and syntax feedback
✅ Natural audio synthesis
✅ Clean web interface
✅ Containerized deployment ready

---

## 💡 Tips

- First run may download ~1GB of models
- Use `base.en` Whisper model for speed
- `llama3` gives better coaching than smaller models
- Different TTS voices have different characteristics
- Check `/docs` endpoint for interactive API testing

---

**Happy learning!** 🎤✨
