import unittest

from src.knowledge import BeruKnowledge
from src.memory import BeruMemory


class BeruPersonalityTests(unittest.TestCase):
    def test_likes_name_opinion_is_consistent(self):
        k = BeruKnowledge()
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)

        q = 'do you like your name?'
        self.assertTrue(k.is_beru_opinion_question(q, memory=m))
        a1 = k.answer_beru_opinion_question(q, 'en', memory=m)
        a2 = k.answer_beru_opinion_question(q, 'en', memory=m)
        self.assertEqual(a1, a2)
        self.assertIn('like', a1.lower())
        self.assertIn('beru', a1.lower())

    def test_name_followup_it(self):
        k = BeruKnowledge()
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        m.add_to_conversation('beru', 'My name is Beru. You gave me that name when you created me.')

        self.assertTrue(k.is_beru_opinion_question('so do you like it?', memory=m))
        reply = k.answer_beru_opinion_question('so do you like it?', 'en', memory=m)
        self.assertIn('beru', reply.lower())

    def test_self_question_without_opinion_falls_through(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        answer = m.answer_from_knowledge('tell me a random made-up fact about mars colonies', 'en')
        self.assertIsNone(answer)


if __name__ == '__main__':
    unittest.main()
