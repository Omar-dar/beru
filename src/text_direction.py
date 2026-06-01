"""Text direction metadata for Arabic UI rendering (tild-ui sets dir=rtl)."""

import re

# Invisible bidi controls — must not appear in chat text (UI shows them as ⁧ ⁩)
_BIDI_CONTROLS = re.compile(
    '[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]'
)


def text_direction_for_language(language):
    return 'rtl' if language == 'ar' else 'ltr'


def strip_bidi_controls(text):
    """Remove stray Unicode bidi isolates from model or legacy API output."""
    if not text:
        return text
    return _BIDI_CONTROLS.sub('', text)
