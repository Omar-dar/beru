from src.fact_i18n import match_personal_memory_fact, reply_from_personal_fact
from src.knowledge import BeruKnowledge


def test_swedish_question_arabic_fact():
    entries = [{'text': 'لوني المفضل هو الأزرق'}]
    q = 'Vilken är min favoritfärg?'
    entry = match_personal_memory_fact(entries, q)
    assert entry is not None
    reply = reply_from_personal_fact(entry, 'sv')
    assert 'Din favoritfärg är blå' in reply
    assert 'röd' not in reply


def test_knowledge_routes_personal_question():
    k = BeruKnowledge()
    k.set_learned_facts([{'text': 'لوني المفضل هو الأزرق'}])
    reply = k.answer_omar_question('Vilken är min favoritfärg?', 'sv')
    assert reply
    assert 'blå' in reply.lower()
