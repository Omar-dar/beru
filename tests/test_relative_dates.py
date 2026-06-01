"""Relative date parsing for Tild memory."""

from datetime import datetime

from src.relative_dates import (
    format_date_for_language,
    infer_event_date_from_text,
    parse_calendar_date,
    parse_date_clarification,
    resolve_relative_phrase,
)
from datetime import date


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


def test_arabic_yesterday():
    ref = datetime(2026, 6, 1, 12, 0)
    d = resolve_relative_phrase('سلمت المشروع أمس', ref)
    assert d.isoformat() == '2026-05-31'


def test_format_date_arabic():
    assert format_date_for_language(date(2026, 5, 29), 'ar') == '29 مايو 2026'


def test_arabic_day_month_mai():
    ref = datetime(2026, 6, 1, 12, 0)
    d = parse_calendar_date('سلمت مشروع الجامعة يوم 29 ماي', ref)
    assert d.isoformat() == '2026-05-29'
