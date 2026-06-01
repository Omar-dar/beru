"""Match and describe Omar facts across languages (storage can be EN/SV/AR)."""

import re

from src.omar_facts import fact_event_date, fact_text, format_event_date

# Topic flags for cross-language matching
_SUBMIT = 1
_UNI = 2
_PROJ = 4
_THESIS = 8

_SUBMIT_WORDS = (
    'submitted', 'handed', 'turned in', 'delivered', 'lämnade', 'lamnade',
    'inlämnade', 'inlamnade', 'سلمت', 'قدمت', 'تسليم',
)
_UNI_WORDS = (
    'university', 'universitet', 'college', 'school', 'جامعة', 'universitet',
)
_PROJ_WORDS = (
    'project', 'projekt', 'مشروع', 'assignment',
)
_THESIS_WORDS = (
    'uppsats', 'thesis', 'c-uppsats', 'dissertation', 'رسالة', 'تخرج',
)


def fact_topic_flags(text):
    if not text:
        return 0
    tl = text.lower()
    flags = 0
    if any(w in tl for w in _SUBMIT_WORDS):
        flags |= _SUBMIT
    if any(w in tl for w in _UNI_WORDS):
        flags |= _UNI
    if any(w in tl for w in _PROJ_WORDS):
        flags |= _PROJ
    if any(w in tl for w in _THESIS_WORDS):
        flags |= _THESIS
    return flags


def _popcount(n):
    return bin(n).count('1')


def facts_matching_when_query(entries, query):
    """Rank facts for a when-question; Arabic queries can match English facts."""
    if not query or not entries:
        return []
    q_flags = fact_topic_flags(query)
    ql = query.lower()
    query_words = set(re.findall(r'\w+', ql, flags=re.UNICODE))
    scored = []

    for entry in entries or []:
        text = fact_text(entry)
        if not text:
            continue
        tl = text.lower()
        f_flags = fact_topic_flags(text)
        score = 0

        if q_flags and f_flags:
            overlap = _popcount(q_flags & f_flags)
            score += overlap * 6
            if (q_flags & _SUBMIT) and not (f_flags & _SUBMIT):
                score -= 8
        else:
            fact_words = set(re.findall(r'\w+', tl, flags=re.UNICODE))
            score += len(query_words.intersection(fact_words))

        if fact_event_date(entry):
            score += 12
        if len(text) > 110 and not fact_event_date(entry):
            score -= 4
        if '2023' in tl and '2026' in tl and not (f_flags & _SUBMIT):
            score -= 3

        if score >= 4:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored]


def attach_event_date_by_topics(entries, event_iso, query_text):
    """Add event_date to an existing English/Swedish fact that matches the topic."""
    q_flags = fact_topic_flags(query_text)
    if not q_flags:
        return []
    best, best_score = None, 0
    for entry in entries or []:
        if not isinstance(entry, dict) or fact_event_date(entry):
            continue
        ff = fact_topic_flags(fact_text(entry))
        overlap = _popcount(q_flags & ff)
        if overlap >= 2 and overlap > best_score:
            best_score = overlap
            best = entry
    if best:
        best['event_date'] = event_iso
        return [best]
    return []


def activity_label_for_fact(text, language='en'):
    """Short phrase in the reply language (fact may stay in English in storage)."""
    flags = fact_topic_flags(text)
    if flags & _SUBMIT and (flags & _UNI or flags & _PROJ):
        if language == 'ar':
            return 'سلمت مشروع الجامعة'
        if language == 'sv':
            return 'du lämnade in universitetsprojektet'
        return 'you submitted your university project'
    if flags & _SUBMIT and flags & _THESIS:
        if language == 'ar':
            return 'سلمت رسالة التخرج'
        if language == 'sv':
            return 'du lämnade in uppsatsen'
        return 'you submitted your thesis'
    if flags & _SUBMIT:
        if language == 'ar':
            return 'فعلت ذلك'
        if language == 'sv':
            return 'du gjorde det'
        return 'you did that'
    if language == 'ar':
        return 'ذلك'
    if language == 'sv':
        return 'det'
    return 'that'


def when_reply_for_fact(entry, language='en', *, day_detail=False):
    """Reply in conversation language; fact text in memory may be English."""
    when = format_event_date(entry, language)
    if not when:
        return None
    label = activity_label_for_fact(fact_text(entry), language)
    if language == 'ar':
        if day_detail:
            return f'التاريخ كان {when}.'
        return f'حسب ذاكرتي، {label} في {when}.'
    if language == 'sv':
        if day_detail:
            return f'Datumet var {when}.'
        return f'Det var {when} bro ({label}).'
    if day_detail:
        return f'The date was {when}.'
    return f'According to my memory, {label} on {when}.'


