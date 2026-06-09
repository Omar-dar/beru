"""Wake phrase detection and varied owner greetings."""

from __future__ import annotations

import random
import re
from datetime import date

# Whisper often mishears "Beru" — treat these as wake words when calling the assistant.
_BERU_STT_ALIASES = (
    'beru', 'buro', 'beirut', 'bero', 'buru', 'baru',
    'barrow', 'barrel', 'beryl', 'burrow', 'burro', 'berry', 'berri', 'barron', 'perot', 'berot',
    'peru', 'bearu', 'bare u', 'bay ru', 'be ru', 'hey ru',
    'bellow', 'below', 'barlow', 'boro', 'burro',
)

# STT said this instead of Beru — prompt, do not treat as random chat.
_WAKE_NEAR_MISS = frozenset({
    'bellow', 'below', 'barlow', 'boro', 'pillow', 'hello', 'yellow', 'mellow',
    'burro', 'hero', 'zero', 'arrow', 'narrow',
})

_WAKE_UP_RE = re.compile(r'\bwake\s+up\b', re.I)

_WAKE_PATTERNS = (
    re.compile(r'\b(?:hey|hi|hello|ok|okay|yo)\s*,?\s*(?:wake\s+up\s+)?beru\b', re.I),
    re.compile(r'\bwake\s+up\s+beru\b', re.I),
    re.compile(r'\bberu\b', re.I),
    re.compile(r'\b(?:buro|beirut)\b', re.I),
    re.compile(
        r'\b(?:hey|hi|hello|ok|okay|yo)\s*,?\s*(?:wake\s+up\s+)?'
        r'(?:barrow|barrel|beryl|burrow|burro|berry|bero|buro|barron|bellow|below|barlow)\b',
        re.I,
    ),
    re.compile(
        r'\b(?:barrow|barrel|beryl|burrow|burro|berry|bero|buro|bellow|below|barlow)\b',
        re.I,
    ),
)

_WAKE_STRIP = re.compile(
    r'^(?:'
    r'(?:hey|hi|hello|ok|okay|yo|good\s+morning|good\s+evening)\s*,?\s*'
    r')*'
    r'(?:wake\s+up\s+)?'
    r'(?:beru|buro|beirut|barrow|barrel|beryl|burrow|burro|berry|bero|buru|baru|barron)\s*[,!.]?\s*',
    re.I,
)


def sounds_like_wake(text: str) -> bool:
    """True when STT likely meant "Beru" even if spelled wrong."""
    if not text or len(text.strip()) < 2:
        return False
    tl = text.lower().strip().strip('.!,')
    if _WAKE_UP_RE.search(tl) and len(tl.split()) <= 4:
        return True
    if any(alias in tl for alias in _BERU_STT_ALIASES):
        return True
    return any(p.search(tl) for p in _WAKE_PATTERNS)


def is_wake_phrase(text: str) -> bool:
    return sounds_like_wake(text)


def strip_wake_prefix(text: str) -> str:
    """Remove leading wake words; return remainder or empty if wake-only."""
    t = (text or '').strip()
    if not t:
        return ''
    remainder = _WAKE_STRIP.sub('', t).strip(' .,!?')
    if remainder.lower() == t.lower() and sounds_like_wake(t):
        return ''
    if sounds_like_wake(t) and len(remainder.split()) <= 1:
        return ''
    return remainder or ''


def is_wake_only(text: str) -> bool:
    if not sounds_like_wake(text):
        return False
    remainder = strip_wake_prefix(text)
    return len(remainder.split()) < 2


_GREETINGS = {
    'en': [
        "Yes sir, I'm here. What are you getting up to today?",
        "Hey Omar, good to hear you. What's the plan for today, sir?",
        "I'm awake, sir. What will you be doing today?",
        "Right here, Omar. How's your day looking?",
        "Good to have you back, sir. What's on your agenda today?",
        "Hey bro, I'm listening. What are you up to today?",
        "Yes sir, Beru is ready. What would you like to tackle today?",
        "Morning energy or chill mode today, sir? What's the move?",
        "I'm here for you, Omar. What are we doing today?",
        "Locked in, sir. Tell me what today's looking like for you.",
    ],
    'sv': [
        'Ja sir, jag är här. Vad ska du göra idag?',
        'Hej Omar, bra att höra dig. Vad är planen idag?',
        'Jag är vaken. Vad har du för dig idag?',
        'Här är jag, sir. Hur ser dagen ut?',
        'Bra att du är tillbaka. Vad står på schemat idag?',
        'Hej bro, jag lyssnar. Vad ska du hitta på idag?',
        'Ja sir, Beru är redo. Vad ska vi ta oss an idag?',
        'Jag är här för dig, Omar. Vad gör vi idag?',
    ],
    'ar': [
        'نعم سيدي، أنا هنا. ماذا ستفعل اليوم؟',
        'أهلاً عمر، سعيد بسماعك. ما خطة اليوم؟',
        'أنا مستيقظ. ماذا ستعمل اليوم يا سيدي؟',
        'حاضر يا عمر. كيف يبدو يومك؟',
        'سعيد بعودتك. ما جدولك اليوم؟',
        'أنا هنا يا صديقي. ماذا سنفعل اليوم؟',
    ],
}


def is_near_wake_miss(text: str) -> bool:
    """Single-word STT that sounds like Beru but did not match wake."""
    if not text or sounds_like_wake(text):
        return False
    tl = text.lower().strip().strip('.!,')
    if tl in _WAKE_NEAR_MISS:
        return True
    if len(tl.split()) <= 2 and any(n in tl for n in _WAKE_NEAR_MISS):
        return True
    return False


def wake_miss_prompt(language: str = 'en') -> str:
    if language == 'sv':
        return 'Nästan! Säg "Beru" eller "Vakna Beru" så vet jag att det är du.'
    if language == 'ar':
        return 'قريب! قل "Beru" أو "استيقظ Beru" لأعرف أنك أنت.'
    return 'Almost bro! Say "Beru" or "Wake up Beru" so I know it is you.'


def wake_greeting(language: str = 'en', *, memory=None) -> str:
    """Varied wake response — not the same line every time."""
    lang = language if language in _GREETINGS else 'en'
    pool = list(_GREETINGS[lang])
    random.shuffle(pool)

    if memory and getattr(memory, 'session', None):
        if memory.session.get('today_story_logged'):
            pool = [g for g in pool if 'today' in g.lower() or 'idag' in g.lower() or 'اليوم' in g]
            if not pool:
                pool = list(_GREETINGS[lang])

    weekday = date.today().weekday()
    if weekday >= 5 and lang == 'en':
        pool.insert(0, "Weekend mode, sir. What's the plan for today?")
    elif weekday >= 5 and lang == 'sv':
        pool.insert(0, 'Helgläge, sir. Vad ska du göra idag?')

    return random.choice(pool[: max(4, len(pool))])
