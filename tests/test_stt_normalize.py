import unittest

from src.computer_control import parse_computer_intent, remember_computer_action, release_overlay_for_ui, execute
from src.memory import BeruMemory
from src.stt_normalize import normalize_stt_text
from src.wake import is_near_wake_miss, sounds_like_wake


class SttNormalizeTests(unittest.TestCase):
    def test_tap_to_tab(self):
        self.assertIn('tab', normalize_stt_text('Close Google Tap.').lower())

    def test_close_google_tap_intent(self):
        self.assertEqual(parse_computer_intent(normalize_stt_text('Close Google Tap.')), 'close_tab')

    def test_bellow_is_wake(self):
        self.assertTrue(sounds_like_wake('BELLOW'))

    def test_near_miss_prompt(self):
        self.assertTrue(is_near_wake_miss('pillow'))

    def test_browser_session_survives_overlay_release(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        action = release_overlay_for_ui(execute('open Google', language='en', memory=m))
        remember_computer_action(m, action)
        last = m.get_last_computer_action()
        self.assertTrue(last.get('url'))
        self.assertIn('google', last['url'])


if __name__ == '__main__':
    unittest.main()
