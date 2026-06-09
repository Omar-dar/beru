"""Owner-only computer actions: browser search, open URLs, screenshots (Windows/macOS/Linux)."""

from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.project_env import load_project_dotenv

load_project_dotenv()

SCREENSHOT_DIR = os.path.join('data', 'screenshots')

BROWSER_SEARCH_TRIGGERS = (
    'search google', 'google search', 'search on google', 'google for',
    'search the web', 'search the internet', 'browse the web', 'browse the internet',
    'browse for', 'look up online', 'look it up online',
    'open the browser and search', 'open browser and search',
    'open the browser and look', 'open browser and look',
    'search on the browser', 'search on browser', 'search in the browser',
    'sök på google', 'sök google', 'sök på nätet', 'sök internet',
    'ابحث في جوجل', 'ابحث في الانترنت', 'ابحث على الانترنت',
)

OPEN_URL_TRIGGERS = (
    'open url', 'open the url', 'open a link', 'open the link', 'open link',
    'go to ', 'open website', 'open site', 'open page', 'navigate to', 'browse to',
    'visit ', 'öppna ', 'gå till ', 'افتح ',
)

_OPEN_URL_PLACEHOLDERS = frozenset({
    'a link', 'link', 'links', 'the link', 'a url', 'url', 'urls', 'the url',
    'a website', 'website', 'a site', 'site', 'some link', 'that link', 'this link',
})

SCREENSHOT_TRIGGERS = (
    'take a screenshot', 'take screenshot', 'screenshot my screen', 'capture my screen',
    'ta en skärmdump', 'skärmdump',
)

# See what's on screen / in browser — general agent vision (not weather-specific).
SEE_COMPUTER_TRIGGERS = (
    'what can you see', 'what do you see', 'what are you seeing',
    "what's on my screen", 'what is on my screen', 'see my screen', 'look at my screen',
    'what can you see on my computer', 'what do you see on my computer',
    'look at my computer', 'see my computer', 'on my computer',
    "what's on my computer", 'what is on my computer', 'look at my desktop',
    'what is on the screen', "what's on the screen",
    'look at the browser', 'look at browser', 'look in the browser',
    'read the browser', 'read whats on the browser', "read what's on the browser",
    'read what is on the browser', 'what is on the browser', "what's on the browser",
    'what can you see in the browser', 'what do you see in the browser',
    'tell me what you see', 'tell me what you can see',
    'can you read it', 'can you read that', 'read it for me', 'read that page',
    'read the page', 'read whats on the page', "read what's on the page",
    'vad ser du', 'vad finns på skärmen', 'läs webbläsaren', 'läs sidan',
    'vad ser du i webbläsaren', 'ماذا ترى', 'اقرأ الصفحة', 'اقرأ المتصفح',
)

TAKEOVER_TRIGGERS = (
    'take over', 'control my computer', 'use my computer', 'access my computer',
    'control the computer', 'ta över', 'تحكم في جهازي',
)

# Ability questions — explain what Beru can do (not an actionable open/search yet).
BROWSER_CAPABILITY_TRIGGERS = (
    'browse my browser', 'use my browser', 'access my browser', 'control my browser',
    'can you use my browser', 'can you access my browser', 'can you control my browser',
    'can you open a link', 'can you open links',
    'can you open urls', 'can you open websites', 'can you open sites',
    'can you visit links', 'can you visit websites', 'can you visit a site',
    'do you have access to my browser', 'do you have access to my computer',
    'what can you open', 'what links can you open',
    'kan du öppna en länk', 'kan du använda min webbläsare', 'kan du surfa',
)


@dataclass
class ComputerActionResult:
    ok: bool
    message: str
    activity: str = ''
    source: str = 'computer'
    opened_url: str = ''
    browser_url: str = ''
    screenshot_path: str = ''
    query: str = ''
    search_query: str = ''
    summary: str = ''
    page_title: str = ''
    page_text: str = ''
    client_actions: list = field(default_factory=list)
    browser_open: bool = False


BROWSER_BUSY_ACTIVITIES = frozenset({'searching', 'browsing', 'reading_page'})


COMPUTER_FOLLOWUP_TRIGGERS = (
    'what did you find', 'what did you open', 'what did you search',
    'what is it', "what's that", 'what is that', 'what was that',
    'tell me what you found', 'tell me what you opened', 'tell me about it',
    'read that', 'read it for me', 'read it to me', 'read for me',
    'read the browser', 'read the page', 'can you read', 'could you read',
    "tell me what's the weather", 'tell me the weather', 'what is the weather',
    "what's the weather", 'summarize', 'summary of', 'what about that',
    'what is on that page', "what's on that page",
    'what can you see', 'what do you see', 'what are you seeing',
    'vad hittade du', 'vad öppnade du', 'vad är det', 'vad ser du',
    'läs det', 'vad är vädret',
)

BROWSER_END_TRIGGERS = (
    'go back', 'back to beru', 'back to the app', 'back in beru',
    'close the browser', 'close browser', 'focus beru', 'return to beru',
    'come back to beru', 'back to app', 'tillbaka till beru',
)

CLOSE_TAB_TRIGGERS = (
    'close the tab', 'close this tab', 'close that tab', 'close tab',
    'close current tab', 'close the browser tab', 'close browser tab',
    'close the tap', 'close this tap', 'close that tap', 'close tap',
    'shut the tab', 'shut this tab', 'dismiss the tab', 'dismiss this tab',
    'enclose this tab', 'enclose the tab', 'inclose this tab',
    'stäng fliken', 'stäng den här fliken', 'stäng denna flik', 'stäng flik',
    'اغلق التبويب', 'أغلق التبويب',
)

SCROLL_PAGE_TRIGGERS = (
    'scroll down', 'scroll up', 'scroll to top', 'scroll to bottom',
    'page down', 'page up', 'scroll the page', 'scroll on the page',
    'scroll a bit', 'scroll more', 'keep scrolling',
    'rulla ner', 'rulla upp', 'scrolla ner', 'scrolla upp',
)

