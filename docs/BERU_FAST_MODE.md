# Faster Beru replies

Voice chat is a **pipeline**. Total wait ≈ sum of these steps:

| Step | Typical (CPU) | What it is |
|------|----------------|------------|
| **STT** | 1–4 s | faster-whisper transcribes your mic clip |
| **Routing** | 0–0.2 s | wake / memory / knowledge (fast) |
| **Ollama** | 3–15 s | `source: brain` — main chat LLM |
| **Web scrape** | 8–20 s | only when you ask weather/search |
| **TTS** | 1–3 s | UI `POST /voice/speak` (separate request) |

Wake words, goodbye, and “what do you want to do?” use **memory/knowledge** — no Ollama — and should feel much snappier than open-ended brain chat.

---

## Quick fix: add to `.env`

```env
BERU_FAST=1
BERU_WHISPER_MODEL=small
BERU_WHISPER_BEAM_SIZE=1
BERU_OLLAMA_NUM_PREDICT_SHORT=60
BERU_COMPUTER_BRAIN_NLU=0
BERU_OLLAMA_PRELOAD=1
BERU_PRELOAD_VOICE=1
```

Restart `beru_api.py` after changing `.env`.

See [`.env.example`](../.env.example) for a full fast profile.

---

## What `BERU_FAST=1` does

- Whisper **beam size 1**, VAD off → faster transcription
- Shorter Ollama replies (`num_predict` ~60)
- Smaller conversation window sent to Ollama
- **No** extra Ollama call for computer-command guessing
- Shorter Playwright timeout when web search runs

---

## Bigger wins (optional)

### 1. GPU for Whisper (if you have NVIDIA)

```env
BERU_WHISPER_DEVICE=cuda
BERU_WHISPER_COMPUTE_TYPE=float16
```

### 2. Smaller Ollama model

```bash
ollama pull llama3.2:1b
```

```env
BERU_OLLAMA_MODEL=llama3.2:1b
```

Trade-off: slightly simpler answers, much faster on CPU.

### 3. UI: don’t wait for two round trips

Your UI currently does:

1. `POST /voice/chat` → wait for text  
2. `POST /voice/speak` → wait for audio  

**Option A:** send `include_audio=1` on `/voice/chat` (one HTTP call).  
**Option B:** start TTS as soon as `response` arrives; show “thinking” during STT+chat only.  
**Option C:** use browser `speechSynthesis` for instant playback (robot voice) while keeping edge-tts for quality mode.

Tell the beru-ui agent:

```
Reduce voice latency:
1. Show thinking state immediately when mic stops.
2. Prefer include_audio=1 on POST /voice/chat OR pipeline speak without blocking UI.
3. Do not wait for speak before showing transcript + text bubble.
4. Read timing_ms from response when BERU_DEBUG_TIMING=1.
```

### 4. Debug where time goes

```env
BERU_DEBUG_TIMING=1
```

`/voice/chat` then includes:

```json
"timing_ms": { "stt": 2100, "chat": 4800, "total": 6900 }
```

- High **stt** → smaller Whisper model or GPU  
- High **chat** + `source: brain` → smaller Ollama model or lower `BERU_OLLAMA_NUM_PREDICT_SHORT`  
- High **chat** + `source: search` → weather API is fast; full page scrape is slow (Playwright)

---

## What stays slow on purpose

- **First message after API start** — Whisper + Ollama loading (mitigated by preload flags)
- **Real web search with page read** — Playwright (~8–15 s)
- **Long code/letter requests** — Ollama uses long mode automatically

For everyday voice chat, keep messages on the **conversation** path (wake, chitchat, questions to Beru) and use explicit phrases for web tasks: *“search weather in Stockholm”*.
