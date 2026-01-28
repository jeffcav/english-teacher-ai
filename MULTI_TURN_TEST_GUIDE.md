# Multi-Turn Conversation - Testing Guide

## Quick Start

### Setup
```bash
cd /home/jeff/dev/pg/english

# Terminal 1: Start backend
python -m app.backend.main

# Terminal 2: Start frontend
streamlit run app/frontend/streamlit_app.py
```

### Basic Test (5 minutes)

**Turn 1: First Exchange**
1. Record audio: "I am very happy today and I want to celebrate"
2. Click "Analyze Audio"
3. Wait for responses
4. **Expected:** See coaching feedback and conversational response
5. Check `app/feedback_storage/conversations/` for JSON file

**Turn 2: Continuation with Context**
1. Record audio: "I got a new job"
2. Click "Analyze Audio"
3. **Expected:** 
   - Conversational response mentions the celebration from Turn 1
   - Shows understanding of context
   - JSON file now has 2 turns

**Turn 3: Extended Conversation**
1. Record audio: "I want to call my family"
2. Click "Analyze Audio"
3. **Expected:** References both previous turns in natural way

## Detailed Test Scenarios

### Test 1: Conversation Persistence

**Objective:** Verify context is maintained across turns

**Steps:**
1. Record Turn 1: "My name is Alex and I like coffee"
2. Check response mentions your interests
3. Record Turn 2: "My favorite hobby is reading books"
4. **Expected:** Response should reference both coffee AND books
5. Record Turn 3: "I want to learn English"
6. **Expected:** Response should acknowledge all three facts

**Verification:**
```bash
# Check conversation JSON
cat app/feedback_storage/conversations/session_<id>.json | jq '.'
# Should show 3 turns with increasing context complexity
```

### Test 2: Multiple Sessions

**Objective:** Verify conversations don't interfere

**Steps:**
1. **Session A:**
   - Record: "I like pizza"
   - Wait for response
   
2. **Click "New Conversation"**
   
3. **Session B:**
   - Record: "I like sushi"
   - Wait for response
   - **Expected:** No mention of pizza, only sushi context
   
4. **Go back to Session A** (if UI supports session switching)
   - **Expected:** Previous context still includes pizza

**Verification:**
```bash
ls app/feedback_storage/conversations/
# Should see 2 different session JSON files
```

### Test 3: Clear Conversation History

**Objective:** Verify history can be reset

**Steps:**
1. Record Turn 1: "I am from France"
2. Record Turn 2: "I like wine"
3. Check JSON file has 2 turns
4. Click "Clear Conversation History" button
5. **Expected:** Success message
6. Check JSON file is deleted
7. Record Turn 3: "I like cheese"
8. **Expected:** Response has NO context about France/wine

**Verification:**
```bash
# File should be deleted
ls app/feedback_storage/conversations/session_*.json
# Record new audio and check it doesn't reference cleared history
```

### Test 4: API Endpoints

**Objective:** Verify conversation endpoints work

**Test 4A: GET conversation history**
```bash
curl http://localhost:8000/conversation/session_<id>

# Expected response:
{
  "session_id": "session_<id>",
  "conversation_count": 3,
  "history": [
    {"user": "...", "coaching": "...", "conversational": "..."},
    ...
  ]
}
```

**Test 4B: DELETE conversation history**
```bash
curl -X DELETE http://localhost:8000/conversation/session_<id>

# Expected response:
{
  "status": "success",
  "session_id": "session_<id>",
  "message": "Conversation history cleared"
}

# Verify file deleted:
ls app/feedback_storage/conversations/session_<id>.json
# Should return: No such file
```

### Test 5: LLM Context Injection

**Objective:** Verify context is properly sent to LLM

**Steps:**
1. Enable backend logging (check for `[HISTORY]` messages)
2. Record Turn 1: "I want to improve my English pronunciation"
3. **Expected in backend logs:**
   ```
   [HISTORY] Saved conversation turn 1 for session session_xxx
   ```
4. Record Turn 2: "I practice daily"
5. **Expected in backend logs:**
   ```
   [HISTORY] Saved conversation turn 2 for session session_xxx
   ```
6. Review the conversational responses
7. **Expected:** Turn 2 response acknowledges the improvement goal from Turn 1

### Test 6: UI Conversation History Display

**Objective:** Verify conversation history displays correctly

**Steps:**
1. Record 2-3 turns of conversation
2. **Expected:** "📚 Conversation History" expander shows all turns
3. Each turn should display:
   - Turn number
   - 🗣️ User transcript
   - 📝 Coaching feedback
   - 💬 Conversational response
4. Click expander to collapse/expand
5. **Expected:** No layout issues, clean display

### Test 7: Error Handling

