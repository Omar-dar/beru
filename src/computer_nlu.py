"""Natural-language understanding for owner computer agent — any wording."""

from __future__ import annotations

import json
import re
from typing import Optional

# Chit-chat — not computer tasks unless they also mention web/browser/search.
_CHITCHAT = (
    'how are you', 'how do you feel', 'what do you want to do today',
    'what are you doing', 'how are you doing', 'nice to meet', 'good morning',
    'thank you', 'thanks bro', 'lol', 'haha',
    'just chatting', 'only chatting', 'just talking to you', "that's all", 'thats all',
    'nothing else', 'just hanging out', 'only here to chat',
    'goodbye', 'good bye', 'bye bye', 'see you', 'talk later', 'good night',
)

_NOT_COMPUTER = (
    'your name', "what's your name", 'what is your name', 'whats your name',
    'who are you', 'what are you called', 'my name is', 'call you',
    'wake up', 'goodbye', 'good bye', 'bye bye', 'see you later',
    'thank you', 'thanks', 'hello', 'hey there', 'how are you',
    'what do you want', 'what would you like', 'what are you doing',
    'what are you up to', 'why did you', 'why do you', 'why are you',
    'what is this', 'what was that', 'did you open', 'you opened', 'you open',
    'stop opening', 'close the browser', "don't open", 'dont open',
    'just talk', 'talk to me', 'can we talk', 'are you there',
    'vad vill du', 'vad gör du', 'varför öppnade', 'varför öppnar',
)

# User talking TO Beru — never treat as a Google search.
_TALKING_TO_BERU = (
    'what do you want', 'what would you like', 'what you want to do',
    'what are you doing', 'what are you up to', 'whatcha doing',
    'why did you', 'why do you', 'why are you', 'what is this', 'what was that',
    'did you open', 'you opened', 'you open', 'open the browser',
    'stop opening', 'close the browser', "don't open", 'dont open',
    'just talk', 'talk to me', 'can we talk', 'are you listening',
    'vad vill du', 'vad gör du', 'varför öppnade', 'varför öppnar',
)


def is_talking_to_beru(text: str) -> bool:
    if not text:
        return False
    tl = text.lower().strip()
    if any(x in tl for x in _TALKING_TO_BERU):
        return True
    if '?' in text and re.search(r'\b(you|your|du|dig|ditt)\b', tl):
        if not any(s in tl for s in _WEB_SIGNALS):
            return True
        if any(x in tl for x in ('why did you', 'why do you', 'why are you', 'did you open')):
            return True
    return False


def _browser_is_complaint(tl: str) -> bool:
    return any(
        x in tl
        for x in (
            'why did you', 'why do you', 'why are you', 'did you open',
            'you opened', 'you open', 'stop opening', "don't open", 'dont open',
            'varför öppnade', 'varför öppnar',
        )
    )

_WEB_SIGNALS = (
    'weather', 'temperature', 'forecast', 'väder', 'hot', 'cold', 'rain', 'raining',
    'snow', 'warm', 'cool', 'degrees', 'google', 'browser', 'browsing',
    'website', 'internet', 'online', 'web', 'search', 'look up', 'lookup', 'find out',
    'check the', 'check what', 'open ', 'go to', 'visit ', 'navigate', 'link',
    'news', 'headlines', 'score', 'price', 'stock', 'flight', 'restaurant',
    'youtube', 'reddit', 'twitter', 'facebook', 'github', 'http', 'www.', '.com',
    'screen', 'page', 'tab', 'read it', 'read that', 'tell me what', 'show me what',
)

_POLITE_PREFIXES = re.compile(
    r'^(?:'
    r'(?:hi|hey|hello|good|ok|okay|so|well|yeah|yes|no)[,!.]?\s+'
    r')*'
    r'(?:'
    r'(?:can|could|would|will)\s+you\s+'
    r'|(?:please\s+)?'
    r'|(?:beru|buro|beirut|bro)\s*[,]?\s*'
    r')*',
    re.I,
)