FIND_ON_PAGE_TRIGGERS = (
    'show me on the page', 'find on the page', 'on the page find',
    'scroll to', 'go to on the page', 'where is on the page',
    'show me on facebook', 'find on facebook', 'show me on google',
    'visa mig på sidan', 'hitta på sidan', 'scrolla till',
)

_TAB_SITE_NAMES = (
    'facebook', 'google', 'youtube', 'github', 'instagram', 'reddit', 'twitter', 'smhi',
)

_WEATHER_WORDS = frozenset({
    'weather', 'temperature', 'forecast', 'väder', 'vädret', 'temperatur', 'grader',
    'طقس', 'الجو',
})

_QUERY_NOISE_PREFIXES = (
    'on google ', 'on google for ', 'google for ', 'google ',
    'on the web for ', 'the web for ', 'the internet for ', 'for ',
)


def computer_control_enabled() -> bool:
    return os.getenv('BERU_COMPUTER_CONTROL', '1').strip().lower() in ('1', 'true', 'yes')


def _extract_after_triggers(text: str, triggers: tuple[str, ...]) -> str:
    tl = text.lower().strip()
    for trigger in sorted(triggers, key=len, reverse=True):
        idx = tl.find(trigger)
        if idx >= 0:
            rest = text[idx + len(trigger):].strip(' :.,!?')
            if rest:
                return rest
    return ''


def _extract_url(text: str) -> str:
    match = re.search(r'https?://[^\s<>"\']+', text, re.I)
    if match:
        return match.group(0).rstrip('.,)')
    domain = re.search(
        r'\b(?:www\.)?[a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:/[^\s]*)?',
        text,
        re.I,
    )
    if domain:
        url = domain.group(0).rstrip('.,)')
        if not url.lower().startswith('http'):
            url = 'https://' + url
        return url
    return ''


def _clean_search_query(raw: str) -> str:
    q = (raw or '').strip(' ?.,!')
    if not q:
        return ''
    lowered = q.lower()
    changed = True
    while changed:
        changed = False
        for prefix in _QUERY_NOISE_PREFIXES:
            if lowered.startswith(prefix):
                q = q[len(prefix):].strip(' ?.,!')
                lowered = q.lower()
                changed = True
                break
    if lowered in ('google', 'the web', 'the internet', 'online'):
        return ''
    return q


def _refine_weather_query(text: str, query: str) -> str:
    """Fix voice STT garble; pull city from full sentence."""
    from src.search import BeruSearch

    blob = f'{text} {query}'.lower()
    if not _is_weather_query(blob):
        return query
    city = BeruSearch._extract_city_from_weather_query(query, text)
    if city and city != 'Stockholm' or 'stockholm' in blob:
        return f'weather in {city} today'
    if 'talking' in query.lower() or len(query.split()) > 8:
        return f'weather in {city} today'
    return query


def _extract_search_query(text: str) -> str:
    rest = _extract_after_triggers(text, BROWSER_SEARCH_TRIGGERS)
    if rest:
        cleaned = _clean_search_query(rest)
        if len(cleaned) >= 2:
            return _refine_weather_query(text, cleaned)
    for pattern in (
        r'search\s+on\s+(?:the\s+)?browser\s*,?\s*(?:what(?:\'s| is)\s+)?(?:the\s+)?(.+)',
        r'open\s+(?:the\s+)?browser\s+(?:and\s+)?search\s+(?:for\s+)?(?:what(?:\'s| is)\s+)?(?:the\s+)?(.+)',
        r'search\s+(?:what|for)\s+(?:is\s+)?(?:the\s+)?(.+)',
        r'(?:search|look up)(?:\s+\w+){0,4}\s+(?:on\s+)?google\s+(?:for\s+)?(.+)',
        r'(?:search|google|browse|look up)(?:\s+\w+){0,3}\s+for\s+(.+)',
        r'(?:sök|sök på)\s+(?:google|nätet|internet)?\s*(?:efter\s+)?(.+)',
        r'(?:ابحث(?: في)?(?: جوجل| الانترنت| على الانترنت)?(?: عن)?)\s*(.+)',
    ):
        m = re.search(pattern, text, re.I)
        if m:
            cleaned = _clean_search_query(m.group(1))
            if len(cleaned) >= 2:
                return _refine_weather_query(text, cleaned)
    for pattern in (
        r'(?:look up|find out about|tell me about)\s+(.+)',
        r'search for\s+(.+)',
        r'find\s+(.+?)\s+online',
    ):
        m = re.search(pattern, text, re.I)
        if m:
            cleaned = _clean_search_query(m.group(1))
            if len(cleaned) >= 2:
                return _refine_weather_query(text, cleaned)
    return ''


