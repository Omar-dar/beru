import unittest

from src.memory import BeruMemory


class ChatOnlyTests(unittest.TestCase):
    def setUp(self):
        self.memory = BeruMemory()
        self.memory.identify_session('Omar', 'en', is_owner=True)

    def test_chat_only_message_detected(self):
        self.assertTrue(self.memory.is_chat_only_message("I'm just chatting with you. That's all"))
        self.assertTrue(self.memory.is_chat_only_message('just want to chat'))
        self.assertFalse(self.memory.is_chat_only_message('search weather in Stockholm'))

    def test_casual_short_ack_without_question(self):
        self.memory.conversation_history.append({
            'role': 'beru',
            'text': 'It is currently 21°C in Stockholm. Partly cloudy.',
        })
        self.assertTrue(self.memory.is_casual_conversation_reply('Okay.'))

    def test_answer_chat_only(self):
        reply = self.memory.answer_chat_only('en')
        self.assertIn('chat', reply.lower())
        self.assertNotIn('gym', reply.lower())


if __name__ == '__main__':
    unittest.main()
