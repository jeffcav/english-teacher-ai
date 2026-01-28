# Multi-Turn Conversation Feature

## Overview
PhonicFlow now supports **continuous conversations** where the LLM maintains context from previous exchanges. Users can continue a conversation across multiple turns, with the AI tutor remembering and building upon previous corrections and responses.

## Architecture Changes

### Backend Implementation

#### 1. Conversation History Storage (`app/core/architect.py`)

**New Directory:**
```
app/feedback_storage/
├── conversations/
│   ├── session_1234567890.json
│   ├── session_1234567891.json
│   └── ...
```

**JSON Format:**
```json
[
  {
    "user": "I am very happy today",
    "coaching": "Great! Try emphasizing 'happy' to show emotion. Pronunciation was clear.",
    "conversational": "That's wonderful! What made you so happy today?"
  },
  {
    "user": "I got a new job",
    "coaching": "Excellent! Consider: 'I got a new job' - well done! Your stress placement was natural.",
    "conversational": "Oh wow, congratulations! That's amazing news! How are you feeling about it?"
  }
]
```

#### 2. New Methods in `PhonicFlowArchitect`

**`get_conversation_history(session_id: str) -> List[Dict]`**
- Retrieves all previous turns for a session
- Returns list of conversation dictionaries
- Returns empty list if no history exists

**`save_conversation_turn(session_id, user_transcript, coaching_feedback, conversational_response) -> None`**
- Saves current turn to JSON file
- Appends to existing history
- Called after successful TTS synthesis

**`clear_conversation_history(session_id: str) -> bool`**
- Deletes conversation file
- Called when user starts new conversation
- Returns success status

#### 3. Enhanced LLM Prompt

**With Context Injection:**
```python
prompt = f"""Analyze the user's speech and provide TWO separate responses.

CONVERSATION CONTEXT (previous exchanges):
Turn 1:
  User: I am very happy today
  Your conversational response: That's wonderful! What made you so happy?

CURRENT USER INPUT: "I got a new job"

RESPONSE FORMAT (clearly separate both parts):
---COACHING---
Provide feedback on pronunciation, grammar, and naturalness. Reference context if relevant.

---CONVERSATION---
Respond naturally to what the user said, as if you were their friend having a conversation. 
Use context from previous exchanges. Keep it natural and conversational (under 50 words).
"""
```

### Frontend Implementation

#### 1. Conversation History Display

**New UI Section:**
```
📚 Conversation History (expandable)
├─ Turn 1:
│  ├─ 🗣️ You said: "I am very happy today"
│  ├─ 📝 Coaching: "Great! Try emphasizing..."
│  └─ 💬 Response: "That's wonderful!..."
├─ Turn 2:
│  ├─ 🗣️ You said: "I got a new job"
│  ├─ 📝 Coaching: "Excellent! Consider..."
│  └─ 💬 Response: "Oh wow, congratulations!..."
└─ [Current Response Section]
```

#### 2. Conversation Management Buttons

**Clear History:**
- Removes all previous turns from conversation file
- Resets context for future inputs
- Doesn't affect other sessions

**New Conversation:**
- Generates new session ID
- Clears current transcript and responses
- Allows user to start fresh conversation

### API Changes

#### 1. New Endpoints

**`GET /conversation/{session_id}`**
```bash
curl http://localhost:8000/conversation/session_123

Response:
{
  "session_id": "session_123",
  "conversation_count": 2,
  "history": [
    {
      "user": "I am very happy today",
      "coaching": "Great!...",
      "conversational": "That's wonderful!..."
    },
    {
      "user": "I got a new job",
      "coaching": "Excellent!...",
      "conversational": "Oh wow,..."
    }
  ]
}
```

**`DELETE /conversation/{session_id}`**
```bash
curl -X DELETE http://localhost:8000/conversation/session_123

Response:
{
  "status": "success",
  "session_id": "session_123",
  "message": "Conversation history cleared"
}
```

#### 2. Modified `/process` Endpoint

**Behavior:**
- Automatically loads conversation history before LLM processing
- Passes last 3 turns as context (configurable)
- Saves new turn after synthesis completes

**Data Flow:**
```
POST /process
  ↓
1. Save temporary audio
  ↓
2. Transcribe to text (Whisper)
  ↓
3. Load conversation history from {session_id}.json
  ↓
4. Pass history + new input to LLM
  ↓
5. LLM generates coaching & conversational responses
  ↓
6. Synthesize both to MP3
  ↓
7. Append turn to conversation history JSON
  ↓
Return FeedbackResponse
```

## Implementation Details

### Context Window

**Default:** Last 3 turns included in context
```python
for i, turn in enumerate(conversation_history[-3:], 1):
    context_text += f"Turn {i}:\n..."
```

**Rationale:**
- Provides sufficient context for natural continuity
- Limits token usage to LLM prompt
- Prevents memory overflow for long conversations

**Configuration:**
Can be adjusted in `architect.py` `get_linguistic_coaching()`:
```python
for i, turn in enumerate(conversation_history[-N:], 1):  # Change N here
```

### File Management

**Storage Location:**
```
app/feedback_storage/conversations/
```

**Naming Convention:**
```
{session_id}.json
```

**Automatic Cleanup:**
- Files persist indefinitely (can be manually cleared)
- No automatic deletion after timeout
- User can clear via "Clear Conversation History" button

### Error Handling

**If JSON Load Fails:**
```python
try:
    with open(history_file, "r") as f:
        return json.load(f)
except Exception as e:
    print(f"[HISTORY] Error loading conversation history: {str(e)}")
    return []
```
- Returns empty list (starts fresh)
- Logs error for debugging
- Doesn't crash the application