_COMMAND_NOISE = re.compile(
    r'(?:'
    r'open\s+(?:the\s+)?browser(?:\s+and)?\s*'
    r'|search\s+on\s+(?:the\s+)?(?:browser|google)\s*'
    r'|(?:can|could)\s+you\s+'
    r'|please\s+'
    r'|tell\s+me\s+'
    r'|i\s+(?:want|need)\s+(?:you\s+to\s+)?(?:know|find|see|check)\s+'
    r'|what\s+(?:is|are|was|s)\s+'
    r'|how\s+(?:is|are|s)\s+'
    r')',
    re.I,
)


def _after_wake_command(text: str) -> str:
    """If user said 'Beru …' plus a real request, return the request part."""
    from src.wake import sounds_like_wake, strip_wake_prefix

    if not sounds_like_wake(text):
        return text
    remainder = strip_wake_prefix(text)
    if remainder and len(remainder.split()) >= 2:
        return remainder
    return text


def is_natural_computer_request(text: str, *, has_browser_session: bool = False) -> bool:
    """True when owner likely wants browser/screen action — loose wording OK."""
    if not text or len(text.strip()) < 3:
        return False

    from src.wake import sounds_like_wake, strip_wake_prefix

    if sounds_like_wake(text):
        remainder = strip_wake_prefix(text)
        if not remainder or len(remainder.split()) < 2:
            return False
        text = remainder

    tl = text.lower().strip()

    if is_talking_to_beru(text):
        return False

    if any(x in tl for x in _NOT_COMPUTER):
        return False

    if any(s in tl for s in ('browser', 'browsing', 'google')) and _browser_is_complaint(tl):
        return False

    if any(c == tl or tl.startswith(c + ' ') for c in _CHITCHAT):
        if not any(s in tl for s in _WEB_SIGNALS):
            return False

    if any(s in tl for s in _WEB_SIGNALS):
        return True

    if re.search(r'https?://|www\.\w+|\b\w+\.(com|org|net|io|se)\b', tl):
        return True

    if has_browser_session and re.search(
        r'\b(read|see|show|tell|explain|summarize|repeat)\b', tl
    ):
        if is_talking_to_beru(text):
            return False
        if any(x in tl for x in ('your name', 'who are you', 'goodbye', 'good bye', 'bye')):
            return False
        if not any(s in tl for s in _WEB_SIGNALS):
            return False
        return True

    if has_browser_session and re.search(r'\bwhat\b', tl):
        if is_talking_to_beru(text):
            return False
        if any(x in tl for x in ('your name', 'who are you', 'about you', 'beru', 'my name')):
            return False
        if any(s in tl for s in _WEB_SIGNALS):
            return True
        return False

    if '?' in text and any(
        w in tl
        for w in (
            'what', 'how', 'who', 'when', 'where', 'which', 'price', 'cost',
            'latest', 'current', 'today', 'now', 'happening',
        )
    ):
        if is_talking_to_beru(text):
            return False
        if not any(s in tl for s in _WEB_SIGNALS):
            return False
        if any(x in tl for x in (
            'your name', 'who are you', 'about you', 'beru',
            'chat', 'talking to you', 'with you', 'help with anything', 'unwind',
        )):
            return False
        return True

    return False


