from src.fact_i18n import facts_matching_when_query, when_reply_for_fact


def test_arabic_query_matches_english_fact():
    entries = [
        {'text': 'His university education runs 2023 to 2026', 'event_date': None},
        {
            'text': 'I submitted my university project',
            'event_date': '2026-05-29',
        },
    ]
    matches = facts_matching_when_query(entries, 'متى سلمت مشروع الجامعة؟')
    assert matches[0]['event_date'] == '2026-05-29'


def test_arabic_reply_from_english_fact():
    entry = {
        'text': 'I submitted my university project',
        'event_date': '2026-05-29',
    }
    reply = when_reply_for_fact(entry, 'ar')
    assert '29 مايو 2026' in reply
    assert 'سلمت مشروع الجامعة' in reply
    assert 'submitted' not in reply
