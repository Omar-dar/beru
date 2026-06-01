import re

from src.memory import GREETING_WORDS

ROUTE_MEMORY = 'memory'
ROUTE_BRAIN = 'brain'
ROUTE_RAG = 'rag'
ROUTE_SEARCH = 'search'
ROUTE_ANALYSIS = 'analysis'

CREATIVE_TRIGGERS = [
    'write a letter', 'write me a letter', 'write letter', 'draft a letter',
    'write code', 'write me code', 'generate code', 'coding', 'python script',
    'give me code', 'give me anything', 'brainstorm', 'come up with', 'imagine',
    'poem', 'story', 'essay', 'help me write', 'can you write',
    'skriv ett brev', 'skriv brev', 'skriv kod', 'generera kod',
    'help me with a letter', 'full letter', 'complete letter',
]

CONVERSATIONAL_TRIGGERS = [
    'what do you think', 'how do you feel', 'tell me more', 'explain more',
    'continue', 'go on', 'keep going', 'add more', 'make it longer',
    'what about', 'why do you', 'how would you', 'could you help me',
    'give me an idea', 'any ideas', 'suggest', 'recommend',
]

RAG_FACTUAL_TRIGGERS = [
    'what is python', 'what is pytorch', 'what is git', 'what is github',
    'what is a transformer', 'what is machine learning', 'what is ai',
    'how do i learn', 'how to learn programming', 'how to train',
    'vad är python', 'vad är pytorch', 'hur lär jag mig',
]

FOLLOW_UP_WORDS = {
    'letter', 'draft', 'code', 'friend', 'maja', 'tone', 'close', 'happy',
    'more text', 'add more', 'continue', 'brev', 'kod',
}


def is_creative_task(text, memory=None):
    text_lower = text.lower()
    if any(t in text_lower for t in CREATIVE_TRIGGERS):
        return True
    if any(w in text_lower for w in ('letter', 'draft', 'poem', 'story', 'essay', 'brev', 'kod')):
        return True
    if memory and _is_conversation_follow_up(text_lower, memory):
        return True
    return False


def is_conversational(text, memory=None):
    text_lower = text.lower()
    if memory and hasattr(memory, 'is_owner_day_chat_followup'):
        if memory.is_owner_day_chat_followup(text):
            return False
    if any(t in text_lower for t in CONVERSATIONAL_TRIGGERS):
        return True
    if memory and memory.is_casual_conversation_reply(text):
        return True
    words = set(re.findall(r'\w+', text_lower)) - GREETING_WORDS
    if len(words) <= 2 and memory and memory.is_session_identified():
        return True
    if memory and _is_conversation_follow_up(text_lower, memory):
        return True
    return False


def _is_conversation_follow_up(text_lower, memory):
    if any(text_lower.startswith(s) for s in (
        'what is ', 'what are ', 'who is ', 'how does ', 'how do ',
        'vad är ', 'vem är ', 'hur fungerar ', 'tell me about ',
    )):
        return False

    history = memory.conversation_history[-4:]
    if not history:
        return False

    recent = ' '.join(m['text'] for m in history).lower()

    if any(w in recent for w in ('letter', 'draft', 'write a letter', 'help you with writing', 'code snippet')):
        if any(w in text_lower for w in FOLLOW_UP_WORDS):
            return True
        if len(text_lower.split()) > 8:
            return True
    return False


def is_greeting_only(text):
    words = set(re.findall(r'\w+', text.lower())) - GREETING_WORDS
    return len(words) == 0


def is_factual_rag_candidate(text, memory):
    text_lower = text.lower()
    if is_creative_task(text, memory) or is_conversational(text, memory):
        return False
    if memory and memory.knowledge.should_block_search(text, memory.is_owner()):
        return False
    if any(t in text_lower for t in RAG_FACTUAL_TRIGGERS):
        return True
    factual_starts = ('what is ', 'what are ', 'who is ', 'how does ', 'vad är ', 'vem är ', 'hur fungerar ')
    if any(text_lower.startswith(s) for s in factual_starts):
        if not any(w in text_lower for w in ('letter', 'code', 'write', 'draft', 'friend', 'skriv')):
            return True
    return False


def should_use_search(text, memory):
    if is_creative_task(text, memory) or is_conversational(text, memory):
        return False
    if memory and memory.knowledge.should_block_search(text, memory.is_owner()):
        return False
    return True


def route_request(user_input, memory, is_analysis_fn=None, search=None):
    """
    Decide how Tild should answer:
    - memory: identity, Omar/Tild facts, corrections
    - brain: creative, conversational, reasoning
    - rag: high-confidence stored Q&A only
    - search: weather / general web facts
    - analysis: NER on long text
    """
    if is_creative_task(user_input, memory):
        return ROUTE_BRAIN

    if is_conversational(user_input, memory):
        return ROUTE_BRAIN

    if is_greeting_only(user_input):
        return ROUTE_BRAIN

    if is_analysis_fn and len(user_input.split()) > 8 and is_analysis_fn(user_input):
        return ROUTE_ANALYSIS

    if is_factual_rag_candidate(user_input, memory):
        return ROUTE_RAG

    if search and should_use_search(user_input, memory):
        if search.should_search(user_input, memory=memory):
            return ROUTE_SEARCH

    return ROUTE_BRAIN
