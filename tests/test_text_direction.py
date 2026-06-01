from src.text_direction import (
    strip_bidi_controls,
    text_direction_for_language,
)


def test_text_direction_arabic():
    assert text_direction_for_language('ar') == 'rtl'
    assert text_direction_for_language('en') == 'ltr'


def test_strip_bidi_controls():
    polluted = '\u2067أهلاً!\u2069'
    assert strip_bidi_controls(polluted) == 'أهلاً!'
    assert strip_bidi_controls('hello') == 'hello'