**Test 7A: Corrupted JSON File**
1. Manually edit `app/feedback_storage/conversations/session_<id>.json`
2. Insert invalid JSON
3. Record new audio with same session
4. **Expected:** Backend logs `[HISTORY] Error loading conversation history`
5. **Expected:** New turn processes successfully (no crash)
6. **Expected:** New turn appends to file, fixing JSON

**Test 7B: Missing Directory**
1. Delete `app/feedback_storage/conversations/` directory
2. Start recording with a session
3. **Expected:** Directory auto-created
4. **Expected:** Conversation saves successfully

### Test 8: Long Conversations

**Objective:** Test with many turns

**Steps:**
1. Record 10+ turns
2. **Expected:** 
   - Response time consistent (~5-15 seconds)
   - JSON file grows to ~50KB
   - LLM still references context
   - No performance degradation

**Verification:**
```bash
# Check file size
du -h app/feedback_storage/conversations/session_<id>.json

# Count turns
cat app/feedback_storage/conversations/session_<id>.json | jq 'length'
```

## Monitoring and Debugging

### Backend Logs to Watch

```
[HISTORY] messages:
- "[HISTORY] Saved conversation turn N for session..."
- "[HISTORY] Cleared conversation history..."
- "[HISTORY] Error loading..." (if problems)
- "[HISTORY] Error saving..." (if problems)

[TTS] messages:
- Should see coaching and conversational synthesis

Ollama messages:
- LLM should respond with proper format
```

### Frontend Debugging

**Check Browser Console (F12):**
- Look for JavaScript errors
- Check network calls to `/conversation/{id}` endpoint
- Verify response format

**Check Streamlit Terminal:**
- Session state changes
- API call responses
- Error messages

### File System Checks

```bash
# View conversation structure
tree app/feedback_storage/conversations/

# View specific conversation
cat app/feedback_storage/conversations/session_<id>.json | jq '.'

# Pretty print with context
cat app/feedback_storage/conversations/session_<id>.json | jq '.[] | {user: .user, coaching: .coaching, conversational: .conversational}'

# Count turns
cat app/feedback_storage/conversations/session_<id>.json | jq 'length'
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Conversation history not showing | Verify JSON file exists in `conversations/` dir |
| LLM not using context | Check `[HISTORY]` logs, verify last 3 turns format |
| "Clear History" doesn't work | Check file permissions, verify DELETE endpoint working |
| New conversation button doesn't work | Verify frontend can call session_state changes |
| JSON parse errors | Check file encoding, ensure valid JSON format |
| Slow responses with many turns | Context grows, LLM slower; consider limiting turns |

## Performance Benchmarks

**Expected Performance:**

```
Single Turn Processing:
├─ Whisper (STT): 2-3 seconds
├─ LLM Response: 2-4 seconds
├─ pyttsx3 Synthesis: 2-4 seconds
└─ Total: 6-11 seconds

Multi-Turn Processing (with 2 context turns):
├─ Whisper (STT): 2-3 seconds
├─ LLM Response (larger prompt): 3-5 seconds
├─ pyttsx3 Synthesis: 2-4 seconds
└─ Total: 7-12 seconds

File Operations:
├─ JSON Load: <10ms
├─ JSON Save: 10-20ms
└─ Delete: <5ms
```

## Success Criteria

✅ **Feature is working when:**

1. First turn processes without context
2. Second turn shows history expander with 1 turn
3. Third turn shows 2 previous turns
4. LLM responses reference context naturally
5. "Clear History" button removes conversation
6. "New Conversation" generates new session
7. API `/conversation/{id}` returns correct data
8. API DELETE `/conversation/{id}` clears history
9. Multiple sessions don't interfere
10. Backend logs show `[HISTORY]` messages
11. No errors in browser console
12. JSON files store correctly

## Test Report Template

```markdown
# Multi-Turn Conversation Test Report

**Date:** [date]
**Tester:** [name]
**System:** [OS/Python version]

## Test Results

### Test 1: Basic Conversation Persistence
- [ ] Turn 1 processed
- [ ] Turn 2 shows history
- [ ] Turn 3 uses context
- **Status:** [PASS/FAIL]

### Test 2: Multiple Sessions
- [ ] Session A created
- [ ] Session B created
- [ ] Contexts isolated
- **Status:** [PASS/FAIL]

### Test 3: Clear History
- [ ] History cleared
- [ ] New turn has no context
- **Status:** [PASS/FAIL]

### Test 4: API Endpoints
- [ ] GET /conversation works
- [ ] DELETE /conversation works
- **Status:** [PASS/FAIL]

### Test 5: UI Display
- [ ] History expander shows
- [ ] All turns display
- [ ] Layout clean
- **Status:** [PASS/FAIL]

## Issues Found

[List any bugs or issues]

## Notes

[Additional observations]
```

---

**Ready to test!** Start with "Quick Start" section above.
