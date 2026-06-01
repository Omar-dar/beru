"""Arabic identity gate: full name collection."""

import unittest

from chat.chat import detect_full_name, merge_partial_full_name
from src.language import detect_arabic_full_name, detect_arabic_name, is_arabic_name_meta_question


class TestArabicNameGate(unittest.TestCase):
    def test_arabic_full_name_plain(self):
        self.assertEqual(detect_arabic_full_name('خالد درويش'), 'خالد درويش')

    def test_arabic_full_name_three_parts(self):
        self.assertEqual(detect_arabic_full_name('خالد عيسي درويش'), 'خالد عيسي درويش')

    def test_arabic_intro_full(self):
        self.assertEqual(detect_arabic_full_name('اسمي خالد درويش'), 'خالد درويش')

    def test_mixed_latin_full(self):
        self.assertEqual(
            detect_arabic_full_name('اسمي بالكامل  Khaled Darwish'),
            'Khaled Darwish',
        )

    def test_detect_full_name_arabic(self):
        self.assertEqual(
            detect_full_name('خالد درويش', original_text='خالد درويش'),
            'خالد درويش',
        )

    def test_detect_name_single_only(self):
        self.assertEqual(detect_arabic_name('اسمي خالد'), 'خالد')
        self.assertIsNone(detect_arabic_name('اسمي خالد درويش'))

    def test_merge_partial_surname(self):
        merged = merge_partial_full_name('خالد', 'درويش', 'درويش')
        self.assertEqual(merged, 'خالد درويش')

    def test_meta_question(self):
        self.assertTrue(is_arabic_name_meta_question('ما ذا تقصد باسمي بالكامل'))

    def test_momken_ask_not_a_name(self):
        from src.language import detect_arabic_full_name, is_arabic_gate_chatter

        self.assertTrue(is_arabic_gate_chatter('ممكن اسالك'))
        self.assertIsNone(detect_arabic_full_name('ممكن اسالك'))

    def test_la_resolves_to_arabic(self):
        from src.language import resolve_turn_language

        self.assertEqual(
            resolve_turn_language('لا', session_language='en', in_gate=True),
            'ar',
        )

    def test_not_omar_negation(self):
        from src.language import is_arabic_negation, detect_arabic_full_name
        from src.memory import TildMemory

        self.assertTrue(is_arabic_negation('لست عمر'))
        self.assertIsNone(detect_arabic_full_name('لست عمر'))
        mem = TildMemory.__new__(TildMemory)
        self.assertTrue(mem.is_negative('لست عمر'))

    def test_name_intro_not_name_question(self):
        from src.language import is_arabic_name_intro_statement, is_name_intro_statement
        from src.memory import TildMemory

        self.assertTrue(is_arabic_name_intro_statement('اسمي خالد'))
        self.assertTrue(is_arabic_name_intro_statement('انا خالد'))
        self.assertTrue(is_name_intro_statement('my name is Khaled'))
        mem = TildMemory.__new__(TildMemory)
        self.assertFalse(mem.is_name_question('اسمي خالد'))
        self.assertFalse(mem.is_name_question('انا خالد'))


if __name__ == '__main__':
    unittest.main()
