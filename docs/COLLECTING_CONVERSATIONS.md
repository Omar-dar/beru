# Collecting conversations (backend + tild-ui)

Use this when the GUI is on **Netlify** and the API runs on your **Mac**. Each guest turn is saved on the Mac as training-style text.

---

## What the backend does (already in `tild`)

### Files added/changed

| File | Role |
|------|------|
| `src/conversation_collector.py` | Appends `user:` / `tild:` lines to disk |
| `src/pipeline.py` | After each reply, calls `collect_turn(...)` if a session id is present |
| `tild_api.py` | Reads session id from the request and passes it to `chat_turn` |
| `data/collected_conversations/` | Output folder (`.txt` per browser session) |
| `.gitignore` | Ignores `*.txt` in that folder |

### When it logs

- Every **`POST /chat`** and **`POST /voice/chat`** turn (after Tild’s reply is ready).
- Format per turn:

```text
user: <what the human sent>
tild: <what Tild answered>
```

- One file per session: `data/collected_conversations/{session_id}.txt`
- First lines in each file are metadata (`# session_id`, `# user`, `# started`, …).

### How the backend gets `session_id`

Priority in `tild_api._collector_session_id()`:

1. HTTP header **`X-Tild-Session-Id`**
2. JSON field **`session_id`** on `/chat`
3. Form field **`session_id`** on `/voice/chat`
4. Fallback: client IP (not ideal for Netlify — **use a UUID in the UI**)

### Environment variables (Mac, before `python3 tild_api.py`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `TILD_COLLECT_CONVERSATIONS` | `1` | `1` = log files, `0` = off |
| `TILD_COLLECT_EXCLUDE_OWNER` | `1` | `1` = do **not** log Omar after password login |
| `TILD_COLLECT_DIR` | (empty) | Custom folder; default `data/collected_conversations` |

### Check it works

```bash
curl http://localhost:8000/health
```

Look for:

```json
"conversation_collection": true,
"conversation_collect_dir": ".../data/collected_conversations"
```

After a guest chats, open:

`data/collected_conversations/<session_id>.txt`

### Label good vs bad

Move files to:

- `data/collected_conversations/good/`
- `data/collected_conversations/bad/`

Or add `# label: bad` at the top. Use good pairs later in `data/conversation_data.txt`.

### Per-browser sessions

Identity and chat history are **separate per `X-Tild-Session-Id`** (`src/client_sessions.py`). Omar on Mac does not log the phone in as Omar. Omar’s facts in `memory.json` are still shared. **Restart** `python3 tild_api.py` after pulling this change.

---

## What to do in **tild-ui** (so it matches the backend)

The UI must send the **same session id on every request** from that browser (store in `localStorage`).

### 1. Create `src/utils/tildSession.ts`

```typescript
const SESSION_KEY = 'tild_session_id'

export function getTildSessionId(): string {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `sess-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}
```

### 2. Update `src/services/api.ts`

At the top, after imports:

```typescript
import { getTildSessionId } from '../utils/tildSession'

export const API_URL =
  process.env.REACT_APP_API_URL?.replace(/\/$/, '') || 'http://localhost:8000'

/** Same id on every request so the Mac logs one file per visitor */
axios.defaults.headers.common['X-Tild-Session-Id'] = getTildSessionId()
```

In `sendMessage`, also send `session_id` in the body (optional backup if headers are stripped):

```typescript
export const sendMessage = async (
  message: string,
  options?: { new_chat?: boolean; document_id?: string }
): Promise<ChatResponse> => {
  const body: ChatRequest = {
    message,
    ...options,
    session_id: getTildSessionId(),
  }
  const response = await axios.post<ChatResponse>(`${API_URL}/chat`, body)
  return response.data
}
```

In `voiceChat`, append session id to the form:

```typescript
  formData.append('session_id', getTildSessionId())
```

### 3. Update `src/types/index.ts`

```typescript
export interface ChatRequest {
  message: string
  new_chat?: boolean
  document_id?: string
  session_id?: string
}
```

### 4. Netlify + Mac API URL

Set at **build** time on Netlify (Site settings → Environment variables):

```env
REACT_APP_API_URL=https://YOUR-TUNNEL-OR-MAC-URL
```

Examples:

- Same Wi‑Fi: `http://192.168.1.10:8000` (your Mac’s IP; may need HTTPS tunnel for mixed content)
- **Recommended:** ngrok HTTPS URL, e.g. `https://abc123.ngrok-free.app`

On the Mac, run API listening on the network:

```python
# last line of tild_api.py should be:
app.run(host='0.0.0.0', port=8000, debug=False)
```

### 5. Deploy flow

1. Mac: `export TILD_COLLECT_CONVERSATIONS=1` (default) and start `python3 tild_api.py`
2. Netlify: set `REACT_APP_API_URL`, deploy `tild-ui`
3. Send testers the Netlify link
4. Read logs on the Mac under `data/collected_conversations/`

---

## Quick test (laptop)

1. Start API on Mac.
2. Run UI locally with `REACT_APP_API_URL=http://localhost:8000`.
3. Chat as a **guest** (not Omar / not Yellow password).
4. Confirm a new `.txt` file appears in `data/collected_conversations/`.

---

## Copy-paste block for the tild-ui repo

> Wire session collection: add `src/utils/tildSession.ts` with `getTildSessionId()` (localStorage UUID). In `api.ts` set `axios.defaults.headers.common['X-Tild-Session-Id'] = getTildSessionId()`, add `session_id` to `ChatRequest` and `sendMessage`, append `session_id` in `voiceChat` FormData. Extend `ChatRequest` type with optional `session_id`. Backend already logs `user:` / `tild:` to `data/collected_conversations/{session_id}.txt` when this header or field is sent.
