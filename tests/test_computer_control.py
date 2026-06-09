import unittest
from unittest.mock import patch

from src.computer_control import (
    _extract_search_query,
    answer_computer_followup,
    capabilities,
    ComputerActionResult,
    execute,
    is_computer_control_request,
    is_computer_followup,
    parse_computer_intent,
    release_overlay_for_ui,
)
from src.memory import BeruMemory


class ComputerControlTests(unittest.TestCase):
    def test_parse_google_search(self):
        self.assertEqual(parse_computer_intent('search google for python asyncio'), 'browser_search')
        self.assertEqual(_extract_search_query('search google for python asyncio'), 'python asyncio')

    def test_search_on_google_weather_query(self):
        q = (
            "Good, good. Can you search on Google what's the weather in Stockholm today?"
        )
        eq = _extract_search_query(q).lower()
        self.assertIn('stockholm', eq)
        self.assertIn('weather', eq)

    def test_voice_open_browser_and_search(self):
        q = 'Can you open the browser and search what the weather today in Stockholm'
        self.assertEqual(parse_computer_intent(q), 'browser_search')
        self.assertIn('weather', _extract_search_query(q).lower())
        self.assertIn('stockholm', _extract_search_query(q).lower())

    def test_search_on_browser_stockholm(self):
        q = "Can you search on the browser what's the weather in Stockholm today?"
        self.assertEqual(parse_computer_intent(q), 'browser_search')
        eq = _extract_search_query(q).lower()
        self.assertIn('stockholm', eq)
        self.assertIn('weather', eq)

    def test_stt_talking_garble_refined(self):
        refined = _extract_search_query(
            'Can you open the browser and search for what the weather is talking today in Stockholm'
        )
        self.assertIn('stockholm', refined.lower())

    def test_general_look_up_not_weather_only(self):
        self.assertEqual(parse_computer_intent('look up Python asyncio tutorials'), 'browser_search')
        self.assertEqual(_extract_search_query('look up Python asyncio tutorials'), 'Python asyncio tutorials')

    def test_see_computer_intent(self):
        self.assertEqual(parse_computer_intent('what can you see on my computer'), 'see_computer')
        self.assertEqual(parse_computer_intent('what is on my screen'), 'see_computer')

    def test_release_overlay_after_answer(self):
        action = ComputerActionResult(
            ok=True,
            message='It is 21°C in Stockholm.',
            activity='reading_page',
            source='search',
            browser_url='https://www.google.com/search?q=weather',
        )
        out = release_overlay_for_ui(action)
        self.assertEqual(out.activity, 'idle')
        self.assertTrue(out.browser_open)

    def test_read_it_followup_trigger(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        m.set_last_computer_action(
            action_type='search',
            query='weather in stockholm today',
            url='https://www.google.com/search?q=weather',
            summary='It is currently 21°C in Stockholm.',
        )
        self.assertTrue(is_computer_followup('can you read it for me?', m))
        self.assertTrue(is_computer_followup("tell me what's the weather", m))

    def test_chat_only_not_computer_followup(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        m.set_last_computer_action(
            action_type='search',
            query='weather in stockholm today',
            url='https://www.google.com/search?q=weather',
            summary='It is currently 21°C in Stockholm.',
        )
        self.assertFalse(is_computer_followup("I'm just chatting with you. That's all", m))
        self.assertFalse(is_computer_followup('Okay.', m))

    @patch('src.computer_control._weather_api_answer', return_value='It is currently 5°C in Stockholm.')
    @patch('src.computer_control._facts_from_url', return_value=('', 'page', 'Google', 'no text'))
    def test_search_weather_uses_api_when_scrape_empty(self, _scrape, weather):
        result = execute('search google for weather in Stockholm', language='en')
        self.assertNotIn('https://', result.message)
        self.assertIn('5°C', result.message)
        weather.assert_called_once()

    def test_parse_open_url(self):
        self.assertEqual(parse_computer_intent('open github.com'), 'open_url')
        self.assertEqual(parse_computer_intent('open Google'), 'open_url')
        self.assertEqual(parse_computer_intent('öppna Facebook hemsida'), 'open_url')

    def test_look_at_browser_is_see_not_search(self):
        self.assertEqual(parse_computer_intent('look at the browser'), 'see_computer')
        self.assertEqual(parse_computer_intent('read it'), 'see_computer')

    @patch('src.computer_control._facts_from_url')
    def test_open_google_normalizes_url(self, scrape):
        result = execute('open Google', language='en')
        self.assertTrue(result.ok)
        self.assertEqual(result.browser_url, 'https://www.google.com')
        self.assertEqual(result.client_actions[0]['url'], 'https://www.google.com')
        self.assertTrue(result.client_actions[0].get('reuse_tab'))
        self.assertEqual(result.activity, 'browsing')
        self.assertNotIn('Koldioxid', result.message)
        scrape.assert_not_called()

    def test_polite_open_google_on_browser_not_chitchat(self):
        from src.computer_nlu import is_talking_to_beru

        q = 'Could you open Google on browser?'
        self.assertFalse(is_talking_to_beru(q))
        self.assertEqual(parse_computer_intent(q), 'open_url')
        self.assertTrue(is_computer_control_request(q, is_owner=True))

    def test_close_facebook_tab(self):
        self.assertEqual(parse_computer_intent('Close the Facebook tab.'), 'close_tab')
        result = execute('Close the Facebook tab.', language='en')
        self.assertTrue(result.ok)
        self.assertEqual(result.client_actions[0]['type'], 'close_tab')
        self.assertEqual(result.client_actions[0]['site'], 'facebook')

    def test_close_google_tap_stt(self):
        from src.stt_normalize import normalize_stt_text

        q = normalize_stt_text('Close Google Tap.')
        self.assertEqual(parse_computer_intent(q), 'close_tab')

    def test_capabilities_not_search(self):
        from src.computer_nlu import extract_search_topic

        q = 'Could you tell me what you can do?'
        self.assertFalse(is_computer_control_request(q, is_owner=True))
        self.assertEqual(extract_search_topic(q), '')

    def test_scroll_down(self):
        self.assertEqual(parse_computer_intent('scroll down on the page'), 'scroll_page')
        result = execute('scroll down', language='en')
        self.assertEqual(result.client_actions[0]['type'], 'scroll')
        self.assertEqual(result.client_actions[0]['direction'], 'down')

    def test_browse_browser_capability(self):
        self.assertEqual(parse_computer_intent('can you browse my browser?'), 'takeover_help')

    def test_open_link_capability_question(self):
        self.assertEqual(parse_computer_intent('can you open a link?'), 'takeover_help')

    def test_open_link_without_url_prompts(self):
        result = execute('open a link', language='en')
        self.assertFalse(result.ok)
        self.assertIn('github.com', result.message.lower())

    def test_parse_screenshot(self):
        self.assertEqual(parse_computer_intent('take a screenshot'), 'screenshot')

    def test_owner_only_gate(self):
        self.assertFalse(is_computer_control_request('search google for cats', is_owner=False))
        self.assertTrue(is_computer_control_request('search google for cats', is_owner=True))
        self.assertFalse(is_computer_control_request('Goodbye', is_owner=True))
        self.assertFalse(is_computer_control_request('Hey, Barrow!', is_owner=True))
        self.assertFalse(is_computer_control_request("What's your name?", is_owner=True))
        self.assertFalse(is_computer_control_request('What do you want to do?', is_owner=True))
        self.assertFalse(is_computer_control_request(
            'What is this? Why did you open the browser?', is_owner=True,
        ))

    @patch('src.computer_control._facts_from_url')
    def test_browser_search_returns_scraped_facts(self, scrape):
        scrape.return_value = (
            'Asyncio is a library for concurrent Python code.',
            'full page',
            'Google Search',
            '',
        )
        result = execute('search google for python asyncio', language='en')
        self.assertTrue(result.ok)
        self.assertEqual(result.source, 'search')
        self.assertEqual(result.activity, 'reading_page')
        self.assertEqual(result.search_query, 'python asyncio')
        self.assertIn('open_url', result.client_actions[0]['type'])
        self.assertNotIn('https://', result.message)

    @patch('src.computer_control._facts_from_url')
    def test_open_url(self, scrape):
        scrape.return_value = ('', '', 'Example', '')
        result = execute('go to https://example.com', language='en')
        self.assertTrue(result.ok)
        self.assertEqual(result.browser_url, 'https://example.com')
        self.assertEqual(result.client_actions[0]['url'], 'https://example.com')

    def test_capabilities(self):
        caps = capabilities()
        self.assertIn('browser_search', caps)
        self.assertTrue(caps['owner_only'])

    def test_computer_followup_after_search(self):
        m = BeruMemory()
        m.identify_session('Omar', 'en', is_owner=True)
        m.set_last_computer_action(
            action_type='search',
            query='weather in Stockholm',
            url='https://www.google.com/search?q=weather',
            summary='It is currently 5°C in Stockholm.',
        )
        self.assertTrue(is_computer_followup('what did you find?', m))
        result = answer_computer_followup('what did you find?', m, language='en')
        self.assertIn('5°C', result.message)

    def test_browser_session_end(self):
        from src.computer_control import execute_browser_end, is_browser_session_end

        self.assertTrue(is_browser_session_end('go back to beru'))
        end = execute_browser_end(language='en')
        self.assertEqual(end.activity, 'idle')
        self.assertEqual(end.client_actions[0]['type'], 'focus_app')


if __name__ == '__main__':
    unittest.main()
