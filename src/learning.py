"""Persist conversation exchanges so Tild's RAG learns from Ollama and chat."""

import os
import re

CONVERSATION_DATA_PATH = 'data/conversation_data.txt'

MIN_QUESTION_LEN = 8
MIN_ANSWER_LEN = 40

# Do not train on identity gates, passwords, or tiny canned replies
SKIP_SOURCES = {'gate', 'correction'}

_GATE_MARKERS = (
    'what is the password',
    'what is your full name',
    'who am i talking to',
    'is that you',
    'wrong password',
    'say yes if you are',
)


def _normalize(text):
    return re.sub(r'\s+', ' ', (text or '').strip())


def is_learnable_exchange(question, answer, source):
    """Return True when this Q&A should be appended to Tild training data."""
    if source in SKIP_SOURCES:
        return False

    q = _normalize(question)
    a = _normalize(answer)
    if len(q) < MIN_QUESTION_LEN or len(a) < MIN_ANSWER_LEN:
        return False

    q_lower = q.lower()
    if any(marker in q_lower for marker in _GATE_MARKERS):
        return False

    # Prefer learning from Ollama (brain); also keep strong RAG/search hits
    if source not in ('brain', 'rag', 'search'):
        return False

    return True


def _pair_exists(path, question):
    """Avoid duplicate Human lines in conversation_data.txt."""
    if not os.path.exists(path):
        return False
    needle = f"### Human: {question}\n"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return needle in f.read()
    except OSError:
        return False


def append_conversation_pair(question, answer, path=CONVERSATION_DATA_PATH):
    """Append a Human/Tild pair to conversation_data.txt."""
    question = question.strip()
    answer = answer.strip()
    if not question or not answer:
        return False

    if _pair_exists(path, question):
        return False

    block = f"### Human: {question}\n### Tild: {answer}\n\n"
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(block)
    return True


def learn_from_exchange(question, answer, source, rag=None):
    """
    Save exchange to disk and refresh in-memory RAG.
    Ollama answers become retrievable by Tild's own RAG on the next question.
    """
    if not is_learnable_exchange(question, answer, source):
        return False

    saved = append_conversation_pair(question, answer)
    if saved and rag is not None:
        rag.add_pair(question, answer)
    return saved
