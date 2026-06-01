# Free voice upgrade (hear + speak better)

Tild now defaults to **free** tools that are much closer to “smart assistant” quality than `whisper small` + macOS `say`.

## Install

```bash
source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg   # for CLI playback fallback
```

First run downloads the **medium** Whisper model (~1.5 GB, one time).

## Defaults (in `.env`)

```env
TILD_STT_BACKEND=faster-whisper
TILD_WHISPER_MODEL=medium
TILD_WHISPER_DEVICE=cpu
TILD_WHISPER_COMPUTE_TYPE=int8
TILD_TTS_BACKEND=edge
```

| Setting | What it does |
|---------|----------------|
| **faster-whisper** | Same Whisper models, faster → you can use **medium** on a Mac for free |
| **medium** | Much better accents / Swedish / Arabic than `small` |
| **edge-tts** | Free Microsoft **neural** voices (EN, SV, AR) — no API key |

Restart API: `python3 tild_api.py`

## Slow responses?

Each voice turn runs: **Whisper (CPU)** → **Ollama** → **TTS**. That takes time.

Speed up hearing (`.env`):

```env
TILD_WHISPER_MODEL=small
```

GUI: use `include_audio=true` on `/voice/chat` (one HTTP call instead of chat + speak).

## Two voices at once?

Your UI is probably playing **both** server MP3 and **browser** `speechSynthesis`. Use only one — see `TILD_UI_VOICE_INTEGRATION.md`.

## GUI: send language every voice request

Wrong language detection is the #1 issue with code-switching. In tild-ui:

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
TILD_WHISPER_MODEL=small
```

Or larger (best hearing, slower):

```env
TILD_WHISPER_MODEL=large-v3
```

## Fallback to old stack

```env
TILD_STT_BACKEND=whisper
TILD_WHISPER_MODEL=small
TILD_TTS_BACKEND=macos
```

## Voice map (override in `.env`)

```env
TILD_EDGE_VOICE_EN=en-US-JennyNeural
TILD_EDGE_VOICE_SV=sv-SE-SofieNeural
TILD_EDGE_VOICE_AR=ar-SA-ZariyahNeural
```

List more: `edge-tts --list-voices | grep -E 'sv-SE|ar-|en-US'`