**If JSON Save Fails:**
```python
try:
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
except Exception as e:
    print(f"[HISTORY] Error saving conversation history: {str(e)}")
```
- Logs error
- Continues processing (audio already generated)
- User can retry manually

## User Workflow

### Single Session Example

```
Session: session_1704067200000

Turn 1:
  User records: "I am very happy"
  Frontend sends to /process
  Backend generates responses with no context (first turn)
  User sees coaching + conversational response
  Turn saved to session_1704067200000.json

Turn 2:
  User records: "I got a new job"
  Frontend sends to /process with same session_id
  Backend loads Turn 1 from JSON
  LLM generates responses with Turn 1 context
  Response references "I am happy you're excited"
  Turn saved to session JSON (now has 2 turns)

Turn 3:
  User records: "I want to celebrate"
  Backend loads Turns 1-2 from JSON
  LLM generates responses with context of both previous turns
  Conversation continues naturally
  Turn saved to session JSON (now has 3 turns)

User clicks "Clear Conversation History"
  session_1704067200000.json is deleted
  Next input will start fresh (no context)
  New turns append to empty history
```

### Multiple Sessions Example

```
Session A: session_111
├─ Turn 1: User input A1
├─ Turn 2: User input A2
└─ Turn 3: User input A3

Session B: session_222
├─ Turn 1: User input B1
├─ Turn 2: User input B2

Session C: session_333
└─ Turn 1: User input C1

Each has separate JSON file
Each maintains independent context
Users can switch between sessions
```

## Frontend Display Structure

```
Main App
├─ Left Column (Recording)
│  └─ [Audio Recording Widget]
│  └─ [Analyze Audio Button]
│
└─ Right Column (Responses)
   ├─ Conversation History (expandable)
   │  ├─ All previous turns
   │  └─ [Clear History Button]
   │
   ├─ Current Response
   │  ├─ Your Speech (Transcribed)
   │  ├─ Coaching Feedback
   │  ├─ Audio Player
   │  ├─ Conversational Response
   │  └─ Audio Player
   │
   ├─ Speech Settings (Sidebar)
   │  ├─ Speech Rate Slider
   │  └─ Speech Pitch Slider
   │
   └─ Conversation Management
      ├─ Clear Conversation History Button
      └─ New Conversation Button
```

## Backend Logging

**[HISTORY] Prefix Messages:**

```
[HISTORY] Saved conversation turn 1 for session session_123
[HISTORY] Saved conversation turn 2 for session session_123
[HISTORY] Cleared conversation history for session session_123
[HISTORY] Error loading conversation history: <error>
[HISTORY] Error saving conversation history: <error>
```

## Testing Checklist

- [ ] Record first audio → no previous context used
- [ ] Record second audio → previous turn shown in history
- [ ] Verify LLM references previous context in response
- [ ] Click "Clear Conversation History" button
- [ ] Verify conversation.json file deleted
- [ ] Record new audio → should not reference cleared history
- [ ] Click "New Conversation" button
- [ ] Verify new session_id generated
- [ ] Multiple sessions don't interfere with each other
- [ ] History displays correctly for all previous turns
- [ ] API `/conversation/{id}` returns correct history
- [ ] API `/conversation/{id}` DELETE clears history

## Future Enhancements

1. **Conversation Export**
   - Download conversation as TXT or PDF
   - Include timestamps
   - Include audio links

2. **Conversation Search**
   - Search within conversation history
   - Filter by date or topic
   - Quick navigation to specific turn

3. **Conversation Analytics**
   - Track improvement over time
   - Show common error patterns
   - Generate progress reports

4. **Context Expansion**
   - Include more than 3 turns (configurable per user)
   - Semantic summary of older turns
   - Multi-day conversation continuity

5. **Conversation Sharing**
   - Share specific conversation turns
   - Collaborative learning
   - Peer review of responses

6. **Advanced LLM Features**
   - User personality modeling
   - Topic tracking
   - Adaptive difficulty
   - Learning style detection

## Performance Considerations

**File I/O:**
- JSON files small (typically 1-10 KB for 10+ turns)
- No database overhead
- Instant load/save operations

**LLM Prompt Size:**
- Base prompt: ~250 tokens
- Each context turn: ~50-100 tokens
- 3 turns context: ~150-300 additional tokens
- Total typical prompt: 400-600 tokens (acceptable)

**Storage:**
- 1 session with 100 turns ≈ 50 KB
- 1000 sessions with 10 turns each ≈ 500 KB
- Essentially unlimited storage for practical use

## Files Modified

1. `app/core/architect.py`
   - Added conversation directory creation
   - Added 3 history management methods
   - Enhanced `get_linguistic_coaching()` with context
   - Updated `process_user_input()` to use history

2. `app/backend/main.py`
   - Added `/conversation/{session_id}` GET endpoint
   - Added `/conversation/{session_id}` DELETE endpoint

3. `app/frontend/streamlit_app.py`
   - Added conversation history display with expander
   - Added "Clear Conversation History" button
   - Added "New Conversation" button
   - Enhanced UI with conversation management section

## Documentation Files

- **MULTI_TURN_CONVERSATION.md** (this file)
  - Complete feature documentation
  - Architecture and implementation details
  - User workflow examples

---

**Implementation Status:** Complete and ready for testing
**Database Required:** No (file-based storage)
**New Dependencies:** None
**Backward Compatible:** Yes (existing single-turn functionality preserved)
