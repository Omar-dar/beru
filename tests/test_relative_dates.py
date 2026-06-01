"""Relative date parsing for Tild memory."""

from datetime import datetime

from src.relative_dates import (
    infer_event_date_from_text,
    parse_calendar_date,
    parse_date_clarification,
    resolve_relative_phrase,
)


def test_forgar_on_june_first():
    ref = datetime(2026, 6, 1, 12, 0)
    d = resolve_relative_phrase('jag lämnade in uppsatsen i förrgår', ref)
    assert d.isoformat() == '2026-05-30'


def test_yesterday():
    ref = datetime(2026, 6, 1, 12, 0)
    d = resolve_relative_phrase('igår åt jag lunch', ref)
    assert d.isoformat() == '2026-05-31'


def test_three_days_ago():
    ref = datetime(2026, 6, 1, 12, 0)
    d = resolve_relative_phrase('for 3 days ago', ref)
    assert d.isoformat() == '2026-05-29'


def test_parse_may_29():
    ref = datetime(2026, 6, 1, 12, 0)
    d = parse_calendar_date('den 29 maj', ref)
    assert d.isoformat() == '2026-05-29'


def test_clarification_swedish():
    ref = datetime(2026, 6, 1, 12, 0)
    text = 'När jag säger förrgår jag menar den 29 may inte idag'
    parsed = parse_date_clarification(text, ref)
    assert parsed is not None
    assert parsed['event_date'] == '2026-05-29'
    assert parsed['keyword'] == 'förrgår'


def test_infer_from_remember_phrase():
    ref = datetime(2026, 6, 1, 1, 48)
    assert infer_event_date_from_text(
        'Jag lämnade in min C-uppsats i förrgår', ref
    ) == '2026-05-30'
