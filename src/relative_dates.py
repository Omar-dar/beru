"""Resolve relative and explicit calendar dates in user text (EN/SV/AR)."""

import re
from datetime import date, datetime, timedelta

_MONTHS = {
    'jan': 1, 'january': 1, 'januari': 1,
    'feb': 2, 'february': 2, 'februari': 2,
    'mar': 3, 'march': 3, 'mars': 3,
    'apr': 4, 'april': 4,
    'may': 5, 'maj': 5,
    'jun': 6, 'june': 6, 'juni': 6,
    'jul': 7, 'july': 7, 'juli': 7,
    'aug': 8, 'august': 8, 'augusti': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'okt': 10, 'october': 10, 'oktober': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12, 'december': 12,
    'ماي': 5, 'مايو': 5,
}

_AR_MONTHS_MAP = {
    'يناير': 1, 'فبراير': 2, 'مارس': 3, 'أبريل': 4, 'ابريل': 4,
    'مايو': 5, 'ماي': 5, 'يونيو': 6, 'يوليو': 7,
    'أغسطس': 8, 'اغسطس': 8, 'سبتمبر': 9,
    'أكتوبر': 10, 'اكتوبر': 10, 'نوفمبر': 11, 'ديسمبر': 12,
}

# (pattern, days before reference date; negative = future)
_RELATIVE_RULES = [
    (r'\b(day before yesterday|i förrgår|förrgår|forre igår|förre igår|forreigar)\b', 2),
    (r'\b(yesterday|igår|i går)\b', 1),
    (r'\b(today|idag)\b', 0),
    (r'\b(tomorrow|imorgon|i morgon)\b', -1),
    (r'\b(أول\s*أمس|اول\s*امس)\b', 2),
    (r'\b(أمس)\b', 1),
    (r'\b(اليوم)\b', 0),
    (r'\b(غداً|غدا)\b', -1),
    (r'\b(\d{1,2})\s+days?\s+ago\b', None),
    (r'\bfor\s+(\d{1,2})\s+days?\s+ago\b', None),
    (r'\bför\s+(\d{1,2})\s+dag(?:ar)?\s+sedan\b', None),
    (r'\b(\d{1,2})\s+dag(?:ar)?\s+sedan\b', None),
    (r'\bin\s+(\d{1,2})\s+days?\b', None),
    (r'\bom\s+(\d{1,2})\s+dag(?:ar)?\b', None),
]

_EXPLICIT_DATE = re.compile(
    r'(?:den\s+)?(\d{1,2})(?:\s+|\s*/\s*|-)'
    r'(\d{1,2}|jan(?:uary|uari)?|feb(?:ruary|ruari)?|mar(?:ch|s)?|apr(?:il)?|'
    r'may|maj|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust)?(?:i)?|sep(?:t(?:ember)?)?|'
    r'oct(?:ober)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)?'
    r'(?:\s+|\s*/\s*|-)?'
    r'(\d{2,4}|jan(?:uary|uari)?|feb(?:ruary|ruari)?|mar(?:ch|s)?|apr(?:il)?|'
    r'may|maj|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust)?(?:i)?|sep(?:t(?:ember)?)?|'
    r'oct(?:ober)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)?',
    re.I,
)

_SIMPLE_DAY_MONTH = re.compile(
    r'(?:den\s+)?(\d{1,2})\s+'
    r'(jan(?:uary|uari)?|feb(?:ruary|uari)?|mar(?:ch|s)?|apr(?:il)?|'
    r'may|maj|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust)?(?:i)?|sep(?:t(?:ember)?)?|'
    r'oct(?:ober)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
    r'(?:\s+(\d{4}))?',
    re.I,
)

_AR_DAY_MONTH = re.compile(
    r'(?:يوم\s+)?(\d{1,2})\s+'
    r'(يناير|فبراير|مارس|أبريل|ابريل|مايو|ماي|يونيو|يوليو|'
    r'أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)'
    r'(?:\s+(\d{4}))?',
)

_CLARIFICATION_PATTERNS = [
    re.compile(
        r'när\s+jag\s+säger\s+(\w+)\s+.*?(?:menar|betyder)\s+.*?(?:den\s+)?(\d{1,2})\s+'
        r'(jan(?:uari)?|feb(?:ruari)?|mar(?:s)?|apr(?:il)?|maj|may|jun(?:i)?|jul(?:i)?|'
        r'aug(?:usti)?|sep(?:tember)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)',
        re.I,
    ),
    re.compile(
        r'when\s+i\s+say\s+(\w+).*?(?:mean|meant)\s+.*?(?:the\s+)?(\d{1,2})\s+'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|'
        r'aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)',
        re.I,
    ),
    re.compile(
        r'(\w+)\s+menar\s+(?:alltså\s+)?(?:den\s+)?(\d{1,2})\s+'
        r'(jan(?:uari)?|feb(?:ruari)?|mar(?:s)?|apr(?:il)?|maj|may|jun(?:i)?|jul(?:i)?|'
        r'aug(?:usti)?|sep(?:tember)?|okt(?:ober)?|nov(?:ember)?|dec(?:ember)?)',
        re.I,
    ),
]


