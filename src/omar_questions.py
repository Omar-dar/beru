"""Detect questions about Omar Darwish (not Umrah / عمرة)."""

import re


def is_umrah_or_hajj_topic(text):
    """Religious topics that contain عمر but are not about Omar the person."""
    if not text:
        return False
    return bool(
        re.search(
            r'العمرة|عمرة|مناسك\s+العمر|مناسك\s+الحج|الحج\b|حج\b|pilgrimage|umrah|hajj',
            text,
            re.I,
        )
    )


def is_asking_about_omar_person(text):
    """
    Guest or owner asking who Omar is — Arabic or English.
    Excludes مناسك العمرة (Umrah) and معلومات عن الحج.
    """
    if not text or not text.strip():
        return False

    if is_umrah_or_hajj_topic(text) and not re.search(
        r'دارويش|darwish|omar\s*darwish', text, re.I
    ):
        return False

    tl = text.lower()
    if 'omar' in tl or 'darwish' in tl:
        hints = (
            'who is', 'what is', 'tell me about', 'know about', 'about omar',
            'who was', 'you asked', 'asked if', 'is he', 'leader',
            'vem är', 'vad är', 'berätta om', 'den här omar',
            'omar darwish', 'about omar', 'who is omar',
        )
        if any(h in tl for h in hints):
            return True
        if re.search(r'\bomar\b', tl) and any(
            w in tl for w in ('who', 'what', 'know', 'about', 'leader', 'قائد')
        ):
            return True

    if re.search(r'عمر\s*دارويش|دارويش', text):
        return True

    if re.search(
        r'(من\s+(هو|هي)|عن|معلومات\s+عن|تعرف|تعلم|وين\s+المشكله).{0,40}عمر\b',
        text,
    ):
        return True
    if re.search(r'من\s+هو\s+عمر|القائد\s+عمر|من\s+هي\s+عمر', text):
        return True

    return False


def is_omar_info_wrong_feedback(text):
    """User says Beru's facts about Omar are wrong (not a fact correction)."""
    if not text:
        return False
    raw = text.strip()
    patterns = (
        'معلوماتك عن عمر خطأ',
        'كل معلوماتك عن عمر',
        'معلومات عن عمر خطأ',
        'معلوماتك عن عمر غلط',
        'كل ما قلته عن عمر',
    )
    return any(p in raw for p in patterns)