def extract_search_topic(text: str) -> str:
    """Best-effort search query from free-form speech."""
    from src.computer_control import _extract_search_query, _is_weather_query, _refine_weather_query
    from src.search import BeruSearch
    from src.wake import sounds_like_wake, strip_wake_prefix

    if sounds_like_wake(text):
        remainder = strip_wake_prefix(text)
        if not remainder or len(remainder.split()) < 2:
            return ''
        text = remainder

    tl = (text or '').lower()
    if is_talking_to_beru(text):
        return ''
    if any(x in tl for x in _NOT_COMPUTER):
        return ''
    if any(c == tl.strip().strip('.!,') or tl.startswith(c) for c in _CHITCHAT):
        return ''

    strict = _extract_search_query(text)
    if strict:
        return strict

    t = _POLITE_PREFIXES.sub('', text).strip()
    t = _COMMAND_NOISE.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' ?.,!')

    if _is_weather_query(t) or _is_weather_query(text):
        city = BeruSearch._extract_city_from_weather_query(t or text, text)
        return f'weather in {city} today'

    # Drop trailing filler
    t = re.sub(
        r'\s+(?:for me|please|thanks|thank you|bro|man)\s*$', '', t, flags=re.I
    ).strip()

    if len(t) >= 3 and is_natural_computer_request(text):
        return _refine_weather_query(text, t)
    return ''


def infer_with_brain(text: str, brain) -> Optional[dict]:
    """Ollama JSON plan when heuristics are unsure. Returns action, query, url."""
    if not brain:
        return None
    prompt = f"""Classify this owner command for a computer agent.
User: "{text}"

Reply ONLY with JSON on one line:
{{"action":"search|open_url|see_computer|screenshot|chat","query":"short google search or empty","url":"full url or empty"}}

Rules:
- search: anything needing web info (weather, news, prices, people, how-to, etc.)
- open_url: open a specific site/link
- see_computer: what is on screen / browser / read the page
- screenshot: capture screen
- chat: NOT a computer task (greetings, feelings, coding help only)

query: 2-8 words for Google, no polite filler. Example: "weather Stockholm today"
"""
    try:
        import requests

        response = requests.post(
            brain.generate_url,
            json={
                'model': brain.model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.1, 'num_predict': 120},
            },
            timeout=int(__import__('os').getenv('BERU_NLU_TIMEOUT', '25')),
        )
        raw = response.json().get('response', '').strip()
        start = raw.find('{')
        end = raw.rfind('}')
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start : end + 1])
        action = (data.get('action') or 'chat').strip().lower()
        if action == 'chat':
            return None
        return {
            'action': action,
            'query': (data.get('query') or '').strip(),
            'url': (data.get('url') or '').strip(),
        }
    except Exception as exc:
        print(f'[Computer NLU brain error: {exc}]')
        return None


def resolve_plan(text: str, *, brain=None, has_browser_session: bool = False) -> Optional[dict]:
    """
    Map free-form text → {intent, query, url}.
    intent matches computer_control parse ids: browser_search, open_url, see_computer, screenshot, takeover_help
    """
    from src.computer_control import parse_computer_intent, _extract_url, _open_url_target

    intent = parse_computer_intent(text)
    if intent:
        if intent == 'browser_search':
            q = extract_search_topic(text)
            return {'intent': intent, 'query': q, 'url': ''}
        if intent == 'open_url':
            return {'intent': intent, 'query': '', 'url': _open_url_target(text) or _extract_url(text)}
        return {'intent': intent, 'query': '', 'url': ''}

    if not is_natural_computer_request(text, has_browser_session=has_browser_session):
        return None

    q = extract_search_topic(text)
    if q:
        return {'intent': 'browser_search', 'query': q, 'url': ''}
    url = _extract_url(text)
    if url:
        return {'intent': 'open_url', 'query': '', 'url': url}

    import os

    from src.performance import computer_brain_nlu_enabled

    use_brain = brain and computer_brain_nlu_enabled()
    plan = infer_with_brain(text, brain) if use_brain else None
    if plan:
        action = plan['action']
        if action == 'search':
            q = plan['query'] or extract_search_topic(text)
            return {'intent': 'browser_search', 'query': q, 'url': ''}
        if action == 'open_url':
            url = plan['url'] or _extract_url(text)
            return {'intent': 'open_url', 'query': '', 'url': url}
        if action in ('see_computer', 'screenshot'):
            return {'intent': action, 'query': '', 'url': ''}

    return None
