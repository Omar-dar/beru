# Tild UI ↔ Backend handoff

What we built in **tild-ui** (frontend) and what **tild** (backend) must provide or verify.  
Phone UI: [https://tildui.netlify.app](https://tildui.netlify.app)

---

## What we built in tild-ui (frontend)

### Chat UI

- ChatGPT-style layout (Tild theme `#0c0c12`), markdown (`react-markdown` + GFM), code blocks, user/assistant bubbles.
- Typewriter animation for new Tild replies; RTL replies skip typewriter when `text_direction: "rtl"`.
- PDF upload: `POST /upload`, drag-drop, PDF shown as a user message card in chat.
- Suggested prompts after upload.

### Voice

- `POST /voice/chat` — audio blob (WebM on desktop; MP4/M4A on iOS via `voiceSupport.ts`).
- `POST /voice/speak` — MP3 playback in browser.
- Continuous voice session (silence auto-stop, orb overlay) until goodbye or close.
- **No language picker in UI** — backend auto-detects; UI does **not** send `language` in FormData.
- Mobile fixes: HTTPS/mic errors shown in overlay; iOS-friendly mime + file extension on upload.

### RTL / Arabic

- UI reads `text_direction` from API and sets `dir="rtl"` on bubbles/markdown.
- Voice user lines use `transcript_language` when present.

### API base URL (Netlify + phone)

- `REACT_APP_API_URL` baked at build time (`src/services/api.ts`).
- Local dev: `.env.development` → `http://localhost:8000` for `npm start`.
- **Netlify production:** must be **HTTPS** (e.g. ngrok), **not** `http://192.168.x.x:8000` (Safari blocks mixed content on `https://tildui.netlify.app`).
- Deploy helpers: `netlify.toml`, `scripts/check-netlify-env.js` (fails build if URL missing, localhost, HTTP-on-HTTPS site, or placeholder like `abc123.ngrok-free.app`).
- Docs: `tild-ui/docs/DEPLOY.md`.

### Guest conversation collection (UI side — done)

Backend already logs turns; UI sends a stable per-browser session id:

| Mechanism | Where |
|-----------|--------|
| `X-Tild-Session-Id: <uuid>` | Axios default header on all requests |
| `session_id` in JSON body | `POST /chat` |
| `session_id` form field | `POST /voice/chat` |
| Storage | `localStorage` key `tild_session_id` via `src/utils/tildSession.ts` |

**Important:** Without this UUID, backend falls back to client IP (bad behind Netlify). UI always sends UUID.

### Responsive / mobile

- `src/styles/responsive.css`, safe areas, 44px touch targets, `viewport-fit=cover`.
- Phone UI URL: **https://tildui.netlify.app** (not the ngrok URL for normal use).

### Git (tild-ui, on `main`)

Separate commits for: responsive, mobile voice, session id, Netlify env verification.

---

## What the backend (tild) must provide / verify

### 1. Network access (Mac + phone + Netlify)

- API listens on `0.0.0.0:8000`, e.g. `app.run(host='0.0.0.0', port=8000, debug=False)` in `tild_api.py`.
- macOS firewall allows port **8000**.
- For `https://tildui.netlify.app` on phone: run `ngrok http 8000`, put the real `https://….ngrok-free.app` in Netlify `REACT_APP_API_URL` (not the doc example `abc123`).
- Keep `python3 tild_api.py` and ngrok running while testing; ngrok URL changes when restarted → update Netlify + redeploy.

### 2. CORS (if not already)

Browser on `https://tildui.netlify.app` calls API on ngrok origin. Backend must allow:

- **Origin:** `https://tildui.netlify.app` (and optionally `http://localhost:3000` for dev).
- **Methods/headers:** `POST`, `GET`, `Content-Type`, `X-Tild-Session-Id`.

Current code: `CORS(app)` in `tild_api.py` (all origins). If chat fails only from Netlify but works from `npm start`, fix CORS first.

### 3. Session id for conversation collection (implemented)

On every `POST /chat` and `POST /voice/chat`, after Tild replies, append:

```text
user: <human message>
tild: <tild reply>
```

To: `data/collected_conversations/{session_id}.txt` (one file per visitor).

**Read session id in this order** (`tild_api._collector_session_id`):

1. Header: `X-Tild-Session-Id: <uuid>` ← UI sends this on every request  
2. JSON: `"session_id": "<uuid>"` on `/chat`  
3. Form: `session_id` on `/voice/chat`  
4. Fallback: client IP (avoid for production guests)

**Files (backend):**

| File | Role |
|------|------|
| `src/conversation_collector.py` | Writes files |
| `src/pipeline.py` | Calls collector after each turn |
| `tild_api.py` | Reads session id and passes it in |

**Env vars (Mac):**

| Variable | Default | Meaning |
|----------|---------|---------|
| `TILD_COLLECT_CONVERSATIONS` | `1` | Logging on |
| `TILD_COLLECT_EXCLUDE_OWNER` | `1` | Skip Omar after owner password |
| `TILD_COLLECT_DIR` | (empty) | Default `data/collected_conversations/` |

- **Check:** `GET /health` → `"conversation_collection": true`  
- **Restart:** `python3 tild_api.py`  
- **Label data:** move `.txt` to `good/` or `bad/` under collected folder.  
- **Test:** Guest chat on Netlify → new `{uuid}.txt` on Mac with `user:` / `tild:` lines (not owner session).

See also: [COLLECTING_CONVERSATIONS.md](./COLLECTING_CONVERSATIONS.md)

### 4. Endpoints the UI uses

| Method | Path | Notes |
|--------|------|--------|
| GET | `/start` | Initial greeting |
| POST | `/chat` | `{ message, session_id?, new_chat?, document_id? }` + header |
| POST | `/clear` | New chat |
| POST | `/upload` | multipart file (PDF) |
| GET | `/documents` | (if used) |
| GET | `/voice/capabilities` | STT/TTS flags |
| POST | `/voice/chat` | multipart audio, `session_id`, optional `document_id`, `new_chat` |
| POST | `/voice/speak` | `{ text, language }` → audio bytes |
| GET | `/health` | Include `conversation_collection` |

**Response fields UI uses:** `response`, `language`, `text_direction`, `active_document`; voice: `transcript`, `transcript_language`.

### 5. Voice / STT

- Accept iOS recordings (m4a/mp4, not only webm).
- Return useful **422** when transcription fails (UI shows “Could not understand audio…”).

### 6. Owner vs guest

- Owner login (Omar + password) should still work; collection should exclude owner when `TILD_COLLECT_EXCLUDE_OWNER=1`.

---

## Quick test checklist (both repos)

1. Mac: `python3 tild_api.py` + `ngrok http 8000`
2. Netlify: `REACT_APP_API_URL` = your ngrok **HTTPS** URL → **clear cache deploy**
3. Mac browser: `https://tildui.netlify.app` → send message (should hit ngrok → Mac)
4. iPhone: same URL; allow mic for voice
5. Mac: `data/collected_conversations/<uuid>.txt` grows for guest (not owner)
6. `GET /health` shows collection enabled

---

## Common mistakes (already hit)

| Mistake | Symptom |
|---------|---------|
| Netlify `REACT_APP_API_URL` = `http://192.168.x.x:8000` | Build fails (mixed content check) or phone can’t connect |
| Netlify URL = `https://abc123.ngrok-free.app` (example) | “Cannot reach Tild at https://abc123…” |
| ngrok stopped or URL changed | Netlify still has old URL until redeploy |
| UI opened ngrok URL instead of Netlify | Wrong app; use **tildui.netlify.app** for chat |
| No `X-Tild-Session-Id` / `session_id` | One file per IP or missing logs |
| API only on `127.0.0.1` | ngrok/LAN/Netlify can’t reach Mac |

---

## One-line prompt for backend agent

> Match tild-ui: API on `0.0.0.0:8000`, CORS for `https://tildui.netlify.app` and `X-Tild-Session-Id`, read `session_id` on `/chat` and `/voice/chat`, conversation collector to `data/collected_conversations/{session_id}.txt`, health shows `conversation_collection`, voice accepts m4a/mp4. UI sends session UUID via header + body/form; Netlify uses HTTPS ngrok in `REACT_APP_API_URL`.