# --- Personal preferences (favorite color, etc.) across languages ---

_COLOR_LEXICON = {
    'أزرق': {'ar': 'أزرق', 'sv': 'blå', 'en': 'blue'},
    'ازرق': {'ar': 'أزرق', 'sv': 'blå', 'en': 'blue'},
    'الأزرق': {'ar': 'الأزرق', 'sv': 'blå', 'en': 'blue'},
    'blue': {'ar': 'أزرق', 'sv': 'blå', 'en': 'blue'},
    'blå': {'ar': 'أزرق', 'sv': 'blå', 'en': 'blue'},
    'bla': {'ar': 'أزرق', 'sv': 'blå', 'en': 'blue'},
    'red': {'ar': 'أحمر', 'sv': 'röd', 'en': 'red'},
    'röd': {'ar': 'أحمر', 'sv': 'röd', 'en': 'red'},
    'rod': {'ar': 'أحمر', 'sv': 'röd', 'en': 'red'},
    'أحمر': {'ar': 'أحمر', 'sv': 'röd', 'en': 'red'},
    'green': {'ar': 'أخضر', 'sv': 'grön', 'en': 'green'},
    'grön': {'ar': 'أخضر', 'sv': 'grön', 'en': 'green'},
    'gron': {'ar': 'أخضر', 'sv': 'grön', 'en': 'green'},
    'أخضر': {'ar': 'أخضر', 'sv': 'grön', 'en': 'green'},
    'yellow': {'ar': 'أصفر', 'sv': 'gul', 'en': 'yellow'},
    'gul': {'ar': 'أصفر', 'sv': 'gul', 'en': 'yellow'},
    'أصفر': {'ar': 'أصفر', 'sv': 'gul', 'en': 'yellow'},
}

_FAVORITE_COLOR_QUERY = (
    'favoritfärg', 'favorit färg', 'favorite color', 'favourite color',
    'favoritfarbe', 'لوني المفضل', 'ما لوني', 'لونك المفضل', 'min favoritfärg',
    'my favorite color', 'vilken är min favorit', 'vad är min favoritfärg',
)
_FAVORITE_COLOR_FACT = (
    'لون', 'مفضل', 'färg', 'favorit', 'favorite', 'colour', 'color',
)


def extract_color_from_text(text):
    if not text:
        return None
    for key, names in _COLOR_LEXICON.items():
        if key in text or key in text.lower():
            return names
    return None


def is_favorite_color_question(text):
    if not text:
        return False
    tl = text.lower()
    if not any(m in tl or m in text for m in _FAVORITE_COLOR_QUERY):
        if not (any(w in tl for w in ('favorit', 'favorite', 'مفضل')) and any(
            w in tl or w in text for w in ('färg', 'color', 'colour', 'لون')
        )):
            return False
    if '?' in text or '؟' in text:
        return True
    return any(
        w in tl
        for w in (
            'vilken', 'vad', 'vilket', 'what', 'which', 'ما', 'ماذا',
            'berätta', 'tell me', 'kommer du ihåg',
        )
    )


def is_favorite_color_fact(text):
    if not text:
        return False
    tl = text.lower()
    has_color_word = extract_color_from_text(text) is not None
    has_topic = any(m in tl or m in text for m in _FAVORITE_COLOR_FACT)
    return has_color_word and has_topic


def match_personal_memory_fact(entries, query):
    """Find a stored preference/fact for a personal question (any language)."""
    if not query or not entries:
        return None
    if is_favorite_color_question(query):
        for entry in entries:
            if is_favorite_color_fact(fact_text(entry)):
                return entry
    return None


def reply_from_personal_fact(entry, language='en'):
    """Answer in the user's language; fact in memory may be another language."""
    text = fact_text(entry)
    colors = extract_color_from_text(text)
    if colors and is_favorite_color_fact(text):
        word = colors.get(language, colors['en'])
        if language == 'sv':
            return f'Din favoritfärg är {word}!'
        if language == 'ar':
            return f'لونك المفضل هو {word}!'
        return f'Your favorite color is {word}!'

    from src.omar_facts import detect_fact_language, owner_fact_for_reply

    stored_lang = detect_fact_language(text)
    body = owner_fact_for_reply(text, stored_lang)
    if language == 'sv':
        return f'Enligt minnet bro: {body}'
    if language == 'ar':
        return f'حسب ذاكرتي: {body}'
    return f'From memory bro: {body}'
