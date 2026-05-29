import json
import os
from datetime import datetime

class TildMemory:
    def __init__(self, memory_path='data/memory.json'):
        self.memory_path = memory_path
        self.conversation_history = []
        self.corrections = []
        self.user = {}
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.corrections = data.get('corrections', [])
                self.user = data.get('user', {})
            print(f"Tild remembered {len(self.corrections)} corrections!")
            if self.user.get('name'):
                print(f"Tild remembers user: {self.user['name']}")
        else:
            self.user = {}
            print("Tild starting with fresh memory!")

    def save_memory(self):
        data = {
            'corrections': self.corrections,
            'user': self.user
        }
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_to_conversation(self, role, text):
        self.conversation_history.append({
            'role': role,
            'text': text,
            'time': datetime.now().isoformat()
        })
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
        correct_answer = correct_answer.strip('. ,\n')
        if not correct_answer:
            return

        correction = {
            'question': question,
            'wrong': wrong_answer,
            'correct': correct_answer,
            'time': datetime.now().isoformat()
        }
        self.corrections.append(correction)
        self.save_memory()

        with open('data/data.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n### Human: {question}\n### Tild: {correct_answer}\n")

        print(f"Tild learned: {question} → {correct_answer}")

    def is_correction(self, text):
        correction_words = [
            # English
            'no that', 'no thats', 'wrong', 'incorrect',
            'not right', 'that is wrong', 'that was wrong',
            'you are wrong', 'not correct', 'thats not',
            "that's not", 'no you', 'thats wrong',
            # Swedish
            'nei det', 'nej det', 'fel', 'felaktigt',
            'inte rätt', 'du har fel', 'det stämmer inte',
            'nej', 'fel svar', 'inte korrekt',
            # Arabic
            'لا', 'خطأ', 'غلط', 'مش صح',
            'ده غلط', 'هذا خطأ', 'لأ',
            'مش كده', 'انت غلطان', 'غير صحيح'
        ]
        text_lower = text.lower()
        return any(word in text_lower for word in correction_words)

    def extract_correction(self, text):
        remove_words = [
            'no that is wrong', 'no thats wrong',
            'that is wrong', 'that was wrong',
            'you are wrong', 'not correct',
            "that's not right", 'not right',
            'incorrect', 'wrong', 'remember,',
            'remember', 'no,', 'no ', 'please',
            'actually', 'instead', 'should be',
            'should say', 'you should',
        ]
        result = text.lower()
        for word in remove_words:
            result = result.replace(word, '')

        result = result.strip('. ,\n-')

        if result:
            result = result[0].upper() + result[1:]

        return result.strip()

    def set_user(self, name, language='en', notes=''):
        self.user = {
            'name': name,
            'language': language,
            'notes': notes,
            'verified': self.user.get('verified', False)
        }
        self.save_memory()
        print(f"Tild saved user: {name}")

    def get_user_name(self):
        return self.user.get('name', None)

    def is_known_user(self):
        return bool(self.user.get('name'))

    def is_omar(self):
        return self.user.get('name') == 'Omar' and self.user.get('verified', False)

    def is_verified(self):
        return self.user.get('verified', False)

    def get_tone(self):
        if self.is_omar():
            return 'bro'
        elif self.is_known_user():
            return 'friendly'
        else:
            return 'formal'

    def clear_session_user(self):
        # Clear only session data not persistent data
        self.user.pop('pending_name', None)
        self.user.pop('pending_language', None)
        self.save_memory()