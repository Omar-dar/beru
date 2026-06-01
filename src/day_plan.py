"""Parse owner's day plan / recap: activity order and future vs past."""

import re

_ACTIVITY_PATTERNS = (
    ('gym', ('gym', 'gymmet', 'workout', 'träningspass', 'träna')),
    ('eat', ('eat', 'ate', 'eating', 'lunch', 'middag', 'frukost', 'food', 'äta', 'åt')),
    ('chill', ('chill', 'chilled', 'chilling', 'relax', 'koppla av', 'chilla', 'chillade')),
    ('study', ('study', 'studied', 'plugg', 'pluggade', 'jobb', 'work', 'worked')),
)

_FUTURE_MARKERS = (
    'will ', "i'll ", "i'll ", 'gonna ', 'going to ', 'im going to ', "i'm going to ",
    'plan to ', 'ska ', 'skall ', 'kommer att', 'tänker ', 'going to the',
)
_PAST_MARKERS = (
    r'\bwent\b', r'\bgick\b', r'\bwas at\b', r'\bhave been\b', r'\bhar varit\b',
    r'\btränade\b', r'\btrained\b', r'\bchillade\b', r'\bchilled\b',
    r'\båt\b', r'\bate\b', r'\bdid\b', r'\bvar på\b', r'\bbeen to\b',
)


def activity_order(text):
    """Return activities in the order they appear (gym, eat, chill, ...)."""
    if not text:
        return []
    tl = text.lower()
    found = []
    for label, keys in _ACTIVITY_PATTERNS:
        best = -1
        for k in keys:
            idx = tl.find(k)
            if idx >= 0 and (best < 0 or idx < best):
                best = idx
        if best >= 0:
            found.append((best, label))
    found.sort(key=lambda x: x[0])
    order = []
    for _, label in found:
        if not order or order[-1] != label:
            order.append(label)
    return order


def is_future_plan(text):
    """True when the user describes plans, not what already happened."""
    if not text:
        return False
    tl = text.lower()
    has_future = any(m in tl for m in _FUTURE_MARKERS)
    has_past = any(re.search(m, tl) for m in _PAST_MARKERS)
    if has_future and not has_past:
        return True
    return False


def _join_order_en(labels):
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f'{labels[0]} first, then {labels[1]}'
    return ', then '.join(labels[:-1]) + f', then {labels[-1]}'


def _join_order_sv(labels):
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f'{labels[0]} först och sen {labels[1]}'
    return ', sen '.join(labels[:-1]) + f', sen {labels[-1]}'


def _join_order_ar(labels):
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f'{labels[0]} أولاً ثم {labels[1]}'
    return ' ثم '.join(labels)


def describe_plan_order(text, language='en'):
    """Human phrase for activity order in the user's language."""
    order = activity_order(text)
    if not order:
        return None

    en = {
        'gym': 'the gym',
        'eat': 'eating',
        'chill': 'chilling',
        'study': 'studying',
    }
    sv = {
        'gym': 'gymmet',
        'eat': 'äta',
        'chill': 'chilla',
        'study': 'plugga',
    }
    ar = {
        'gym': 'الجيم',
        'eat': 'الأكل',
        'chill': 'الاسترخاء',
        'study': 'الدراسة',
    }
    if language == 'sv':
        return _join_order_sv([sv.get(a, a) for a in order])
    if language == 'ar':
        return _join_order_ar([ar.get(a, a) for a in order])
    return _join_order_en([en.get(a, a) for a in order])


def reply_to_day_message(text, language='en'):
    """Acknowledge day plan or recap with correct order and tense."""
    order = activity_order(text)
    future = is_future_plan(text)
    phrase = describe_plan_order(text, language)

    if not phrase and not order:
        if language == 'sv':
            return 'Okej nice! Berätta mer, hur har dagen varit?'
        if language == 'ar':
            return 'تمام! كيف كان يومك بشكل عام؟'
        return 'Nice! Tell me more, how has the day been?'

    if future:
        if language == 'sv':
            return (
                f'Härligt bro, låter som en bra plan! {phrase.capitalize()}. '
                f'Lycka till på gymmet!'
            )
        if language == 'ar':
            return (
                f'حلو! خطة حلوة: {phrase}. '
                f'بالتوفيق في التمرين!'
            )
        return (
            f'Nice bro, sounds like a solid plan! {phrase.capitalize()}. '
            f'Have a great workout when you go!'
        )

    # Past / already happened today
    if language == 'sv':
        return (
            f'Härligt bro, låter som en bra dag! {phrase.capitalize()}. '
            f'Hur kändes det?'
        )
    if language == 'ar':
        return f'حلو! {phrase.capitalize()}. كيف كان شعورك؟'
    return (
        f'Nice bro, sounds like a solid day! {phrase.capitalize()}. '
        f'How did it feel?'
    )
