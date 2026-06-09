"""Fix common voice/STT mishears before routing."""

from __future__ import annotations

import re

# Whisper often hears "tab" as "tap".
_TAP_TO_TAB = re.compile(r'\b(tap|taps)\b', re.I)


def normalize_stt_text(text: str) -> str:
    if not text or not str(text).strip():
        return text or ''
    s = str(text).strip()
    s = _TAP_TO_TAB.sub(lambda m: 'tabs' if m.group(1).lower() == 'taps' else 'tab', s)
    return s
