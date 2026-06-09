"""Turn spoken site names into real URLs (google → google.com)."""

from __future__ import annotations

import re

# Spoken / Swedish UI labels → canonical HTTPS URLs
SITE_ALIASES: dict[str, str] = {
    'google': 'https://www.google.com',
    'facebook': 'https://www.facebook.com',
    'youtube': 'https://www.youtube.com',
    'github': 'https://github.com',
    'twitter': 'https://twitter.com',
    'x': 'https://x.com',
    'reddit': 'https://www.reddit.com',
    'instagram': 'https://www.instagram.com',
    'linkedin': 'https://www.linkedin.com',
    'smhi': 'https://www.smhi.se',
    'väder': 'https://www.smhi.se',
    'weather': 'https://www.smhi.se',
    'väderhemsida': 'https://www.smhi.se',
    'facebook hemsida': 'https://www.facebook.com',
    'google hemsida': 'https://www.google.com',
}

_NOISE_SUFFIXES = (
    ' hemsida', ' webbsida', ' website', ' homepage', ' web site',
    ' sida', ' page', ' site', ' websida',
)


def _strip_site_noise(text: str) -> str:
    s = (text or '').strip().strip('.!,')
    lowered = s.lower()
    for suffix in _NOISE_SUFFIXES:
        if lowered.endswith(suffix):
            s = s[: -len(suffix)].strip()
            lowered = s.lower()
    return s


def normalize_open_url(raw: str) -> str:
    """
    Convert 'Google', 'Facebook hemsida', 'github.com' → full https URL.
    """
    if not raw or not str(raw).strip():
        return ''

    s = _strip_site_noise(str(raw).strip())
    key = s.lower().strip()

    if key in SITE_ALIASES:
        return SITE_ALIASES[key]

    # Already a URL or domain with TLD
    if re.search(r'https?://', s, re.I):
        return s.rstrip('.,)')
    if re.search(r'\b[a-z0-9][-a-z0-9]*\.[a-z]{2,}(?:/[^\s]*)?', s, re.I):
        url = s if s.lower().startswith('http') else f'https://{s.lstrip("/")}'
        return url.rstrip('.,)')

    # Single token brand name → www.name.com
    token = re.sub(r'[^\w-]', '', key)
    if token in SITE_ALIASES:
        return SITE_ALIASES[token]
    if token and re.match(r'^[a-z0-9-]+$', token, re.I) and len(token) >= 2:
        return f'https://www.{token}.com'

    return f'https://{s.lstrip("/")}'
