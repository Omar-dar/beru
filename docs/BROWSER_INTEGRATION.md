# Browser integration (beru-ui Electron + backend)

Backend spec for the floating browser widget, Playwright scraping, and `client_actions`.

## Response fields

`POST /chat`, `POST /voice/chat`, `GET /start` (when applicable):

```json
{
  "response": "ONLY facts from scraped page or weather API — never guess",
  "language": "en",
  "text_direction": "ltr",
  "activity": "reading_page",
  "source": "search",
  "search_query": "weather Stockholm today",
  "browser_url": "https://www.google.com/search?q=weather+stockholm",
  "page_title": "Google Search",
  "opened_url": "https://www.google.com/search?q=weather+stockholm",
  "client_actions": [
    { "type": "open_url", "url": "https://www.google.com/search?q=weather+stockholm" }
  ]
}
```

## `activity` values

| Value | When |
|-------|------|
| `searching` | Opening search / loading (legacy; search now usually ends at `reading_page`) |
| `browsing` | Browser tab open, no readable scrape yet |
| `reading_page` | (internal) busy reading — UI should not stay here after reply |
| `idle` | Beru finished — overlay/voice work again. Use `browser_open: true` if Chrome tab still open |
| `browser_open` | `true` when a tab is open but Beru is ready to listen (paired with `activity: idle`) |

## `client_actions`

| type | Purpose |
|------|---------|
| `open_url` | Electron navigates in browser — **reuse existing tab when `reuse_tab: true`** |
| `close_tab` | Close browser tab — optional `site` (e.g. `facebook`) to pick the right tab |
| `scroll` | Scroll page — `{ direction: "up"|"down"|"top"|"bottom", amount: 1 }` |
| `scroll_to_text` | Scroll until snippet visible — `{ text: "..." }` |
| `focus_app` | Electron focuses Beru window, hides float widget |

### `open_url` action

```json
{
  "type": "open_url",
  "url": "https://www.google.com",
  "reuse_tab": true
}
```

- **`url`** must be a full URL with scheme (backend normalizes spoken names: `Google` → `https://www.google.com`, `Facebook hemsida` → `https://www.facebook.com`).
- **`reuse_tab: true`** (default): navigate the **current** browser tab instead of opening a new tab every turn. Set `false` only when the user explicitly asks for a new tab.
- Without a TLD, Firefox/Chrome fail with “Server Not Found” — backend always adds `.com` or uses known site aliases before sending `client_actions`.

End session example:

```json
{
  "response": "Back in Beru. What else?",
  "activity": "idle",
  "client_actions": [{ "type": "focus_app" }]
}
```

Triggers: “go back”, “back to beru”, “close browser”, etc.

## Critical rules (implemented)

1. **Playwright** loads the URL headless and reads `body` inner text.
2. **No DuckDuckGo snippet guessing** for user-facing answers.
3. **Weather** uses OpenWeather API when `OPENWEATHER_KEY` is set (real API, not LLM).
4. **“What can you see?”** re-scrapes the last `browser_url` or uses stored `page_text`.
5. **No URLs in spoken `response`** — `browser_url` is for UI “Opened: …” only.
6. **Electron opens the visible browser** via `client_actions`; backend does not call `webbrowser.open()`.

## Setup

```powershell
.venv\Scripts\pip.exe install playwright
.venv\Scripts\playwright.exe install chromium
```

Optional weather API in `.env`:

```env
OPENWEATHER_KEY=your_key_here
```

## Quick test (with beru-ui Electron)

```powershell
# Terminal 1 — backend
.venv\Scripts\python.exe beru_api.py

# Terminal 2 — UI
npm run electron:dev
```

1. “Search Google for weather in Stockholm” → float stays up, Chrome opens, reply is real weather or scraped text.
2. “What can you see?” → same page text, no invented WhatsApp/dictionary content.
3. “Go back to Beru” → `activity: idle`, `focus_app`, float hides.

## Files

| File | Role |
|------|------|
| `src/browser_scraper.py` | Playwright scrape + text extraction |
| `src/computer_control.py` | Intents, `client_actions`, session memory |
| `src/api_contract.py` | `browser_url`, `search_query`, `client_actions` in JSON |
| `chat/chat.py` | Routes owner browser commands before LLM |
