"""Timestamped facts Omar asks Tild to remember."""

import re
from datetime import date, datetime

from src.relative_dates import infer_event_date_from_text


def owner_fact_for_reply(text, language='en'):
    """
    Rewrite Omar's first-person memory for Tild to say to him.
    Storage keeps Omar's wording (jag/min); replies use du/din.
    """
    if not text:
        return text
    out = text.strip()

    if language in ('sv', 'ar'):
        for pat, repl in (
            (r'\bJag\b', 'Du'),
            (r'\bjag\b', 'du'),
            (r'\bMin\b', 'Din'),
            (r'\bmin\b', 'din'),
            (r'\bMina\b', 'Dina'),
            (r'\bmina\b', 'dina'),
            (r'\bMitt\b', 'Ditt'),
            (r'\bmitt\b', 'ditt'),
            (r'\bMig\b', 'Dig'),
            (r'\bmig\b', 'dig'),
        ):
            out = re.sub(pat, repl, out)

    if language in ('en', 'ar'):
        for pat, repl in (
            (r"\bI'm\b", "You're"),
            (r"\bI've\b", "You've"),
            (r"\bI'll\b", "You'll"),
            (r'\bI\b', 'You'),
            (r'\bMy\b', 'Your'),
            (r'\bmy\b', 'your'),
            (r'\bMe\b', 'You'),
            (r'\bme\b', 'you'),
            (r'\bmine\b', 'yours'),
        ):
            out = re.sub(pat, repl, out)

    if out and out[0].islower():
        out = out[0].upper() + out[1:]
    return out


def fact_text(entry):
    if isinstance(entry, dict):
        return (entry.get('text') or '').strip()
    return str(entry).strip()


def fact_event_date(entry):
    """When the remembered event happened (not when it was saved)."""
    if isinstance(entry, dict):
        return entry.get('event_date')
    return None


def normalize_fact_entries(raw):
    """Load legacy string facts and {text, saved_at, date, event_date} objects."""
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            text = fact_text(item)
            if text:
                entry = {
                    'text': text,
                    'saved_at': item.get('saved_at'),
                    'date': item.get('date'),
                    'event_date': item.get('event_date'),
                }
                if not entry['event_date']:
                    entry['event_date'] = infer_event_date_from_text(text)
                out.append(entry)
        elif isinstance(item, str) and item.strip():
            entry = new_fact_entry(item.strip())
            out.append(entry)
    return out


def new_fact_entry(text, reference=None):
    now = reference or datetime.now()
    text = text.strip().strip('. ,;')
    event_date = infer_event_date_from_text(text, now)
    entry = {
        'text': text,
        'saved_at': now.isoformat(timespec='minutes'),
        'date': now.date().isoformat(),
    }
    if event_date:
        entry['event_date'] = event_date
    return entry


def format_timestamp(entry, language='en'):
    if isinstance(entry, dict) and entry.get('saved_at'):
        try:
            dt = datetime.fromisoformat(entry['saved_at'])
        except ValueError:
            return entry.get('date') or ''
        if language == 'sv':
            months = (
                'januari', 'februari', 'mars', 'april', 'maj', 'juni',
                'juli', 'augusti', 'september', 'oktober', 'november', 'december',
            )
            return f'{dt.day} {months[dt.month - 1]} {dt.year} kl {dt:%H:%M}'
        if language == 'ar':
            return f'{dt.date().isoformat()} {dt:%H:%M}'
        return dt.strftime('%Y-%m-%d %H:%M')
    if isinstance(entry, dict) and entry.get('date'):
        return entry['date']
    return ''


def format_event_date(entry, language='en'):
    from src.relative_dates import format_date_for_language

    ed = fact_event_date(entry)
    if not ed:
        return ''
    try:
        d = date.fromisoformat(ed[:10])
    except ValueError:
        return ed
    return format_date_for_language(d, language)


def format_now(language='en'):
    now = datetime.now()
    if language == 'sv':
        weekdays = (
            'måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag',
        )
        months = (
            'januari', 'februari', 'mars', 'april', 'maj', 'juni',
            'juli', 'augusti', 'september', 'oktober', 'november', 'december',
        )
        return (
            f'Idag är {weekdays[now.weekday()]} {now.day} {months[now.month - 1]} {now.year}, '
            f'klockan är {now:%H:%M}'
        )
    if language == 'ar':
        return f'اليوم {now.date().isoformat()} والساعة {now:%H:%M}'
    return f'Today is {now.strftime("%A %Y-%m-%d")}, the time is {now:%H:%M}'


def facts_on_date(entries, day_iso):
    """Facts whose event_date is day_iso (YYYY-MM-DD). Ignores save date."""
    out = []
    for entry in entries or []:
        ed = fact_event_date(entry)
        if ed and str(ed)[:10] == day_iso:
            out.append(entry)
    return out


def update_facts_event_date(entries, event_date_iso, *, keyword=None, text_hint=None):
    """
    Set event_date on matching facts. Prefer keyword in text, else text_hint overlap.
    Returns list of updated entry dicts.
    """
    updated = []
    hint = (text_hint or '').lower()
    hint_words = set(hint.split()) if hint else set()

    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        t = fact_text(entry).lower()
        match = False
        if keyword and keyword in t:
            match = True
        elif hint_words and len(hint_words.intersection(set(t.split()))) >= 2:
            match = True
        elif not keyword and not hint_words and entries:
            match = entry is entries[-1]

        if match:
            entry['event_date'] = event_date_iso
            updated.append(entry)
    return updated
