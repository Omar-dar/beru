import unittest

from src.url_normalize import normalize_open_url


class UrlNormalizeTests(unittest.TestCase):
    def test_google_alias(self):
        self.assertEqual(normalize_open_url('Google'), 'https://www.google.com')

    def test_facebook_hemsida(self):
        self.assertEqual(
            normalize_open_url('Facebook hemsida'),
            'https://www.facebook.com',
        )

    def test_bare_name_gets_com(self):
        self.assertEqual(normalize_open_url('github'), 'https://github.com')

    def test_existing_domain(self):
        self.assertEqual(normalize_open_url('example.com'), 'https://example.com')

    def test_full_https(self):
        self.assertEqual(normalize_open_url('https://example.org'), 'https://example.org')

    def test_smhi_weather(self):
        self.assertEqual(normalize_open_url('väderhemsida'), 'https://www.smhi.se')


if __name__ == '__main__':
    unittest.main()