def _domain_from_url(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc
        return host.replace('www.', '') if host else url
    except Exception:
        return url


def _is_weather_query(query: str) -> bool:
    return any(w in query.lower() for w in _WEATHER_WORDS)


def _open_url_client_action(url: str, *, reuse_tab: bool = True) -> dict:
    return {'type': 'open_url', 'url': url, 'reuse_tab': reuse_tab}


def _focus_app_client_action() -> dict:
    return {'type': 'focus_app'}


def _close_tab_client_action(*, site: str = '') -> dict:
    action: dict = {'type': 'close_tab'}
    if site:
        action['site'] = site
    return action


def _scroll_client_action(direction: str, *, amount: int = 1) -> dict:
    return {'type': 'scroll', 'direction': direction, 'amount': amount}


def _scroll_to_text_client_action(text: str) -> dict:
    return {'type': 'scroll_to_text', 'text': text}


def _parse_tab_site(text: str) -> str:
    tl = (text or '').lower()
    for site in _TAB_SITE_NAMES:
        if site in tl:
            return site
    return ''


def _is_close_tab_request(tl: str) -> bool:
    if any(t in tl for t in CLOSE_TAB_TRIGGERS):
        return True
    return bool(re.search(
        r'\b(?:close|shut|dismiss|enclose|inclose)\s+(?:the\s+)?(?:\w+\s+){0,2}(?:tab|tap)\b',
        tl,
    ))


def _parse_scroll_direction(tl: str) -> str:
    if any(x in tl for x in ('scroll up', 'page up', 'rulla upp', 'scrolla upp', 'to top')):
        return 'up'
    if any(x in tl for x in ('to bottom', 'scroll to bottom')):
        return 'bottom'
    if any(x in tl for x in ('to top', 'scroll to top')):
        return 'top'
    return 'down'


def _extract_find_on_page_query(text: str) -> str:
    for pattern in (
        r'(?:show|find|locate|highlight)\s+(?:me\s+)?(.+?)(?:\s+on\s+(?:the\s+)?(?:page|site|tab|browser|facebook|google))',
        r'(?:scroll|go)\s+to\s+(.+?)(?:\s+on\s+(?:the\s+)?(?:page|site|tab))?',
        r'(?:where\s+is|where\'s|wheres)\s+(.+?)(?:\s+on\s+(?:the\s+)?(?:page|site|tab))?',
        r'(?:show|find)\s+(?:me\s+)?(.+)$',
    ):
        m = re.search(pattern, text, re.I)
        if m:
            q = m.group(1).strip(' .,!?')
            if len(q) >= 2 and q.lower() not in ('it', 'that', 'this', 'the page', 'the tab'):
                return q
    return ''


def _looks_like_cookie_wall(text: str) -> bool:
    low = (text or '').lower()
    return any(
        x in low
        for x in (
            'before you continue', 'accept all', 'cookie', 'consent',
            'privacy policy', 'koldioxidneutralt', 'leverera och underhålla',
        )
    )


def _find_text_on_page(page_text: str, query: str) -> str:
    """Return a line/snippet from page_text that matches query, or ''."""
    if not page_text or not query:
        return ''
    q_words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 2]
    if not q_words:
        return ''
    best = ''
    best_score = 0
    for ln in page_text.splitlines():
        ln = ln.strip()
        if len(ln) < 8:
            continue
        low = ln.lower()
        score = sum(1 for w in q_words if w in low)
        if score > best_score:
            best_score = score
            best = ln
    if best_score > 0:
        return best[:240]
    collapsed = ' '.join(page_text.split())
    low = collapsed.lower()
    idx = low.find(q_words[0])
    if idx >= 0:
        start = max(0, idx - 40)
        end = min(len(collapsed), idx + 200)
        return collapsed[start:end].strip()
    return ''

def _weather_api_answer(query: str, full_text: str = '') -> str:
    """Real weather APIs only — never LLM."""
    blob = f'{full_text} {query}'.strip()
    if not _is_weather_query(blob):
        return ''
    from src.search import BeruSearch

    return BeruSearch().get_weather(query, full_text=full_text or query) or ''


def _answer_from_search(query: str, full_text: str, language: str) -> tuple[str, str, str, str, str]:
    """
    Returns (spoken_message, summary, page_text, page_title, error).
    Weather: real API first (fast, reliable). Other topics: scrape Google results.
    """
    blob = f'{full_text} {query}'
    if _is_weather_query(blob):
        weather = _weather_api_answer(query, full_text=full_text)
        if weather:
            return weather, weather, '', '', ''
        google_url = _google_search_url(query)
        facts, page_text, page_title, scrape_err = _facts_from_url(google_url, query, language)
        if facts:
            return facts, facts, page_text, page_title, ''
        return '', '', page_text, page_title, scrape_err or 'weather lookup failed'

    google_url = _google_search_url(query)
    facts, page_text, page_title, scrape_err = _facts_from_url(google_url, query, language)
    if facts:
        return facts, facts, page_text, page_title, ''
    return '', '', page_text, page_title, scrape_err or 'could not read the page'


