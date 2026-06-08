from src.omar_facts import owner_fact_for_reply
from src.memory import BeruMemory


def test_arabic_my_color_to_your():
    fact = 'لوني المفضل هو الأزرق'
    reply = owner_fact_for_reply(fact, 'ar')
    assert 'لونك' in reply
    assert 'لوني' not in reply


def test_extract_remember_arabic():
    mem = BeruMemory.__new__(BeruMemory)
    fact = mem.extract_remember_instruction('تذكر أن لوني المفضل هو الأزرق')
    assert fact.startswith('لون')
    assert not fact.startswith('أن')


def test_swedish_still_works():
    assert owner_fact_for_reply('Min favoritfärg är blå', 'sv').startswith('Din')


def test_english_still_works():
    assert 'Your' in owner_fact_for_reply('My favorite color is blue', 'en')
