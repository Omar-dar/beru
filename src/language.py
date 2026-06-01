def resolve_turn_language(text, *, hint=None, session_language=None, in_gate=False):
    """
    Pick UI/gate language for this turn.
    Voice STT often mis-detects short replies (e.g. "Yeah" → en while user speaks Swedish).
    """
    detected = detect_language(text)
    words = len(text.split())

    # Very short replies (yes, password, STT noise): trust UI / session hint.
    if words <= 2:
        if hint in ('en', 'sv', 'ar'):
            return hint
        if session_language in ('en', 'sv', 'ar'):
            return session_language

    if in_gate and hint in ('en', 'sv', 'ar'):
        return hint

    # Normal questions: follow what the user actually wrote.
    if hint in ('en', 'sv', 'ar') and detected != hint and words >= 3:
        return detected

    if hint in ('en', 'sv', 'ar'):
        return hint
    if session_language in ('en', 'sv', 'ar') and words <= 3:
        return session_language
    return detected


ARABIC_CHARS = set(
    'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'
    'أإآئؤةىﻻﻹﻻﻷﻵ'
)

ARABIC_GREETING_WORDS = {
    'مرحبا', 'مرحباً', 'أهلا', 'أهلاً', 'السلام', 'سلام', 'صباح', 'مساء',
    'هلا', 'هاي', 'كيف', 'حالك', 'حالكم', 'اليوم', 'تيلد', 'تild', 'تيلد',
}

ARABIC_QUESTION_PHRASES = (
    'كيف حالك', 'كيف حالكم', 'كيف انت', 'كيف أنت', 'ما اسمك', 'من انت',
    'من أنت', 'هل انت', 'هل أنت', 'ماذا', 'لماذا', 'أين', 'متى',
)


def is_arabic_text(text):
    if not text:
        return False
    return any(c in ARABIC_CHARS for c in text)


def is_arabic_greeting(text):
    if not is_arabic_text(text):
        return False
    tl = text.lower()
    if any(w in tl for w in ARABIC_GREETING_WORDS):
        return True
  # "مرحبا تيلد" style openers
    words = set(tl.replace('،', ' ').replace(',', ' ').split())
    return bool(words.intersection(ARABIC_GREETING_WORDS))


def is_arabic_question(text):
    if not is_arabic_text(text):
        return False
    tl = text.lower().strip()
    if '؟' in text or '?' in tl:
        return True
    return any(p in tl for p in ARABIC_QUESTION_PHRASES)


def detect_arabic_name(text):
    """Extract name from Arabic intro phrases, e.g. أنا عمر."""
    import re
    if not is_arabic_text(text):
        return None
    patterns = (
        r'اسمي\s+(.+?)(?:[.،!?]|$)',
        r'أنا\s+(\S+)',
        r'انا\s+(\S+)',
    )
    for pat in patterns:
        m = re.search(pat, text.strip(), re.I)
        if m:
            name = m.group(1).strip().strip('.,،!?')
            if name.lower() in ('عمر', 'omar'):
                return 'Omar'
            if len(name) >= 2:
                return name.split()[0].capitalize()
    if re.search(r'\bعمر\b', text):
        return 'Omar'
    return None


def detect_language(text):
    swedish_chars = set('åäöÅÄÖ')
    arabic_chars = ARABIC_CHARS
    swedish_words = {
        'vad', 'heter', 'jag', 'hur', 'vem', 'är', 'det',
        'och', 'att', 'kan', 'du', 'inte', 'med', 'för',
        'på', 'om', 'men', 'har', 'en', 'ett', 'var',
        'när', 'vill', 'ska', 'vi', 'de', 'sig', 'som',
        'skapade', 'byggde', 'berätta', 'kom', 'ihåg', 'menar',
    }
    if any(c in swedish_chars for c in text):
        return 'sv'
    if any(c in arabic_chars for c in text):
        return 'ar'
    words = set(text.lower().split())
    if len(words.intersection(swedish_words)) >= 2:
        return 'sv'
    return 'en'
