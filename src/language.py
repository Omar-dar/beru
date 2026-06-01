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


def detect_language(text):
    swedish_chars = set('åäöÅÄÖ')
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
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
