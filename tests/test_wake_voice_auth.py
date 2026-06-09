import unittest

from src.memory import BeruMemory
from src.voice_auth import voice_auth_enabled
from src.wake import is_wake_only, is_wake_phrase, strip_wake_prefix, wake_greeting


class WakePhraseTests(unittest.TestCase):
    def test_wake_phrases(self):
        self.assertTrue(is_wake_phrase('Beru'))
        self.assertTrue(is_wake_phrase('Wake up Beru'))
        self.assertTrue(is_wake_phrase('Hey Beru'))
        self.assertTrue(is_wake_phrase('Hey, Barrow!'))
        self.assertTrue(is_wake_phrase('Hey, Beryl.'))
        self.assertTrue(is_wake_phrase('Wake up!'))
        self.assertFalse(is_wake_phrase('hello there'))

    def test_wake_only(self):
        self.assertTrue(is_wake_only('Wake up Beru'))
        self.assertFalse(is_wake_only('Beru what is the weather in Stockholm'))

    def test_strip_wake_prefix(self):
        self.assertEqual(
            strip_wake_prefix('Hey Beru what is the weather').lower(),
            'what is the weather',
        )

    def test_wake_greeting_variety(self):
        replies = {wake_greeting('en') for _ in range(12)}
        self.assertGreaterEqual(len(replies), 3)


class VoiceGateMemoryTests(unittest.TestCase):
    def test_start_session_awaits_voice_when_permanent_owner(self):
        m = BeruMemory()
        m.known_users['Omar'] = {
            'full_name': 'Omar Darwish',
            'first_name': 'Omar',
            'is_owner': True,
            'permanently_verified': True,
        }
        m.start_session(clear_history=True)
        if voice_auth_enabled():
            self.assertTrue(m.is_awaiting_voice_wake())
            self.assertFalse(m.is_session_identified())
        else:
            self.assertTrue(m.is_awaiting_owner_confirm())

    def test_confirm_owner_by_voice(self):
        m = BeruMemory()
        m.session['awaiting_voice_wake'] = True
        m.confirm_owner_by_voice('en')
        self.assertTrue(m.is_owner())
        self.assertTrue(m.is_voice_verified())
        self.assertFalse(m.is_awaiting_voice_wake())


if __name__ == '__main__':
    unittest.main()
