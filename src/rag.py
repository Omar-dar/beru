from sentence_transformers import SentenceTransformer
import numpy as np
import re

class TildRAG:
    def __init__(self, data_path='data/data.txt'):
        print("Loading Tild's memory...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.questions = []
        self.answers = []
        self._load_data(data_path)
        self._encode_questions()
        print(f"Tild remembers {len(self.questions)} things!")

    def _load_data(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        pairs = re.findall(
            r'### Human: (.+?)\n### Tild: (.+?)(?=\n### Human:|\Z)',
            content,
            re.DOTALL
        )

        for question, answer in pairs:
            self.questions.append(question.strip())
            self.answers.append(answer.strip())

    def _encode_questions(self):
        self.embeddings = self.model.encode(self.questions)

    def find_answer(self, query, threshold=0.65):
        query_embedding = self.model.encode([query])
        
        # Calculate similarity
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        if best_score >= threshold:
            return self.answers[best_idx], best_score
        return None, best_score