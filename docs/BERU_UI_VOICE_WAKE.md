# beru-ui handoff: voice auth + wake word (no password)

Backend **removed the Omar password gate** when `BERU_VOICE_AUTH=1` (default). Omar is identified by **voice**, not text password. Chat and file upload still work **after** voice unlocks the session.

---

## What changed on the backend

| Before | After |
|--------|--------|
| "Is that you Omar?" → password | "Say Beru" → voice match → session unlocked |
| `BERU_OMAR_PASSWORD` required | Password ignored when voice auth is on |
| Same greeting every login | **Wake word** → varied "what's your plan today, sir?" |

---

## API fields (add to UI state)

On `GET /start`, `POST /chat`, `POST /voice/chat`, `POST /clear`:

| Field | Type | Meaning |
|-------|------|---------|
| `session_identified` | bool | User can use full features |
| `is_owner` | bool | Omar unlocked this session |
| `awaiting_voice_wake` | bool | Waiting for voice + wake |
| `voice_verified` | bool | Voice matched this session |
| `voice_enrolled` | bool | Omar voice profile exists on server |
| `source` | string | `"wake"` on wake-only replies |
| `voice_score` | float? | Similarity 0–1 on voice gate (optional) |

`GET /voice/capabilities` and `GET /voice/auth/status` return enrollment + threshold info.

---

## One-time voice enrollment (settings screen)

**Before first wake**, Omar must enroll 2–5 short clips (~3 seconds each).

```
POST /voice/enroll
Content-Type: multipart/form-data
Form: audio=<file>  (repeat field or audio0, audio1, …)
Header: X-Beru-Session-Id: <uuid>
```

Success:

```json
{ "ok": true, "samples": 3, "enrolled": true }
```

UI: simple "Train my voice" flow — record 3 phrases, upload, show success.

Check status:

```
GET /voice/auth/status
→ { "voice_enrolled": true, "voice_auth_enabled": true, "awaiting_voice_wake": true, ... }
```

---

## Wake word flow (main UX)

1. App loads → `GET /start` → Beru says: *"Say Beru or Wake up Beru so I know it's you."*
2. User says **"Beru"** or **"Wake up Beru"** (mic → `POST /voice/chat`).
3. Backend verifies voice → unlocks Omar → replies with **varied** wake greeting (`source: "wake"`).
4. After unlock, **text chat** and **file upload** work normally for that `session_id`.
5. `POST /clear` or new chat → voice wake required again (same session id).

### Wake phrases (STT)

- `Beru`
- `Hey Beru`
- `Wake up Beru`
- STT may hear `Buro` — backend accepts that too.

### Combined wake + command

`"Beru what's the weather in Stockholm"` → unlock (if needed) + runs weather search in one turn.

---

## UI implementation checklist

### Remove

- Password input UI for Omar
- Any flow that asks for `BERU_OMAR_PASSWORD`
- Treating `awaiting_owner_confirm` as password step (legacy only if `BERU_VOICE_AUTH=0`)

### Add

1. **Voice enrollment screen** (first run if `voice_enrolled === false`)
2. **Wake listening mode** when `awaiting_voice_wake === true`:
   - Show orb/listening state
   - Send mic audio to `POST /voice/chat` (not text-only for unlock)
3. **Handle `source === 'wake'`** — play TTS greeting, don't show as error
4. **Gate messages** when `session_identified === false` on text send:
   - Show: *"Use voice — say Beru"* instead of sending to `/chat` OR send and show backend gate reply
5. **Optional always-on wake** (Electron):
   - Background VAD → on silence, POST short clip to `/voice/chat`
   - Only when `awaiting_voice_wake` or user enabled "Hey Beru" mode

### Text chat after unlock

- `session_identified && is_owner` → normal `POST /chat` + PDF `POST /upload`
- Conversation history is for **tracking**; identity came from voice

### Session id

- Keep stable `X-Beru-Session-Id` + form `session_id` (unchanged)

---

## Copy-paste prompt for beru-ui agent

```
Integrate Beru voice auth (password removed):

1. On load, read GET /voice/auth/status and GET /start fields:
   voice_enrolled, awaiting_voice_wake, session_identified, is_owner.

2. If !voice_enrolled, show Settings → "Enroll my voice":
   record 3 short clips, POST multipart to /voice/enroll (form key "audio").

3. When awaiting_voice_wake, primary UX is voice not text:
   mic → POST /voice/chat with session_id.
   Wake phrases: "Beru", "Hey Beru", "Wake up Beru".
   On success: is_owner=true, source may be "wake" with varied greeting — TTS it.

4. Remove Omar password UI entirely.

5. After session_identified && is_owner:
   enable text chat (POST /chat), file upload (POST /upload), computer control.
   Chat is for conversation history; voice unlocked the session.

6. On POST /clear, expect awaiting_voice_wake=true again — return to wake listening.

7. Handle gate responses (session_identified false): show backend message,
   prompt user to say Beru into mic.

8. Optional Electron: continuous listen for "Beru" when app focused and
   awaiting_voice_wake or user toggles "Hey Beru" mode.
```

---

## Backend env

| Variable | Default | Purpose |
|----------|---------|---------|
| `BERU_VOICE_AUTH` | `1` | Voice auth on; password off for Omar |
| `BERU_VOICE_THRESHOLD` | `0.72` | Match strictness (lower = easier) |
| `BERU_OMAR_PASSWORD` | — | Ignored when voice auth on |

Install on server:

```bash
pip install librosa soundfile imageio-ffmpeg
```

`imageio-ffmpeg` bundles ffmpeg on Windows so browser **WebM** enrollment works without a system ffmpeg install.

Restart API after pull.
