import unittest

from src.computer_nlu import extract_search_topic, is_natural_computer_request, is_talking_to_beru, resolve_plan


class ComputerNluTests(unittest.TestCase):
    def test_natural_weather_wording(self):
        phrases = [
            "Good, can you check what's the weather like in Stockholm?",
            "I need to know if it's raining in Gothenburg today",
            "How hot is it in Malmö right now?",
            "Beru what's the temperature in Stockholm",
        ]
        for p in phrases:
            self.assertTrue(is_natural_computer_request(p), p)
            plan = resolve_plan(p, brain=None)
            self.assertIsNotNone(plan, p)
            self.assertEqual(plan['intent'], 'browser_search')

    def test_not_chitchat(self):
        self.assertFalse(is_natural_computer_request('How are you Bero?'))
        self.assertFalse(is_natural_computer_request('Good, good.'))
        self.assertFalse(is_natural_computer_request("What's your name?"))
        self.assertFalse(is_natural_computer_request('Goodbye'))
        self.assertFalse(is_natural_computer_request('Hey, Barrow!'))
        self.assertFalse(is_natural_computer_request('Wake up!'))
        self.assertFalse(is_natural_computer_request('What do you want to do?'))
        self.assertFalse(is_natural_computer_request('What is this? Why did you open the browser?'))
        self.assertEqual(extract_search_topic('Goodbye'), '')
        self.assertEqual(extract_search_topic('Hey, Barrow!'), '')
        self.assertEqual(extract_search_topic('What do you want to do?'), '')
        self.assertIsNone(resolve_plan('Goodbye', brain=None))
        self.assertIsNone(resolve_plan('What do you want to do?', brain=None))

    def test_general_search(self):
        p = 'Find me the latest news about AI chips'
        self.assertTrue(is_natural_computer_request(p))
        q = extract_search_topic(p)
        self.assertIn('ai', q.lower())

    def test_open_google_polite_not_talking_to_beru(self):
        from src.computer_control import is_computer_control_request, parse_computer_intent
        from src.computer_nlu import is_talking_to_beru

        q = 'Could you open Google on browser?'
        self.assertFalse(is_talking_to_beru(q))
        self.assertEqual(parse_computer_intent(q), 'open_url')
        self.assertTrue(is_computer_control_request(q, is_owner=True))

        p = 'Take me to youtube.com'
        plan = resolve_plan(p, brain=None)
        self.assertIsNotNone(plan)
        self.assertIn(plan['intent'], ('open_url', 'browser_search'))


if __name__ == '__main__':
    unittest.main()
