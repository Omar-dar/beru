# Tild UI ↔ Backend integration (voice + session summary)

Use this document in the **tild-ui** repo so the GUI matches the **tild** API backend.

**Base URL (local dev):** `http://localhost:8000`

---

## What works today (text + documents)

| Feature | Method | Endpoint |
|--------|--------|----------|
| New session / greeting | `GET` | `/start` |
| Clear chat | `POST` | `/clear` |
| Send message | `POST` | `/chat` JSON body |
| Upload PDF | `POST` | `/upload` multipart `file` |
| List PDFs | `GET` | `/documents` |
| Health | `GET` | `/health` |

### `POST /chat` body

```json
{
  "message": "Hello Tild",
  "new_chat": false,
  "document_id": "optional-doc-id-from-upload"
}
```

### `POST /chat` response (important fields)

```json
{
  "response": "markdown-friendly reply",
  "language": "en",
  "tone": "bro",
  "source": "brain",
  "user": "Omar",
  "is_owner": true,
  "session_identified": true,
  "active_document": { "id": "...", "filename": "..." }
}
```

`source` values: `gate`, `memory`, `knowledge`, `rag`, `search`, `brain`, `document`, `correction`, `fallback`, `analysis`.

---

## New: Voice API (for GUI microphone + speaker)

| Feature | Method | Endpoint |
|--------|--------|----------|
| Capabilities | `GET` | `/voice/capabilities` |
| Speech → text only | `POST` | `/voice/transcribe` |
| Speech → full Tild reply | `POST` | `/voice/chat` |
| Text → speech (macOS server) | `POST` | `/voice/speak` |

**Free upgrade (default):** `faster-whisper` + **`medium`** model + **edge-tts** neural voices. See `docs/VOICE_FREE_UPGRADE.md`.

First voice request may take time while the STT model downloads.

### `GET /voice/capabilities`

```json
{
  "stt": true,
  "stt_engine": "faster-whisper",
  "whisper_model": "medium",
  "tts_engine": "edge",
  "tts_server": true,
  "tts_note": "...",
  "supported_upload_extensions": [".wav", ".webm", ...],
  "recommended_record_format": "audio/webm or audio/wav",
  "sample_rate_hint_hz": 16000
}
```

On non-Mac servers, `tts_server` is `false` — use **browser TTS** for playback.

---

### `POST /voice/transcribe`

**Content-Type:** `multipart/form-data`

| Field | Required | Description |
|-------|----------|-------------|
| `audio` | yes | Recorded file (webm, wav, mp3, m4a, …) |
| `language` | no | Hint: `en`, `sv`, or `ar` |

**Response:**

```json
{
  "text": "what the user said",
  "language": "en",
  "segment_count": 3
}
```

---

### `POST /voice/chat` (recommended for GUI voice button)

Same pipeline as `/chat`, but input is audio.

**Content-Type:** `multipart/form-data`

| Field | Required | Description |
|-------|----------|-------------|
| `audio` | yes | User recording |
| `new_chat` | no | `true` / `false` (string ok) |
| `document_id` | no | Active PDF id |
| `language` | no | Whisper hint `en` / `sv` / `ar` |
| `include_audio` | no | `true` → attach `audio_base64` + `audio_mime` (skip separate `/voice/speak`) |

**Response:** everything from `/chat`, plus:

```json
{
  "transcript": "what Whisper heard",
  "transcript_language": "en",
  "audio_base64": "...",
  "audio_mime": "audio/mpeg"
}
```

If transcription is empty or too short:

```json
{ "error": "Could not understand audio. Please try again." }
```

HTTP `422`.

---

### `POST /voice/speak` (optional — macOS API host only)

**Content-Type:** `application/json`

```json
{
  "text": "Reply to read aloud",
  "language": "en"
}
```

**Response:** `audio/mpeg` (MP3) with edge-tts, or `audio/wav` if `TILD_TTS_BACKEND=macos`.

```javascript
const audio = new Audio(URL.createObjectURL(await res.blob()));
audio.play();
```

---

## Suggested GUI implementation

### 1. Record (browser)

