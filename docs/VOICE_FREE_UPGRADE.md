# Free voice upgrade (hear + speak better)

Beru now defaults to **free** tools that are much closer to “smart assistant” quality than `whisper small` + macOS `say`.

## Install

```bash
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg   # for CLI playback fallback
```

First run downloads the **medium** Whisper model (~1.5 GB, one time).

## Defaults (in `.env`)

```env
BERU_STT_BACKEND=faster-whisper
BERU_WHISPER_MODEL=medium
BERU_WHISPER_DEVICE=cpu
BERU_WHISPER_COMPUTE_TYPE=int8
BERU_TTS_BACKEND=edge
```

| Setting | What it does |
|---------|----------------|
| **faster-whisper** | Same Whisper models, faster → you can use **medium** on a Mac for free |
| **medium** | Much better accents / Swedish / Arabic than `small` |
| **edge-tts** | Free Microsoft **neural** voices (EN, SV, AR) — no API key |

Restart API: `python3 beru_api.py`

## Slow responses?

Each voice turn runs: **Whisper (CPU)** → **Ollama** → **TTS**. That takes time.

Speed up hearing (`.env`):

```env
BERU_WHISPER_MODEL=small
```

GUI: use `include_audio=true` on `/voice/chat` (one HTTP call instead of chat + speak).

## Two voices at once?

Your UI is probably playing **both** server MP3 and **browser** `speechSynthesis`. Use only one — see `BERU_UI_VOICE_INTEGRATION.md`.

## GUI: send language every voice request

Wrong language detection is the #1 issue with code-switching. In beru-ui:

```javascript
form.append('language', userSelectedLang); // 'en' | 'sv' | 'ar'
```

`/voice/speak` now returns **`audio/mpeg`** (MP3). Play with:

```javascript
const blob = await res.blob();
new Audio(URL.createObjectURL(blob)).play();
```

## If Mac is slow

Try smaller model (still better than old default):

```env
BERU_WHISPER_MODEL=small
```

Or larger (best hearing, slower):

```env
BERU_WHISPER_MODEL=large-v3
```

## Fallback to old stack

```env
BERU_STT_BACKEND=whisper
BERU_WHISPER_MODEL=small
BERU_TTS_BACKEND=macos
```

## Voice map (override in `.env`)

```env
BERU_EDGE_VOICE_EN=en-US-JennyNeural
BERU_EDGE_VOICE_SV=sv-SE-SofieNeural
BERU_EDGE_VOICE_AR=ar-SA-ZariyahNeural
```

List more: `edge-tts --list-voices | grep -E 'sv-SE|ar-|en-US'`