def _facts_from_url(url: str, query: str, language: str) -> tuple[str, str, str, str]:
    """Scrape URL in a worker thread so Flask/voice stays responsive."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    from src.browser_scraper import extract_facts_from_page, scrape_url

    def _scrape_work():
        scrape = scrape_url(url)
        if not scrape.ok:
            return '', '', '', scrape.error or 'scrape failed'
        facts = extract_facts_from_page(scrape.text, query)
        if not facts:
            return '', scrape.text[:2000], scrape.title, 'no readable text on page'
        return facts, scrape.text[:4000], scrape.title, ''

    from src.performance import scrape_timeout_ms

    timeout = scrape_timeout_ms() / 1000 + 8
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_scrape_work).result(timeout=timeout)
    except FuturesTimeout:
        return '', '', '', 'scrape timed out'
    except Exception as exc:
        return '', '', '', str(exc)


def _browser_result_fields(
    *,
    url: str,
    query: str = '',
    client_actions: list | None = None,
) -> dict:
    actions = client_actions if client_actions is not None else [_open_url_client_action(url)]
    return {
        'opened_url': url,
        'browser_url': url,
        'search_query': query,
        'query': query,
        'client_actions': actions,
    }


def release_overlay_for_ui(action: ComputerActionResult) -> ComputerActionResult:
    """
    beru-ui float overlay blocks stop/voice while activity is searching|browsing|reading_page.
    After we have a spoken answer, return to idle so the widget responds again.
    Browser may stay open — browser_open tells the UI to keep the link chip visible.
    """
    if action.ok and (action.message or '').strip() and action.activity in BROWSER_BUSY_ACTIVITIES:
        url = action.browser_url or action.opened_url
        action.activity = 'idle'
        if url:
            action.browser_open = True
    return action


def apply_turn_meta(meta: dict, action: ComputerActionResult) -> None:
    """Push browser session fields into chat turn meta for API/UI."""
    if action.activity:
        meta['activity'] = action.activity
    url = action.browser_url or action.opened_url
    if url:
        meta['opened_url'] = url
        meta['browser_url'] = url
    sq = action.search_query or action.query
    if sq:
        meta['search_query'] = sq
    if action.page_title:
        meta['page_title'] = action.page_title
    if action.client_actions:
        meta['client_actions'] = action.client_actions
    if action.browser_open:
        meta['browser_open'] = True
    if action.screenshot_path:
        meta['screenshot_path'] = action.screenshot_path


def remember_computer_action(memory, action: ComputerActionResult) -> None:
    if not memory:
        return

    url = action.browser_url or action.opened_url
    query = action.search_query or action.query

    if action.activity == 'idle':
        if action.browser_open and url:
            memory.set_last_computer_action(
                action_type='open_url' if not query else 'search',
                query=query,
                url=url,
                summary=action.summary or action.message,
                page_title=action.page_title,
                page_text=action.page_text,
            )
            return
        if not action.browser_open:
            memory.clear_last_computer_action()
        return

    if not action.ok:
        if url or action.query or action.search_query:
            memory.set_last_computer_action(
                action_type='search',
                query=action.search_query or action.query,
                url=url,
                summary=action.summary or action.message,
                page_title=action.page_title,
                page_text=action.page_text,
            )
        return

    if action.source == 'search' or action.activity in ('searching', 'reading_page', 'browsing'):
        memory.set_last_computer_action(
            action_type='search' if action.search_query or action.query else 'open_url',
            query=action.search_query or action.query,
            url=url,
            summary=action.summary or action.message,
            page_title=action.page_title,
            page_text=action.page_text,
        )
    elif action.opened_url or action.browser_url:
        memory.set_last_computer_action(
            action_type='open_url',
            url=url,
            summary=action.summary or action.message,
            page_title=action.page_title,
            page_text=action.page_text,
        )
    elif action.screenshot_path:
        memory.set_last_computer_action(
            action_type='screenshot',
            summary=action.message,
        )


def is_browser_session_end(text: str) -> bool:
    tl = text.lower().strip()
    return any(t in tl for t in BROWSER_END_TRIGGERS)


def execute_browser_end(*, language: str = 'en') -> ComputerActionResult:
    return ComputerActionResult(
        ok=True,
        message=_msg('back_in_beru', language),
        activity='idle',
        source='computer',
        client_actions=[_focus_app_client_action()],
    )


def is_computer_followup(text: str, memory) -> bool:
    if not memory or not getattr(memory, 'is_owner', lambda: False)():
        return False
    if not memory.get_last_computer_action():
        return False
    from src.computer_nlu import extract_search_topic

    if getattr(memory, 'is_chat_only_message', lambda _t: False)(text):
        return False
    if memory.is_casual_conversation_reply(text):
        return False

    if parse_computer_intent(text) == 'browser_search' and extract_search_topic(text):
        return False
    tl = text.lower().strip()
    if any(t in tl for t in COMPUTER_FOLLOWUP_TRIGGERS):
        return True
    if len(tl.split()) <= 14 and re.search(
        r'\b(it|this|there|again|same|repeat)\b', tl
    ):
        return True
    if re.search(r"\bthat's\b|\bthat is\b", tl) and any(
        w in tl for w in ('read', 'see', 'show', 'tell', 'weather', 'page', 'screen', 'browser')
    ):
        return True
    if re.search(r'\b(it|that|this|the page|the site|the tab|the screen)\b', tl) and any(
        w in tl for w in ('what', 'tell', 'read', 'explain', 'describe', 'show')
    ):
        return True
    return False


def _read_browser_answer(query: str, url: str, full_text: str, language: str):
    """Answer from weather API or scraped page. Returns message, summary, page_text, page_title, err."""
    if _is_weather_query(f'{full_text} {query}'):
        weather = _weather_api_answer(query or full_text, full_text=full_text)
        if weather:
            return weather, weather, '', '', ''
    if url:
        facts, page_text, page_title, err = _facts_from_url(url, query, language)
        if facts:
            return facts, facts, page_text, page_title, ''
        return '', page_text, page_title, err
    return '', '', '', '', 'no browser session'


def answer_computer_followup(text: str, memory, *, language: str = 'en') -> ComputerActionResult:
    last = memory.get_last_computer_action()
    query = last.get('query') or ''
    url = last.get('url') or ''
    tl = text.lower()

    wants_read = any(
        p in tl
        for p in (
            'read it', 'read the browser', 'read the page', 'can you read',
            'tell me the weather', "tell me what's the weather", "what's the weather",
            'what is the weather', 'read for me',
        )
    ) or _is_weather_query(tl)

    if wants_read and (url or query):
        message, summary, page_text, page_title, _err = _read_browser_answer(
            query, url, text, language
        )
        if message:
            memory.update_last_computer_summary(message)
            if page_text:
                memory.update_last_computer_page(page_text, page_title)
            return ComputerActionResult(
                ok=True,
                message=message,
                activity='reading_page',
                source='search' if query else 'computer',
                summary=summary,
                page_title=page_title if isinstance(page_title, str) and len(page_title) < 200 else '',
                page_text=page_text if isinstance(page_text, str) else '',
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )
        if last.get('summary'):
            return ComputerActionResult(
                ok=True,
                message=last['summary'],
                activity='reading_page',
                source='search' if query else 'computer',
                summary=last['summary'],
                page_title=last.get('page_title', ''),
                page_text=last.get('page_text', ''),
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )

    wants_see = any(p in tl for p in ('what can you see', 'what do you see', 'what are you seeing', 'vad ser du'))

    if wants_see and url:
        facts, page_text, page_title, err = _facts_from_url(url, query, language)
        if facts:
            memory.update_last_computer_summary(facts)
            memory.update_last_computer_page(page_text, page_title)
            return ComputerActionResult(
                ok=True,
                message=facts,
                activity='reading_page',
                source='search' if query else 'computer',
                summary=facts,
                page_title=page_title,
                page_text=page_text,
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )
        if last.get('page_text'):
            from src.browser_scraper import extract_facts_from_page

            facts = extract_facts_from_page(last['page_text'], query)
            if facts:
                return ComputerActionResult(
                    ok=True,
                    message=facts,
                    activity='reading_page',
                    source='search' if query else 'computer',
                    summary=facts,
                    page_title=last.get('page_title', ''),
                    page_text=last.get('page_text', ''),
                    **_browser_result_fields(url=url, query=query, client_actions=[]),
                )
        return ComputerActionResult(
            ok=False,
            message=_msg('scrape_empty', language, err=err or 'no stored page'),
            activity='browsing',
            source='computer',
            **_browser_result_fields(url=url, query=query, client_actions=[]),
        )

    if last.get('summary') and not wants_see:
        return ComputerActionResult(
            ok=True,
            message=last['summary'],
            activity='reading_page',
            source='search' if query else 'computer',
            summary=last['summary'],
            page_title=last.get('page_title', ''),
            page_text=last.get('page_text', ''),
            **_browser_result_fields(url=url, query=query, client_actions=[]),
        )

    if last.get('type') == 'open_url' and url:
        site = _domain_from_url(url)
        msg = _msg('followup_opened', language, site=site)
        return ComputerActionResult(
            ok=True,
            message=msg,
            activity='browsing',
            source='computer',
            summary=msg,
            **_browser_result_fields(url=url, client_actions=[]),
        )

    return ComputerActionResult(
        ok=False,
        message=_msg('followup_unknown', language),
        activity='browsing',
        source='computer',
    )


def _open_url_target(text: str) -> str:
    """URL or domain from message, or remainder after an open-url trigger."""
    from src.url_normalize import normalize_open_url

    url = _extract_url(text)
    if url:
        return normalize_open_url(url)
    rest = _extract_after_triggers(text, OPEN_URL_TRIGGERS)
    if rest and rest.lower().strip() not in _OPEN_URL_PLACEHOLDERS:
        return normalize_open_url(rest)
    m = re.search(
        r'\b(?:open|öppna|go to|visit|gå till|navigate to|browse to)\s+(?:the\s+)?(.+)$',
        text,
        re.I,
    )
    if m:
        candidate = m.group(1).strip(' .,!?')
        if candidate.lower() not in _OPEN_URL_PLACEHOLDERS and len(candidate) >= 2:
            if not re.search(r'\b(search|find|for|weather|väder|sök|efter|look up)\b', candidate, re.I):
                return normalize_open_url(candidate)
    return ''


def is_action_confirm(text: str) -> bool:
    tl = (text or '').lower().strip().strip('.!,')
    if not tl:
        return False
    if any(p in tl for p in (
        'do it', 'go ahead', 'go on', 'yeah do', 'yes do', 'please do',
        'gör det', 'kör', 'gör det nu',
    )):
        return True
    if len(tl.split()) <= 4 and any(
        p in tl for p in ('yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'ja', 'japp', 'نعم', 'أيوه')
    ):
        return True
    return False


def execute_pending_client_actions(memory, *, language: str = 'en') -> ComputerActionResult | None:
    pending = memory.get_pending_client_actions() if memory else []
    if not pending:
        return None
    label = (memory.session.get('pending_action_label') or 'that').strip()
    memory.clear_pending_client_actions()
    return ComputerActionResult(
        ok=True,
        message=_msg('pending_action_ok', language, label=label),
        activity='browsing',
        source='computer',
        client_actions=pending,
        browser_open=True,
    )


def parse_computer_intent(text: str) -> Optional[str]:
    """Return action id: browser_search, open_url, screenshot, takeover_help, etc."""
    if not text:
        return None
    tl = text.lower().strip()
    if any(t in tl for t in TAKEOVER_TRIGGERS):
        return 'takeover_help'
    if _is_close_tab_request(tl):
        return 'close_tab'
    if any(t in tl for t in SCROLL_PAGE_TRIGGERS) or re.search(
        r'\bscroll\s+(?:down|up|to)\b', tl
    ):
        return 'scroll_page'
    if any(t in tl for t in FIND_ON_PAGE_TRIGGERS) or re.search(
        r'\b(?:show|find|locate)\s+me\b', tl
    ) and re.search(r'\b(?:page|site|tab|facebook|google|browser)\b', tl):
        return 'find_on_page'
    if any(t in tl for t in SCREENSHOT_TRIGGERS):
        return 'screenshot'
    if any(t in tl for t in SEE_COMPUTER_TRIGGERS):
        return 'see_computer'
    if re.search(
        r'\b(look at|read|see)\s+(?:the\s+)?browser\b', tl
    ) or re.search(r'\bread\s+(?:it|that|the page)\b', tl):
        return 'see_computer'
    if re.search(
        r'\b(?:open|öppna|go to|visit|gå till)\s+(?:the\s+)?(?:google|facebook|youtube|github|smhi|instagram|reddit)\b',
        tl,
    ) and not re.search(r'\b(search|find|for|weather|väder|sök|look up)\b', tl):
        return 'open_url'
    if any(t in tl for t in BROWSER_SEARCH_TRIGGERS):
        return 'browser_search'
    if re.search(r'open\s+(?:the\s+)?browser', tl) and re.search(r'\bsearch\b', tl):
        return 'browser_search'
    if re.search(r'\bgoogle\b', tl) and re.search(r'\b(search|for|find)\b', tl):
        return 'browser_search'
    if re.search(r'\b(look up|find out|search for|tell me about)\b', tl):
        return 'browser_search'
    if any(t in tl for t in BROWSER_CAPABILITY_TRIGGERS):
        return 'takeover_help'
    if _extract_url(text) or any(t in tl for t in OPEN_URL_TRIGGERS):
        return 'open_url'
    return None


def is_computer_control_request(
    text: str, *, is_owner: bool, memory=None, brain=None,
) -> bool:
    if not computer_control_enabled() or not is_owner:
        return False
    if parse_computer_intent(text):
        return True
    from src.computer_nlu import extract_search_topic, is_natural_computer_request

    has_session = bool(memory and memory.get_last_computer_action())
    if is_natural_computer_request(text, has_browser_session=has_session):
        return True
    if _extract_url(text):
        return True
    return False


def capabilities() -> dict:
    from src.browser_scraper import playwright_available

    screenshot_ok = _screenshot_available()
    return {
        'enabled': computer_control_enabled(),
        'owner_only': True,
        'browser_search': True,
        'open_url': True,
        'screenshot': screenshot_ok,
        'playwright': playwright_available(),
        'web_search_source': 'search',
        'activities': ['searching', 'browsing', 'reading_page', 'idle'],
        'client_actions': ['open_url', 'focus_app', 'close_tab', 'scroll', 'scroll_to_text'],
        'see_computer': True,
        'read_browser_page': True,
        'notes': (
            'Owner agent: search the web, open URLs, read page text (Playwright), '
            'capture screen (screenshot), answer what I see in browser or on screen.'
        ),
    }


def _screenshot_available() -> bool:
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


def _google_search_url(query: str) -> str:
    return 'https://www.google.com/search?q=' + urllib.parse.quote(query)


def _take_screenshot() -> str:
    import mss
    from mss import tools

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(SCREENSHOT_DIR, f'beru_screen_{stamp}.png')
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        shot = sct.grab(monitor)
        tools.to_png(shot.rgb, shot.size, output=path)
    return path


def _execute_see_computer(text: str, *, language: str = 'en', memory=None) -> ComputerActionResult:
    """Read open browser tab — screenshot only when user asks about screen/desktop."""
    last = memory.get_last_computer_action() if memory else {}
    url = (last or {}).get('url') or ''
    query = (last or {}).get('query') or ''
    tl = (text or '').lower()
    wants_screen = bool(re.search(r'\b(screen|desktop)\b', tl))

    if url and not wants_screen:
        facts, page_text, page_title, err = _facts_from_url(url, query, language)
        if facts:
            if memory:
                memory.update_last_computer_summary(facts)
                memory.update_last_computer_page(page_text, page_title)
            return ComputerActionResult(
                ok=True,
                message=facts,
                activity='reading_page',
                source='computer',
                summary=facts,
                page_title=page_title,
                page_text=page_text,
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )
        if last.get('page_text'):
            from src.browser_scraper import extract_facts_from_page

            facts = extract_facts_from_page(last['page_text'], query)
            if facts:
                return ComputerActionResult(
                    ok=True,
                    message=facts,
                    activity='reading_page',
                    source='computer',
                    summary=facts,
                    page_title=last.get('page_title', ''),
                    page_text=last['page_text'],
                    **_browser_result_fields(url=url, query=query, client_actions=[]),
                )
        if page_text and _looks_like_cookie_wall(page_text):
            site = _domain_from_url(url)
            return ComputerActionResult(
                ok=True,
                message=_msg('cookie_wall', language, site=site),
                activity='browsing',
                source='computer',
                summary='',
                page_title=page_title,
                page_text=page_text,
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )
        if err:
            return ComputerActionResult(
                ok=False,
                message=_msg('scrape_empty', language, err=err),
                activity='browsing',
                source='computer',
                **_browser_result_fields(url=url, query=query, client_actions=[]),
            )
        site = _domain_from_url(url)
        return ComputerActionResult(
            ok=True,
            message=_msg('see_page_empty', language, site=site),
            activity='browsing',
            source='computer',
            **_browser_result_fields(url=url, query=query, client_actions=[]),
        )

    if not url and not wants_screen:
        return ComputerActionResult(
            ok=False,
            message=_msg('see_computer_help', language),
            source='computer',
        )

    if _screenshot_available() and wants_screen:
        try:
            path = os.path.abspath(_take_screenshot())
            if memory:
                memory.set_last_computer_action(
                    action_type='screenshot',
                    summary=_msg('screen_captured', language),
                    page_text='',
                )
            return ComputerActionResult(
                ok=True,
                message=_msg('screen_captured', language),
                activity='reading_page',
                source='computer',
                screenshot_path=path,
                summary=_msg('screen_captured', language),
            )
        except Exception as exc:
            return ComputerActionResult(
                ok=False,
                message=_msg('screenshot_fail', language, err=str(exc)),
                source='computer',
            )

    return ComputerActionResult(
        ok=False,
        message=_msg('see_computer_help', language),
        source='computer',
    )


def execute(text: str, *, language: str = 'en', memory=None, brain=None) -> ComputerActionResult:
    from src.computer_nlu import extract_search_topic, resolve_plan

    has_session = bool(memory and memory.get_last_computer_action())
    plan = resolve_plan(text, brain=brain, has_browser_session=has_session)
    intent = plan['intent'] if plan else parse_computer_intent(text)
    planned_query = (plan or {}).get('query') or ''
    planned_url = (plan or {}).get('url') or ''

    if not intent:
        return ComputerActionResult(False, _msg('unknown', language))

    if intent == 'takeover_help':
        return ComputerActionResult(
            ok=True,
            message=_takeover_help(language),
            activity='',
            source='computer',
        )

    if intent == 'see_computer':
        return _execute_see_computer(text, language=language, memory=memory)

    if intent == 'close_tab':
        site = _parse_tab_site(text)
        label = site or _domain_from_url((memory.get_last_computer_action() or {}).get('url', ''))
        label = label or 'current'
        client_action = _close_tab_client_action(site=site)
        if memory:
            memory.set_pending_client_actions([client_action], label=f'close {label}')
        return ComputerActionResult(
            ok=True,
            message=_msg('close_tab_ok', language, site=label),
            activity='browsing',
            source='computer',
            client_actions=[client_action],
            browser_open=True,
        )

    if intent == 'scroll_page':
        direction = _parse_scroll_direction(text.lower())
        return ComputerActionResult(
            ok=True,
            message=_msg('scroll_ok', language, direction=direction),
            activity='browsing',
            source='computer',
            client_actions=[_scroll_client_action(direction)],
            browser_open=True,
        )

    if intent == 'find_on_page':
        find_q = _extract_find_on_page_query(text)
        last = memory.get_last_computer_action() if memory else {}
        url = (last or {}).get('url') or ''
        if not find_q:
            return ComputerActionResult(
                ok=False,
                message=_msg('find_need_query', language),
                source='computer',
            )
        if not url:
            return ComputerActionResult(
                ok=False,
                message=_msg('see_computer_help', language),
                source='computer',
            )
        facts, page_text, page_title, err = _facts_from_url(url, find_q, language)
        snippet = _find_text_on_page(page_text, find_q) or facts
        if snippet:
            if memory:
                memory.update_last_computer_page(page_text, page_title)
            scroll_action = _scroll_to_text_client_action(snippet[:120])
            return ComputerActionResult(
                ok=True,
                message=_msg('find_on_page_ok', language, snippet=snippet),
                activity='reading_page',
                source='computer',
                summary=snippet,
                page_title=page_title,
                page_text=page_text,
                **_browser_result_fields(
                    url=url,
                    client_actions=[scroll_action],
                ),
            )
        return ComputerActionResult(
            ok=False,
            message=_msg('find_on_page_miss', language, query=find_q),
            activity='browsing',
            source='computer',
            **_browser_result_fields(url=url, client_actions=[]),
        )

    if intent == 'screenshot':
        if not _screenshot_available():
            return ComputerActionResult(
                ok=False,
                message=_msg('screenshot_missing_dep', language),
                source='computer',
            )
        try:
            path = os.path.abspath(_take_screenshot())
            return ComputerActionResult(
                ok=True,
                message=_msg('screenshot_ok', language, path=path),
                activity='screenshot',
                source='computer',
                screenshot_path=path,
            )
        except Exception as exc:
            return ComputerActionResult(
                ok=False,
                message=_msg('screenshot_fail', language, err=str(exc)),
                source='computer',
            )

    if intent == 'open_url':
        url = planned_url or _open_url_target(text)
        if not url:
            return ComputerActionResult(
                ok=False,
                message=_msg('need_url', language),
                source='computer',
            )
        from src.url_normalize import normalize_open_url

        url = normalize_open_url(url)
        site = _domain_from_url(url)
        return ComputerActionResult(
            ok=True,
            message=_msg('opened_url', language, site=site),
            activity='browsing',
            source='computer',
            summary='',
            page_title='',
            page_text='',
            **_browser_result_fields(url=url),
        )

    if intent == 'browser_search':
        query = planned_query or _extract_search_query(text) or extract_search_topic(text)
        if not query:
            return ComputerActionResult(
                ok=False,
                message=_msg('need_query', language),
                source='computer',
            )
        google_url = _google_search_url(query)
        fields = _browser_result_fields(url=google_url, query=query)
        message, summary, page_text, page_title, err = _answer_from_search(query, text, language)

        if not message:
            return ComputerActionResult(
                ok=False,
                message=_msg('scrape_empty', language, err=err),
                activity='browsing',
                source='search',
                summary='',
                query=query,
                search_query=query,
                **fields,
            )

        return ComputerActionResult(
            ok=True,
            message=message,
            activity='reading_page',
            source='search',
            summary=summary,
            page_title=page_title,
            page_text=page_text,
            **fields,
        )

    return ComputerActionResult(False, _msg('unknown', language))


def _takeover_help(language: str) -> str:
    if language == 'sv':
        return (
            'Jag är din dator-agent bro. Jag kan: söka på nätet och läsa sidor, '
            'öppna webbplatser, fånga skärmen, och svara på "vad ser du?". '
            'Prova: "sök efter Python tutorials", "öppna youtube.com", '
            '"vad ser du på skärmen?", "vad hittade du?". '
            'Jag styr inte mus/tangentbord än.'
        )
    if language == 'ar':
        return (
            'أنا وكيل جهازك. أستطيع: البحث وقراءة الصفحات، فتح المواقع، '
            'التقاط الشاشة، والإجابة على "ماذا ترى؟". '
            'مثلاً: "ابحث عن Python"، "افتح youtube.com"، "ماذا ترى على الشاشة؟".'
        )
    return (
        'I am your computer agent bro. I can: search the web and read pages, '
        'open websites, close tabs, scroll pages, find text on a page, '
        'capture your screen, and answer "what can you see?". '
        'Try: "search for Python tutorials", "open youtube.com", '
        '"close the Facebook tab", "scroll down", "show me login on the page", '
        '"what is on my screen?", "what did you find?". '
        'I do not control mouse and keyboard yet.'
    )


def _msg(key: str, language: str, **kwargs) -> str:
    templates = {
        'opened_with_facts': {
            'en': 'Opened {site}. From the page: {facts}',
            'sv': 'Öppnade {site}. Från sidan: {facts}',
            'ar': 'فتحت {site}. من الصفحة: {facts}',
        },
        'opened_url': {
            'en': 'Opened {site} in your browser. Say "what can you see?" and I will read the page.',
            'sv': 'Öppnade {site}. Säg "vad ser du?" så läser jag sidan.',
            'ar': 'فتحت {site}. قل "ماذا ترى؟" لأقرأ الصفحة.',
        },
        'scrape_empty': {
            'en': 'I opened the page but could not read useful text ({err}). Try another search or check Playwright is installed.',
            'sv': 'Jag öppnade sidan men kunde inte läsa text ({err}).',
            'ar': 'فتحت الصفحة لكن لم أستطع قراءة نص مفيد ({err}).',
        },
        'back_in_beru': {
            'en': 'Back in Beru. What else?',
            'sv': 'Tillbaka i Beru. Vad mer?',
            'ar': 'عدنا إلى Beru. ماذا بعد؟',
        },
        'followup_opened': {
            'en': 'I opened {site} in your browser. Want me to search for something there?',
            'sv': 'Jag öppnade {site}. Vill du att jag söker efter något där?',
            'ar': 'فتحت {site}. هل تريد أن أبحث عن شيء هناك؟',
        },
        'followup_unknown': {
            'en': 'Tell me what to search, or say open and a website — I will handle it.',
            'sv': 'Säg vad jag ska söka, eller säg öppna och en webbplats.',
            'ar': 'قل ماذا أبحث، أو قل افتح وموقعاً.',
        },
        'screenshot_ok': {
            'en': 'Screenshot saved to {path}. I captured your primary screen.',
            'sv': 'Skärmdump sparad: {path}',
            'ar': 'تم حفظ لقطة الشاشة: {path}',
        },
        'screenshot_fail': {
            'en': 'Screenshot failed: {err}',
            'sv': 'Skärmdump misslyckades: {err}',
            'ar': 'فشل التقاط الشاشة: {err}',
        },
        'screenshot_missing_dep': {
            'en': 'Screenshot needs `pip install mss` in the Beru venv, then restart the API.',
            'sv': 'Skärmdump kräver `pip install mss` i venv, starta om API:t.',
            'ar': 'يلزم `pip install mss` ثم إعادة تشغيل API.',
        },
        'screen_captured': {
            'en': (
                'I captured your screen. If you have a browser tab open, ask what I see on the page. '
                'Or tell me to search for something or open a site.'
            ),
            'sv': (
                'Jag fångade skärmen. Om du har en webbläsare öppen, fråga vad jag ser. '
                'Eller säg vad jag ska söka eller öppna.'
            ),
            'ar': (
                'التقطت شاشتك. إن كان المتصفح مفتوحاً اسأل ماذا أرى. '
                'أو قل ماذا أبحث أو أفتح.'
            ),
        },
        'see_computer_help': {
            'en': 'Open a site or search first, then ask what I see. Or say take a screenshot.',
            'sv': 'Öppna en sida eller sök först, fråga sedan vad jag ser. Eller säg ta en skärmdump.',
            'ar': 'افتح موقعاً أو ابحث أولاً، ثم اسأل ماذا أرى. أو قل خذ لقطة شاشة.',
        },
        'cookie_wall': {
            'en': '{site} is open but I only see a cookie or consent screen. Accept it in the browser, then ask what I see again.',
            'sv': '{site} är öppen men jag ser bara cookie-/samtyckesskärm. Acceptera i webbläsaren och fråga igen.',
            'ar': '{site} مفتوح لكن أرى شاشة cookies فقط. وافق في المتصفح ثم اسأل مرة أخرى.',
        },
        'see_page_empty': {
            'en': '{site} is open but I could not read useful text yet. Try scrolling or ask me to find something on the page.',
            'sv': '{site} är öppen men jag kunde inte läsa användbar text än. Prova scrolla eller be mig hitta något på sidan.',
            'ar': '{site} مفتوح لكن لم أجد نصاً مفيداً بعد. جرّب التمرير أو اطلب مني أن أجد شيئاً على الصفحة.',
        },
        'close_tab_ok': {
            'en': 'Closing the {site} tab bro.',
            'sv': 'Stänger {site}-fliken bro.',
            'ar': 'سأغلق تبويب {site}.',
        },
        'scroll_ok': {
            'en': 'Scrolling {direction} on the page.',
            'sv': 'Scrollar {direction} på sidan.',
            'ar': 'أمرّر {direction} على الصفحة.',
        },
        'find_need_query': {
            'en': 'Tell me what to find on the page — e.g. "show me the login button on the page".',
            'sv': 'Säg vad jag ska hitta på sidan — t.ex. "visa mig inloggningen på sidan".',
            'ar': 'قل ماذا أجد على الصفحة — مثلاً "اعرض لي زر تسجيل الدخول على الصفحة".',
        },
        'find_on_page_ok': {
            'en': 'Found this on the page: {snippet}',
            'sv': 'Hittade detta på sidan: {snippet}',
            'ar': 'وجدت هذا على الصفحة: {snippet}',
        },
        'find_on_page_miss': {
            'en': 'I could not find "{query}" on the current page. Try scrolling or open the right site first.',
            'sv': 'Jag hittade inte "{query}" på sidan. Prova scrolla eller öppna rätt sida först.',
            'ar': 'لم أجد "{query}" على الصفحة. جرّب التمرير أو افتح الموقع الصحيح أولاً.',
        },
        'pending_action_ok': {
            'en': 'On it bro — doing {label} now.',
            'sv': 'Kör bro — {label} nu.',
            'ar': 'حاضر — أنفذ {label} الآن.',
        },
        'need_query': {
            'en': (
                'What should I do on your computer? Tell me what to search, '
                'what site to open, or ask what is on your screen.'
            ),
            'sv': (
                'Vad vill du att jag gör? Säg vad jag ska söka — t.ex. vädret i Stockholm — '
                'eller säg öppna och en webbplats.'
            ),
            'ar': (
                'ماذا تريد أن أفعل؟ قل ماذا أبحث — مثل الطقس في ستوكهولم — '
                'أو قل افتح وموقعاً.'
            ),
        },
        'need_url': {
            'en': 'What link should I open? Say something like: open github.com or paste the full URL.',
            'sv': 'Vilken länk ska jag öppna? Säg t.ex.: öppna github.com eller klistra in hela URL:en.',
            'ar': 'أي رابط أفتح؟ قل مثلاً: افتح github.com أو الصق الرابط كاملاً.',
        },
        'open_fail': {
            'en': 'Could not open browser: {err}',
            'sv': 'Kunde inte öppna webbläsaren: {err}',
            'ar': 'تعذر فتح المتصفح: {err}',
        },
        'unknown': {
            'en': 'I could not run that computer action.',
            'sv': 'Jag kunde inte köra den datoråtgärden.',
            'ar': 'تعذر تنفيذ أمر الكمبيوتر.',
        },
    }
    lang = language if language in ('sv', 'ar') else 'en'
    tpl = templates.get(key, {}).get(lang) or templates.get(key, {}).get('en', '')
    return tpl.format(**kwargs)
