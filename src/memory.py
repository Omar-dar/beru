import json
import os
from datetime import datetime

class TildMemory:
    def __init__(self, memory_path='data/memory.json'):
        self.memory_path = memory_path
        self.conversation_history = []
        self.corrections = []
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.corrections = data.get('corrections', [])
            print(f"Tild remembered {len(self.corrections)} corrections!")
        else:
            print("Tild starting with fresh memory!")

    def save_memory(self):
        data = {'corrections': self.corrections}
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_to_conversation(self, role, text):
        self.conversation_history.append({
            'role': role,
            'text': text,
            'time': datetime.now().isoformat()
        })
        # Keep last 10 exchanges only
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def get_context(self):
        if not self.conversation_history:
            return ""
        context = ""
        for msg in self.conversation_history[-6:]:
            if msg['role'] == 'human':
                context += f"### Human: {msg['text']}\n"
            else:
                context += f"### Tild: {msg['text']}\n"
        return context

    def add_correction(self, wrong_answer, correct_answer, question):
        correction = {
            'question': question,
            'wrong': wrong_answer,
            'correct': correct_answer,
            'time': datetime.now().isoformat()
        }
        self.corrections.append(correction)
        self.save_memory()

        # Also save to data.txt for future retraining
        with open('data/data.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n### Human: {question}\n### Tild: {correct_answer}\n")

        print(f"Tild learned: {question} → {correct_answer}")

    def is_correction(self, text):
        correction_words = [
            'no that', 'no thats', 'wrong', 'incorrect', 'not right',
            'that is wrong', 'that was wrong', 'you are wrong',
            'not correct', 'thats not', "that's not", 'no you',
            'nei det', 'nej det', 'fel',  # Swedish
            'لا', 'خطأ', 'غلط'  # Arabic
        ]
        text_lower = text.lower()
        return any(word in text_lower for word in correction_words)

    def extract_correction(self, text):
        # Remove correction words and get the correct answer
        remove_words = [
            'no that is wrong', 'no thats wrong', 'wrong',
            'incorrect', 'not right', 'that is wrong',
            'you are wrong', 'not correct', "that's not right",
            'no,', 'no '
        ]
        result = text.lower()
        for word in remove_words:
            result = result.replace(word, '')
        return result.strip()