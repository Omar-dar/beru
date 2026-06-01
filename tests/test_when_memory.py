from src.fact_i18n import facts_matching_when_query


def test_facts_matching_when_query_prefers_dated_entry():
    entries = [
        {'text': 'University program runs 2023 to 2026', 'event_date': None},
        {
            'text': 'I submitted the university project',
            'event_date': '2026-05-29',
        },
    ]
    matches = facts_matching_when_query(entries, 'متى سلمت مشروع الجامعة؟')
    assert matches
    assert matches[0]['event_date'] == '2026-05-29'
