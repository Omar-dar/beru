"""Playwright page scraping — real visible text only, no LLM guessing."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from src.project_env import load_project_dotenv

load_project_dotenv()

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
)

_SKIP_LINE_FRAGMENTS = (
    'cookie', 'sign in', 'sign up', 'privacy policy', 'accept all',
    'google apps', 'before you continue', 'captcha', 'unusual traffic',
)


@dataclass
class ScrapeResult:
    ok: bool
    url: str
    title: str = ''
    text: str = ''
    error: str = ''


def playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def scrape_url(url: str, *, timeout_ms: int | None = None) -> ScrapeResult:
    """Load URL in headless Chromium and return body text."""
    if not url:
        return ScrapeResult(False, url, error='empty url')
    if not playwright_available():
        return ScrapeResult(
            False,
            url,
            error='Playwright not installed. Run: pip install playwright && playwright install chromium',
        )

    from playwright.sync_api import sync_playwright

    wait_ms = timeout_ms or int(os.getenv('BERU_SCRAPE_TIMEOUT_MS', '12000'))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, wait_until='domcontentloaded', timeout=wait_ms)
                page.wait_for_timeout(1500)
                title = page.title() or ''
                text = page.inner_text('body') or ''
                return ScrapeResult(True, url, title=title.strip(), text=_normalize_text(text))
            finally:
                browser.close()
    except Exception as exc:
        print(f'[Playwright scrape error: {exc}]')
        return ScrapeResult(False, url, error=str(exc))


def _normalize_text(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_facts_from_page(text: str, query: str = '', *, max_len: int = 500) -> str:
    """Pick readable lines from scraped page text — no invented content."""
    if not text or len(text.strip()) < 30:
        return ''

    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 18]
    filtered = []
    for ln in lines:
        low = ln.lower()
        if any(skip in low for skip in _SKIP_LINE_FRAGMENTS):
            continue
        if low in ('images', 'videos', 'news', 'maps', 'more', 'tools'):
            continue
        filtered.append(ln)

    if not filtered:
        collapsed = ' '.join(text.split())
        return collapsed[:max_len].strip()

    query_words = [w for w in re.findall(r'\w+', (query or '').lower()) if len(w) > 3]
    if query_words:
        scored = []
        for ln in filtered:
            low = ln.lower()
            score = sum(1 for w in query_words if w in low)
            scored.append((score, ln))
        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        picked = [ln for score, ln in scored[:6] if score > 0] or [ln for _, ln in scored[:6]]
    else:
        picked = filtered[:6]

    excerpt = ' '.join(picked)
    if len(excerpt) > max_len:
        excerpt = excerpt[: max_len - 3].rsplit(' ', 1)[0] + '...'
    return excerpt.strip()
