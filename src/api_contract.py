"""Normalize Beru API JSON for beru-ui (PWA, Electron, Capacitor, Netlify)."""

from __future__ import annotations

import re

from src.text_direction import text_direction_for_language


def sanitize_spoken_text(text: str) -> str:
    """Strip URLs so voice/TTS never reads links aloud."""
    if not text:
        return ''
    cleaned = re.sub(r'https?://\S+', '', text)
    cleaned = re.sub(r'\bwww\.\S+', '', cleaned)
    cleaned = re.sub(r'\bURL:\s*', '', cleaned, flags=re.I)
    cleaned = re.sub(r'Opened:\s*', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    return cleaned

# UI voice orb: source === 'search' || source === 'web_search'
SEARCH_SOURCES = frozenset({'search', 'web_search'})


def normalize_source(source: str | None) -> str | None:
    if not source:
        return None
    if source == 'web_search':
        return 'search'
    return source


def ui_chat_payload(
    *,
    response: str,
    language: str = 'en',
    text_direction: str | None = None,
    active_document=None,
    source: str | None = None,
    activity: str | None = None,
    tone: str | None = None,
    user: str | None = None,
    is_owner: bool | None = None,
    session_identified: bool | None = None,
    awaiting_owner_confirm: bool | None = None,
    awaiting_voice_wake: bool | None = None,
    voice_verified: bool | None = None,
    voice_enrolled: bool | None = None,
    opened_url: str | None = None,
    browser_url: str | None = None,
    search_query: str | None = None,
    page_title: str | None = None,
    client_actions: list | None = None,
    browser_open: bool | None = None,
    screenshot_path: str | None = None,
    extra: dict | None = None,
) -> dict:
    """ChatResponse shape expected by beru-ui."""
    lang = (language or 'en').strip() or 'en'
    spoken = sanitize_spoken_text(response or '')
    payload = {
        'response': spoken,
        'tts_text': spoken,
        'language': lang,
        'text_direction': text_direction or text_direction_for_language(lang),
        'active_document': active_document,
    }
    src = normalize_source(source)
    if src:
        payload['source'] = src
        if src in SEARCH_SOURCES and not activity:
            payload['activity'] = 'searching'
    if activity:
        payload['activity'] = activity
    if tone is not None:
        payload['tone'] = tone
    if user is not None:
        payload['user'] = user
    if is_owner is not None:
        payload['is_owner'] = is_owner
    if session_identified is not None:
        payload['session_identified'] = session_identified
    if awaiting_owner_confirm is not None:
        payload['awaiting_owner_confirm'] = awaiting_owner_confirm
    if awaiting_voice_wake is not None:
        payload['awaiting_voice_wake'] = awaiting_voice_wake
    if voice_verified is not None:
        payload['voice_verified'] = voice_verified
    if voice_enrolled is not None:
        payload['voice_enrolled'] = voice_enrolled
    url = browser_url or opened_url
    if url:
        payload['browser_url'] = url
        payload['opened_url'] = url
    if search_query:
        payload['search_query'] = search_query
    if page_title:
        payload['page_title'] = page_title
    if client_actions:
        payload['client_actions'] = client_actions
    if browser_open:
        payload['browser_open'] = True
    if screenshot_path:
        payload['screenshot_path'] = screenshot_path
    if extra:
        for key, value in extra.items():
            if value is not None and key not in payload:
                payload[key] = value
    return payload


def cors_origins():
    """Origins for browser/PWA/Capacitor/Electron UI. Default * — set BERU_CORS_ORIGINS to tighten."""
    import os

    raw = (os.getenv('BERU_CORS_ORIGINS') or '*').strip()
    if raw == '*':
        return ['*']
    return [o.strip() for o in raw.split(',') if o.strip()]
