# Beru UI ↔ Backend integration (beru-ui contract)

This document matches **beru-ui** (PWA, Electron, Capacitor, Netlify) to the **beru** Python API.

## Quick start (Windows)

```powershell
cd beru
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe beru_api.py
```

API: `http://localhost:8000` (binds `0.0.0.0` for LAN phones).

UI build-time env: `REACT_APP_API_URL=http://localhost:8000` (or your PC LAN IP / HTTPS ngrok URL).

---

## Endpoints (implemented)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/start` | Session greeting |
| POST | `/chat` | Text chat |
| POST | `/clear` | New chat |
| POST | `/upload` | PDF upload |
| GET | `/documents` | List PDFs |
| GET | `/health` | Status + feature flags |
| GET | `/voice/capabilities` | STT/TTS flags |
| POST | `/voice/chat` | Voice turn (audio → transcript + reply) |
| POST | `/voice/transcribe` | STT only |
| POST | `/voice/speak` | TTS → `audio/mpeg` MP3 |
| GET | `/computer/capabilities` | Owner desktop actions |

---

## Session ID

UI sends:

- Header: `X-Beru-Session-Id: <uuid>`
- Body: `session_id` on `POST /chat` and `POST /voice/chat` form

Backend keeps **per-session** identity gate + chat history (Omar login isolated per device).

---

## ChatResponse JSON (required by UI)

`GET /start`, `POST /chat`, `POST /clear`, `POST /voice/chat`:

```json
{
  "response": "Markdown reply",
  "language": "en",
  "text_direction": "ltr",
  "active_document": null,
  "source": "brain",
  "activity": "searching"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `response` | Yes | Markdown |
| `language` | Yes | `en`, `sv`, `ar` |
| `text_direction` | Yes | `ltr` or `rtl` (Arabic) |
| `active_document` | No | `{ "id", "filename" }` or `null` |
| `source` | No | `gate`, `brain`, `search`, `memory`, `knowledge`, `rag`, … |
| `activity` | No | `searching` when `source` is `search` (voice WEB badge) |

### Web search / voice searching orb

When Beru searches the web or opens Google for the owner:

```json
{
  "source": "search",
  "activity": "searching"
}
```

UI also accepts `"source": "web_search"` (normalized to `search` on output).

---

## Voice

### `GET /voice/capabilities`

```json
{
  "stt": true,
  "tts": true,
  "tts_server": true
}
```

If `stt: false` → UI disables mic. If `tts_server: false` → UI uses browser TTS.

### `POST /voice/chat`

- Multipart field: `audio` (webm, mp4, m4a, wav, …)
- Form: `session_id`, `document_id`, `new_chat`, `language` (optional)

Returns ChatResponse +:

```json
{
  "transcript": "user speech text",
  "transcript_language": "en"
}
```

**422** when audio is unclear → UI shows “Could not understand audio”.

### `POST /voice/speak`

```json
{ "text": "Hello", "language": "en" }
```

→ `Content-Type: audio/mpeg` (MP3). Default voices: **male** (Guy / Mattias / Hamed).

---

## PDF upload

`POST /upload` multipart `file` (PDF):

```json
{
  "status": "ok",
  "document": {
    "id": "...",
    "filename": "...",
    "page_count": 10,
    "chunk_count": 42,
    "preview": "...",
    "uploaded_at": "..."
  },
  "active_document": { "id": "...", "filename": "..." },
  "message": "Ready - I indexed ..."
}
```

---

## CORS

Default: all origins (`*`). Tighten in production:

```env
BERU_CORS_ORIGINS=https://beruui.netlify.app,http://localhost:3000,capacitor://localhost
```

Allowed headers: `Content-Type`, `X-Beru-Session-Id`.

---

## Deploy matrix

| UI runs on | `REACT_APP_API_URL` | Backend |
|------------|---------------------|---------|
| Browser dev | `http://localhost:8000` | `python beru_api.py` |
| Phone same Wi‑Fi | `http://192.168.x.x:8000` | `0.0.0.0:8000`, firewall open |
| Netlify / PWA | `https://….ngrok-free.app` | HTTPS required (no mixed content) |
| Capacitor / Electron | Same HTTPS or LAN URL | CORS + session header |

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BERU_OMAR_PASSWORD` | `beru123` | Owner gate |
| `BERU_CORS_ORIGINS` | `*` | CORS allowlist |
| `BERU_WEB_SEARCH` | `1` | DuckDuckGo + Wikipedia |
| `BERU_COMPUTER_CONTROL` | `1` | Owner browser/screenshot |
| `BERU_OLLAMA_PRELOAD` | `1` | Warm Ollama on startup |
| `BERU_EDGE_VOICE_EN` | `en-US-GuyNeural` | Male TTS |

See also: [BROWSER_INTEGRATION.md](BROWSER_INTEGRATION.md), [BERU_COMPUTER_CONTROL.md](BERU_COMPUTER_CONTROL.md), [BERU_UI_VOICE_INTEGRATION.md](BERU_UI_VOICE_INTEGRATION.md).

---

## Backend agent checklist

- [x] `GET /start`, `POST /chat`, `POST /clear`, `POST /upload`
- [x] `GET /voice/capabilities`, `POST /voice/chat`, `POST /voice/speak`
- [x] `response`, `language`, `text_direction`, `active_document`
- [x] `source: "search"` + `activity: "searching"` for web search
- [x] `transcript` + `transcript_language` on voice chat
- [x] CORS + `X-Beru-Session-Id`
- [x] `0.0.0.0:8000` bind
- [x] MP3 from `/voice/speak`
- [x] 422 on empty voice transcript
