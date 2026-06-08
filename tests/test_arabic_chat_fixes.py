"""Fixes from Khaled guest session log (corrections, Omar, search triggers)."""

import unittest

from src.memory import BeruMemory
from src.omar_questions import is_asking_about_omar_person, is_umrah_or_hajj_topic


class TestArabicChatFixes(unittest.TestCase):
    def test_la_in_alakhira_not_correction(self):
        mem = BeruMemory.__new__(BeruMemory)
        self.assertFalse(mem.is_correction('ما اسباب حرب غزة الاخيره'))

    def test_confirmation_not_correction(self):
        mem = BeruMemory.__new__(BeruMemory)
        self.assertTrue(mem.is_user_confirmation('يعني كلامي صح'))
        self.assertFalse(mem.is_correction('يعني كلامي صح'))

    def test_umrah_not_omar(self):
        self.assertTrue(is_umrah_or_hajj_topic('ممكن معلومات عن مناسك العمره'))
        self.assertFalse(is_asking_about_omar_person('ممكن معلومات عن مناسك العمره'))

    def test_who_is_omar_ar(self):
        self.assertTrue(is_asking_about_omar_person('من هو عمر'))
        self.assertTrue(is_asking_about_omar_person('من هو Omar Darwish'))

    def test_bad_correction_not_reused(self):
        mem = BeruMemory.__new__(BeruMemory)
        mem.corrections = [{
            'question': 'galaxy age',
            'wrong': 'wrong',
            'correct': 'هل تعلمين ان كل معلوماتك عن عمر خطأ',
        }]
        self.assertIsNone(mem.find_correction('من هو عمر'))


if __name__ == '__main__':
    unittest.main()
