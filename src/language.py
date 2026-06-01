def resolve_turn_language(text, *, hint=None, session_language=None, in_gate=False):
    """
    Pick UI/gate language for this turn.
    Voice STT often mis-detects short replies (e.g. "Yeah" → en while user speaks Swedish).
    """
    detected = detect_language(text)
    words = len(text.split())

    # Script beats session default (e.g. لا / نعم must stay Arabic, not English).
    if is_arabic_text(text):
        return 'ar'

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
    'ممكن', 'هل يمكن', 'هل اسال', 'هل أسأل', 'ممكن اسال', 'ممكن أسأ',
    'اسالك', 'أسألك', 'اسألك', 'اسالك', 'أستطيع', 'اقدر', 'أقدر',
)

ARABIC_GATE_CHATTER_PHRASES = (
    'ممكن اسال', 'ممكن أسأ', 'ممكن اسالك', 'ممكن أسألك', 'هل اسال', 'هل أسأل',
    'هل يمكن', 'أريد ان اسال', 'أريد أن أسأل', 'عندي سؤال', 'سؤال',
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
    raw = text.strip()
    tl = raw.lower()
    if '؟' in text or '?' in tl:
        return True
    if any(p in raw for p in ARABIC_GATE_CHATTER_PHRASES):
        return True
    return any(p in tl or p in raw for p in ARABIC_QUESTION_PHRASES)


def is_arabic_gate_chatter(text):
    """Greeting / question / request during identity gate — not a name."""
    if not is_arabic_text(text):
        return False
    if is_arabic_negation(text) or is_arabic_name_intro_statement(text):
        return False
    if is_arabic_greeting(text) or is_arabic_question(text) or is_arabic_name_meta_question(text):
        return True
    raw = text.strip()
    return any(p in raw for p in ARABIC_GATE_CHATTER_PHRASES)


ARABIC_NAME_META_PHRASES = (
    'ما ذا تقصد', 'ماذا تقصد', 'ما تقصد', 'ما جاوبت', 'لم تجب', 'لم ترد',
    'لم تجيب', 'ما المقصود', 'ماذا تعني',
)


def is_arabic_name_meta_question(text):
    """User asking what we mean by full name, or that we did not answer."""
    if not is_arabic_text(text):
        return False
    tl = text.lower().strip()
    return any(p in tl for p in ARABIC_NAME_META_PHRASES)


ARABIC_NAME_STOPWORDS = frozenset({
    'اسمي', 'إسمي', 'انا', 'أنا', 'بالكامل', 'الكامل', 'اسم', 'الاسم', 'هو', 'هي',
    'نعم', 'لا', 'مرحبا', 'مرحباً', 'أهلا', 'أهلاً',
    'لست', 'لستُ', 'ليس', 'ليست', 'مش', 'مو', 'كلا',
    'ممكن', 'هل', 'اسال', 'أسأل', 'اسالك', 'أسألك', 'اسألك', 'أستطيع', 'اقدر', 'أقدر',
    'يوم', 'اليوم', 'بعد', 'قبل', 'عندي', 'سؤال', 'سوال',
})

ARABIC_NEGATION_PHRASES = (
    'لست عمر', 'لستُ عمر', 'ليس عمر', 'ليست عمر', 'انا لست عمر', 'أنا لست عمر',
    'انا ليس عمر', 'أنا ليس عمر', 'مش عمر', 'مو عمر', 'لا لست عمر', 'لستَ عمر',
    'لستِ عمر', 'not omar', 'inte omar',
)


def _arabic_word_tokens(text):
    import re

    return [
        w.strip('.,،!?;:')
        for w in re.findall(r'[\u0600-\u06FF]+', text or '')
        if len(w.strip('.,،!?;:')) >= 2 and w.strip('.,،!?;:') not in ARABIC_NAME_STOPWORDS
    ]


def _latin_name_tokens(text):
    import re

    return [w.capitalize() for w in re.findall(r'[A-Za-z][A-Za-z\'\-]*', text or '') if len(w) > 1]


def is_arabic_negation(text):
    """e.g. لست عمر — I am not Omar (not a name)."""
    import re

    if not text or not is_arabic_text(text):
        return False
    raw = text.strip()
    if any(p in raw for p in ARABIC_NEGATION_PHRASES):
        return True
    if re.search(r'(?:لست|لستُ|ليس|ليست|مش|مو)\s+عمر', raw):
        return True
    return False


def is_arabic_name_intro_statement(text):
    """User states their name (اسمي خالد / أنا خالد), not asking what it is."""
    import re

    if not text or not is_arabic_text(text):
        return False
    if is_arabic_question(text) or is_arabic_negation(text):
        return False
    raw = text.strip()
    if re.search(r'(?:اسمي|إسمي)\s+\S', raw):
        return True
    if re.search(r'(?:أنا|انا)\s+\S', raw):
        return True
    return False


def is_name_intro_statement(text):
    """User introduces themselves (AR or EN), not asking for their name."""
    import re

    if not text or not text.strip():
        return False
    if is_arabic_name_intro_statement(text):
        return True
    if is_arabic_negation(text):
        return False
    tl = text.lower().strip()
    patterns = (
        r'^my name is\s+\S',
        r"^i'?m\s+\S",
        r'^i am\s+\S',
        r'^call me\s+\S',
        r'^this is\s+\S',
        r'^jag heter\s+\S',
        r'^mitt namn är\s+\S',
    )
    if any(re.search(p, tl) for p in patterns):
        return True
  # mid-sentence: "well my name is Khaled"
    return bool(re.search(r'\bmy name is\s+\S', tl))


def detect_arabic_full_name(text):
    """
    Two-or-more-part name from Arabic (or Arabic+English) input.
    Examples: خالد درويش, اسمي خالد عيسي درويش, اسمي بالكامل Khaled Darwish
    """
    import re

    if not text or not text.strip():
        return None

    raw = text.strip()
    has_arabic = is_arabic_text(raw)

    if is_arabic_negation(raw):
        return None

    if has_arabic and (is_arabic_greeting(raw) or is_arabic_question(raw) or is_arabic_name_meta_question(raw)):
        return None

    intro_patterns = (
        r'(?:اسمي|إسمي)\s*(?:بالكامل|الكامل)?\s*[:\-]?\s*(.+)$',
        r'(?:أنا|انا)\s+(?:اسمي\s+)?(.+)$',
    )
    if has_arabic:
        for pat in intro_patterns:
            m = re.search(pat, raw, re.I)
            if m:
                rest = m.group(1).strip().strip('.,،!?')
                latin = _latin_name_tokens(rest)
                if len(latin) >= 2:
                    return ' '.join(latin)
                tokens = _arabic_word_tokens(rest)
                if len(tokens) >= 2:
                    return ' '.join(tokens)

        tokens = _arabic_word_tokens(raw)
        if len(tokens) >= 2:
            return ' '.join(tokens)

    # Mixed Arabic intro + Latin name on same line
    if has_arabic:
        latin = _latin_name_tokens(raw)
        if len(latin) >= 2:
            return ' '.join(latin)

    return None


def detect_arabic_name(text):
    """First name from Arabic intro, e.g. اسمي خالد (single given name only)."""
    import re

    if not is_arabic_text(text):
        return None

    if is_arabic_negation(text):
        return None

    full = detect_arabic_full_name(text)
    if full:
        parts = full.split()
        if len(parts) >= 2:
            return None
        if parts[0].lower() in ('عمر', 'omar'):
            return 'Omar'
        return parts[0]

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
            tokens = _arabic_word_tokens(name)
            if len(tokens) == 1:
                return tokens[0]
            if len(tokens) >= 2:
                return None
            if len(name) >= 2 and ' ' not in name:
                return name
    if re.search(r'\bعمر\b', text) and not is_arabic_negation(text):
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
