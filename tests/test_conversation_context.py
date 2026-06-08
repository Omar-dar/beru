import unittest

from src.knowledge import BeruKnowledge
from src.memory import BeruMemory
from src.router import (
    is_code_explanation_request,
    is_code_generation_request,
    is_conversation_context_question,
    route_request,
    ROUTE_BRAIN,
    ROUTE_SEARCH,
)
from src.search import BeruSearch


class ConversationContextTests(unittest.TestCase):
    def _memory_with_code_reply(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        m.add_to_conversation('human', 'can you code?')
        m.add_to_conversation(
            'beru',
            '```python\ndef greet(language):\n    return "Hello!"\n```',
        )
        return m

    def test_can_you_code_is_not_generation_request(self):
        self.assertFalse(is_code_generation_request('can you code?'))

    def test_write_code_is_generation_request(self):
        self.assertTrue(is_code_generation_request('write me a python script'))

    def test_code_capability_asks_for_details(self):
        k = BeruKnowledge()
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        reply = k.answer_code_capability_question('en', memory=m)
        self.assertIn('language', reply.lower())
        self.assertNotIn('```', reply)

    def test_what_is_that_code_uses_brain_not_search(self):
        m = self._memory_with_code_reply()
        self.assertTrue(is_conversation_context_question('what is that code', m))
        route = route_request('what is that code', m, search=object())
        self.assertEqual(route, ROUTE_BRAIN)

    def test_explain_code_followup(self):
        m = self._memory_with_code_reply()
        self.assertTrue(is_conversation_context_question(
            'i am asking about the code what does it do?', m
        ))
        route = route_request('i am asking about the code what does it do?', m, search=object())
        self.assertNotEqual(route, ROUTE_SEARCH)

    def test_what_does_this_code_never_searches(self):
        m = self._memory_with_code_reply()
        q = 'what does this code do?'
        self.assertTrue(is_code_explanation_request(q))
        self.assertFalse(BeruSearch().should_search(q, m))

    def test_pasted_code_explanation_request(self):
        msg = '''no the code you wrote what does this code do\n\ndef greet(name):\n return "hi"'''
        self.assertTrue(is_code_explanation_request(msg))

    def test_like_your_name_is_opinion(self):
        k = BeruKnowledge()
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        self.assertTrue(k.is_beru_opinion_question('do you like your name?', memory=m))
        reply = k.answer_beru_self_question('do you like your name?', 'en', memory=m)
        self.assertIn('like', reply.lower())


if __name__ == '__main__':
    unittest.main()
