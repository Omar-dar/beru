from sentence_transformers import SentenceTransformer
import numpy as np
import re

from src.document_index import TildDocumentIndex


class TildRAG:

    def __init__(self, data_paths=None):

        if data_paths is None:
            data_paths = [

                'data/data.txt',
                'data/conversation_data.txt',
                'data/personality_data.txt'

            ]

        print("Loading Tild's memory...")

        self.model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
        

        self.questions = []
        self.answers = []

        for path in data_paths:

            try:
                self._load_data(path)

            except FileNotFoundError:

                print(
                    f"File not found: {path}"
                )

        self._encode_questions()

        self.document_index = TildDocumentIndex(self.model)

        print(
            f"Tild remembers "
            f"{len(self.questions)} things!"
        )


    def _load_data(self, path):

        with open(
            path,
            'r',
            encoding='utf8'
        ) as f:

            content = f.read()

        pairs = re.findall(

            r'### Human: (.+?)\n### Tild: (.+?)(?=\n### Human:|\Z)',

            content,

            re.DOTALL
        )

        for q, a in pairs:

            q = q.strip()
            a = a.strip()

            if len(q) < 2:
                continue

            self.questions.append(q)
            self.answers.append(a)


    def _encode_questions(self):

        self.embeddings = self.model.encode(

            self.questions,

            normalize_embeddings=True

        )


    def find_answer(

        self,
        query,
        threshold=0.80,
        quiet=False

    ):

        query_embedding = self.model.encode(

            [query],

            normalize_embeddings=True

        )


        similarities = np.dot(

            self.embeddings,

            query_embedding.T

        ).flatten()


        best_idx = np.argmax(
            similarities
        )


        best_score = float(

            similarities[
                best_idx
            ]

        )


        best_match = self.questions[
            best_idx
        ]


        if not quiet:
            print(
                "\nQUERY:", query,
                "\nMATCH:", best_match,
                "\nSCORE:", round(best_score, 2)
            )


        stopwords = {

    "vad",
    "är",
    "det",
    "du",
    "om",
    "hur",
    "jag",
    "kan",

     "i", 
     "på", 
     "den", 
     "här", 
     "där",
     "händer",
    "tror",
    "vet",
    "vill",

    "tycker",
    "tror",
    "gillar",
    "vet",

    "what",
    "is",
    "the",
    "do",
    "you",
    "about",

    "think",
    "like",
    "know"
}


        query_words = (

            set(

                re.findall(

                    r'\w+',

                    query.lower()

                )

            )

            - stopwords

        )


        match_words = (

            set(

                re.findall(

                    r'\w+',

                    best_match.lower()

                )

            )

            - stopwords

        )


        overlap = len(

            query_words
            &
            match_words

        )


        if not quiet:
            print(
                "QUERY WORDS:", query_words,
                "\nMATCH WORDS:", match_words,
                "\nOVERLAP:", overlap, "\n"
            )


        min_overlap = 2 if threshold >= 0.90 else 1

        if (
            best_score >= threshold
            and overlap >= min_overlap
        ):

            return (

                self.answers[
                    best_idx
                ],

                best_score

            )


        return (

            None,

            best_score

        )

    def add_pair(self, question, answer):
        """Append a Q&A pair to in-memory RAG (after disk write in learning.py)."""
        question = question.strip()
        answer = answer.strip()
        if not question or not answer:
            return False

        if question in self.questions:
            idx = self.questions.index(question)
            self.answers[idx] = answer
        else:
            self.questions.append(question)
            self.answers.append(answer)

        new_embedding = self.model.encode(
            [question],
            normalize_embeddings=True,
        )
        if hasattr(self, 'embeddings') and len(self.embeddings) > 0:
            self.embeddings = np.vstack([self.embeddings, new_embedding])
        else:
            self.embeddings = new_embedding
        return True