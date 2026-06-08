"""Normalize punctuation in user-facing Beru text."""

import re

# Em dash, en dash, figure dash, horizontal bar
_LONG_DASHES = ('\u2014', '\u2013', '\u2012', '\u2015')


def strip_long_dashes(text):
    """Replace long dashes with a simple hyphen; preserve line breaks."""
    if not text:
        return text
    for ch in _LONG_DASHES:
        text = text.replace(ch, ' - ')
    lines = [re.sub(r'[ \t]+', ' ', line) for line in text.split('\n')]
    return '\n'.join(lines)