```javascript
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
// on stop: blob → FormData
const form = new FormData();
form.append('audio', blob, 'recording.webm');
form.append('document_id', activeDocId ?? '');
const res = await fetch('http://localhost:8000/voice/chat', {
  method: 'POST',
  body: form,
});
const data = await res.json();
// Show data.transcript as "You said: ..."
// Show data.response as Tild message (markdown)
```

### 2. Play reply — pick ONE method (fixes “two voices”)

**Common bug:** GUI calls `/voice/speak` **and** `speechSynthesis.speak()` → user hears **two different voices**. Use **only one** path below.

**Recommended — single request (faster, one voice):**

```javascript
form.append('include_audio', 'true');
const data = await (await fetch(`${API}/voice/chat`, { method: 'POST', body: form })).json();
if (data.audio_base64) {
  stopAnyPlayingAudio(); // cancel previous Audio + speechSynthesis.cancel()
  const blob = base64ToBlob(data.audio_base64, data.audio_mime || 'audio/mpeg');
  const url = URL.createObjectURL(blob);
  const player = new Audio(url);
  player.play();
  player.onended = () => URL.revokeObjectURL(url);
}
// Do NOT also call /voice/speak or speechSynthesis
```

**Alternative — two requests (slower):**

Only `POST /voice/speak` after `/voice/chat` — **do not** use browser `speechSynthesis`.

```javascript
function stopAnyPlayingAudio() {
  window.speechSynthesis?.cancel();
  if (window.__tildAudio) {
    window.__tildAudio.pause();
    window.__tildAudio = null;
  }
}
```

### 3. UI states

- `idle` → `recording` → `transcribing` → `thinking` → `speaking` → `idle`
- Disable mic while request in flight
- Show `transcript` in the user bubble even if you only sent audio

### 4. Owner / password flow

Unchanged: text `/chat` handles Omar password gate. Voice uses the same session after `/start`. If `awaiting_owner_confirm` from `/start`, user may need to **type** password (or transcribe "yes" + password in a second voice turn).

Environment on backend: `TILD_OMAR_PASSWORD` in `.env` (not sent to UI).

---

## Backend stack (for context)

| Layer | Role |
|-------|------|
| **Ollama** `llama3.2:3b` | Main reasoning (`source: brain`) |
| **RAG** | `data.txt`, `conversation_data.txt`, `personality_data.txt` |
| **Memory** | `data/memory.json`, corrections, Omar facts |
| **Whisper** | Voice STT in API |
| **GPT-2 `models/tild_v2`** | Not loaded by default (`load_model=False`) |

After factory reset Mac:

```bash
./scripts/setup_machine.sh   # venv + pip + Ollama
# .env: TILD_OMAR_PASSWORD=...
python3 tild_api.py
```

Adding facts: edit `data/data.txt`, restart API (no `train.py` needed).

Ollama answers can auto-append to `data/conversation_data.txt` when `source` is `brain` and learning applies (`[Tild learned from brain]` in server logs).

---

## CORS

API enables `flask-cors` for all origins — GUI on another port (e.g. Vite `5173`) can call `localhost:8000`.

---

## Env vars (backend)

| Variable | Purpose |
|----------|---------|
| `TILD_OMAR_PASSWORD` | Omar gate password |
| `TILD_STT_BACKEND` | `faster-whisper` (or `whisper`) |
| `TILD_WHISPER_MODEL` | Default `medium` |
| `TILD_WHISPER_DEVICE` | Default `cpu` |
| `TILD_WHISPER_COMPUTE_TYPE` | Default `int8` |
| `TILD_TTS_BACKEND` | `edge` (or `macos`) |
| `TILD_EDGE_VOICE_SV` etc. | Optional neural voice IDs |
| `OPENWEATHER_KEY` | Weather search (optional) |

---

## Checklist for tild-ui PR

- [ ] Mic button → `POST /voice/chat` with `FormData`
- [ ] Display `transcript` + `response`
- [ ] TTS: `speechSynthesis` and/or `/voice/speak` on Mac
- [ ] Pass `document_id` when a PDF is active (same as text chat)
- [ ] Loading / error states for empty transcription
- [ ] Optional: `GET /voice/capabilities` on app load to show mic only if `stt`
