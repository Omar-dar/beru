import unittest

from src.api_contract import normalize_source, ui_chat_payload


class ApiContractTests(unittest.TestCase):
    def test_search_source_and_activity(self):
        p = ui_chat_payload(
            response='Found it.',
            language='en',
            source='search',
        )
        self.assertEqual(p['source'], 'search')
        self.assertEqual(p['activity'], 'searching')
        self.assertEqual(p['text_direction'], 'ltr')

    def test_arabic_rtl(self):
        p = ui_chat_payload(response='مرحباً', language='ar')
        self.assertEqual(p['text_direction'], 'rtl')

    def test_web_search_alias(self):
        self.assertEqual(normalize_source('web_search'), 'search')

    def test_gate_start_shape(self):
        p = ui_chat_payload(
            response='Hey! Is that you Omar?',
            language='en',
            source='gate',
            awaiting_owner_confirm=True,
            active_document=None,
        )
        self.assertIn('response', p)
        self.assertIn('language', p)
        self.assertIn('text_direction', p)
        self.assertTrue(p['awaiting_owner_confirm'])

    def test_browser_integration_fields(self):
        p = ui_chat_payload(
            response='It is 5°C in Stockholm.',
            language='en',
            source='search',
            activity='reading_page',
            browser_url='https://www.google.com/search?q=weather',
            search_query='weather Stockholm',
            page_title='Google Search',
            client_actions=[{'type': 'open_url', 'url': 'https://www.google.com/search?q=weather'}],
        )
        self.assertEqual(p['activity'], 'reading_page')
        self.assertEqual(p['browser_url'], p['opened_url'])
        self.assertEqual(p['search_query'], 'weather Stockholm')
        self.assertEqual(len(p['client_actions']), 1)


if __name__ == '__main__':
    unittest.main()