def _month_num(token):
    if not token:
        return None
    if token.isdigit():
        m = int(token)
        return m if 1 <= m <= 12 else None
    t = token.strip()
    if t in _AR_MONTHS_MAP:
        return _AR_MONTHS_MAP[t]
    return _MONTHS.get(t.lower()[:12]) or _MONTHS.get(t.lower()[:3])


def _year_num(token, ref):
    if not token:
        return ref.year
    if token.isdigit():
        y = int(token)
        return y + 2000 if y < 100 else y
    return ref.year


def parse_calendar_date(text, reference=None):
    """Parse explicit dates like '29 may', 'den 29 maj', '2026-05-29'."""
    if not text:
        return None
    ref = reference or datetime.now()

    iso = re.search(r'\b(20\d{2})-(\d{2})-(\d{2})\b', text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass

    for pattern in (_SIMPLE_DAY_MONTH, _AR_DAY_MONTH):
        m = pattern.search(text)
        if m:
            day = int(m.group(1))
            month = _month_num(m.group(2))
            year = _year_num(m.group(3), ref) if m.lastindex and m.lastindex >= 3 else ref.year
            if month:
                try:
                    d = date(year, month, day)
                    if not (m.lastindex and m.lastindex >= 3 and m.group(3)) and d > ref.date():
                        d = date(year - 1, month, day)
                    return d
                except ValueError:
                    pass

    return None


def resolve_relative_phrase(text, reference=None):
    """
    Return calendar date for the strongest relative phrase in text, or None.
    Uses reference datetime (default: now).
    """
    if not text:
        return None
    ref = reference or datetime.now()
    text_lower = text.lower()

    for pattern, offset in _RELATIVE_RULES:
        m = re.search(pattern, text_lower, re.I)
        if not m:
            continue
        if offset is None:
            days = int(m.group(1))
        else:
            days = offset
        return ref.date() - timedelta(days=days)

    return None


def infer_event_date_from_text(text, reference=None):
    """Best event date from explicit calendar date or relative words."""
    ref = reference or datetime.now()
    explicit = parse_calendar_date(text, ref)
    if explicit:
        return explicit.isoformat()
    relative = resolve_relative_phrase(text, ref)
    if relative:
        return relative.isoformat()
    return None


def parse_date_clarification(text, reference=None):
    """
    Parse owner corrections like 'when I say förrgår I mean May 29'.
    Returns dict: keyword (optional), event_date (iso), explicit_date (date).
    """
    if not text:
        return None
    ref = reference or datetime.now()

    for pat in _CLARIFICATION_PATTERNS:
        m = pat.search(text)
        if m:
            keyword = m.group(1).lower()
            day = int(m.group(2))
            month = _month_num(m.group(3))
            if month:
                try:
                    d = date(ref.year, month, day)
                    if d > ref.date():
                        d = date(ref.year - 1, month, day)
                    return {
                        'keyword': keyword,
                        'event_date': d.isoformat(),
                        'explicit_date': d,
                    }
                except ValueError:
                    pass

    explicit = parse_calendar_date(text, ref)
    if explicit and any(
        w in text.lower()
        for w in ('menar', 'mean', 'meant', 'betyder', 'not today', 'inte idag', 'wrong date')
    ):
        kw = None
        km = re.search(
            r'när\s+jag\s+säger\s+(\w+)|when\s+i\s+say\s+(\w+)|(\w+)\s+menar',
            text,
            re.I,
        )
        if km:
            kw = next(g for g in km.groups() if g).lower()
        return {
            'keyword': kw,
            'event_date': explicit.isoformat(),
            'explicit_date': explicit,
        }

    return None


_AR_MONTHS = (
    'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
    'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر',
)


def format_date_for_language(d, language='en'):
    """Human-readable date for replies."""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    if language == 'sv':
        months = (
            'januari', 'februari', 'mars', 'april', 'maj', 'juni',
            'juli', 'augusti', 'september', 'oktober', 'november', 'december',
        )
        return f'{d.day} {months[d.month - 1]} {d.year}'
    if language == 'ar':
        return f'{d.day} {_AR_MONTHS[d.month - 1]} {d.year}'
    return d.strftime('%B %d, %Y')
