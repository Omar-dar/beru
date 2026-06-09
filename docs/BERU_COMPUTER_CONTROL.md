# Beru computer control (owner-only)

Beru can perform **real actions on your machine** when you are logged in as **Omar** (password verified).

## Enable

In `.env` (on by default):

```env
BERU_COMPUTER_CONTROL=1
BERU_WEB_SEARCH=1
```

Restart the API after changes.

## What Beru can do today (computer agent)

**Natural wording OK** — you do not need exact phrases. Beru uses flexible NLU + Ollama fallback (owner only).

| Examples (any similar wording works) | Action |
|--------------------------------------|--------|
| “What’s the weather in Stockholm?” / “Is it raining in Gothenburg?” | Search + real weather answer |
| “Find latest news on AI” / “Look up Python asyncio” | Google + read page |
| “Open youtube.com” / “Take me to GitHub” | Open URL + read page |
| “What can you see?” / “Read that for me” | Browser or screen |
| “Go back to Beru” | End session, focus app |

## What Beru does **not** do yet

- Full mouse/keyboard remote control
- See your screen live without a screenshot command
- Run arbitrary shell commands

## UI integration (voice + chat)

Responses include:

```json
{
  "response": "...",
  "source": "search",
  "activity": "searching",
  "opened_url": "https://www.google.com/search?q=..."
}
```

- `source`: `"search"` or `"web_search"` → voice UI **searching** mode + WEB badge
- `source`: `"computer"` → browser open / screenshot (no WEB badge unless `activity` is `searching`)
- `activity`: optional — `"searching"`, `"browsing"`, `"screenshot"`

`GET /computer/capabilities` — feature flags for the UI.

## Install deps

```powershell
.venv\Scripts\pip.exe install duckduckgo-search mss
```

## Security

Computer control is **owner-only**. Guests cannot trigger browser or screenshot actions.
