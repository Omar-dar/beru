import unittest

from chat.chat import detect_full_name, get_response
from src.memory import BeruMemory, OWNER_NAME


class OwnerGateTests(unittest.TestCase):
    def test_yes_comma_omar_is_affirmative(self):
        m = BeruMemory()
        m.start_session()
        m.session['awaiting_owner_confirm'] = True
        self.assertTrue(m.is_affirmative("Yes, it's me Omar."))

    def test_detect_full_name_ignores_yes_comma(self):
        self.assertIsNone(
            detect_full_name("yes, it's me omar", original_text="Yes, it's me Omar.")
        )

    def test_affirmative_routes_to_password_not_guest(self):
        m = BeruMemory()
        m.start_session()
        m.session['awaiting_owner_confirm'] = True
        reply, source = get_response(
            None, None, None, m, None, None,
            "Yes, it's me Omar.",
            brain=None,
        )
        self.assertEqual(source, 'gate')
        self.assertIn('password', reply.lower())
        self.assertEqual(m.get_pending_name(), OWNER_NAME)


if __name__ == '__main__':
    unittest.main()
