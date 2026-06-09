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

CODE_GENERATION_TRIGGERS = [
    'write code', 'write me code', 'give me code', 'show me code', 'generate code',
    'code for', 'code to', 'need code', 'want code', 'create code', 'make code',
    'python script', 'javascript for', 'skriv kod', 'ge mig kod', 'generera kod',
    'hello world',
]

_CODE_LANG_PATTERN = re.compile(
    r'\b(write|show|give|create|just write|make)\b.{0,40}\b('
    r'java|python|javascript|typescript|c\+\+|c#|rust|go|kotlin|swift|ruby|php'
    r')\b',
    re.I,
)

CONVERSATION_REFERENCE_PHRASES = (
    'that code', 'this code', 'the code', 'your code', 'that script', 'this script',
    'what does it do', 'what does that do', 'what does this code', 'what does that code',
    'what do this code', 'what do that code', 'what is that code', 'what is this code',
    'explain that code', 'explain the code', 'explain this code', 'about the code',
    'about that code', 'the code you', 'code you wrote', 'code you just',
    'asking about the code', 'no the code', 'the code you wrote',
    'that letter', 'this letter', 'the letter you', 'what you wrote', 'what you just',
    'you wrote', 'you said', 'in that message', 'your last message', 'your reply',
    'den koden', 'vad gör den', 'vad gör koden', 'den koden du', 'förklara koden',
)

CODE_IN_REPLY_MARKERS = (
    '```', 'def ', 'import ', 'function ', 'class ', 'print(', 'return ',
)


def _recent_conversation_text(memory, max_messages=6):
    if not memory:
        return ''
    return ' '.join(m['text'] for m in memory.conversation_history[-max_messages:])


def _recent_beru_reply(memory):
    if not memory:
        return ''
    beru_msgs = [m['text'] for m in memory.conversation_history if m.get('role') == 'beru']
    return beru_msgs[-1] if beru_msgs else ''


def is_conversation_context_question(text, memory=None):
    """User is asking about something Beru just said or wrote — not the open web."""
    if is_code_explanation_request(text):
        return True
    if not memory or not memory.conversation_history:
        return False
    tl = text.lower().strip()
    if any(p in tl for p in CONVERSATION_REFERENCE_PHRASES):
        return True
    recent_beru = _recent_beru_reply(memory).lower()
    recent_all = _recent_conversation_text(memory).lower()
    has_code = any(m in recent_beru for m in CODE_IN_REPLY_MARKERS)
    has_letter = any(w in recent_all for w in ('dear ', 'letter', 'draft', 'brev'))
    if re.search(r'\b(it|that|this)\b', tl) and any(
        w in tl for w in ('do', 'does', 'mean', 'for', 'about', 'explain', 'what is', 'what does')
    ):
        if has_code or has_letter:
            return True
    if 'code' in tl and any(w in tl for w in ('that', 'this', 'your', 'explain', 'about', 'does', 'do')):
        if has_code:
            return True
    return False


def is_code_explanation_request(text):
    """User wants an explanation of code from chat (often pasted in the message)."""
    tl = text.lower().strip()
    if 'code' not in tl and not any(m in text for m in CODE_IN_REPLY_MARKERS):
        return False
    explain_markers = (
        'what does', 'what do', 'how does', 'how do', 'explain', 'mean', 'what is this',
        'what is that', 'tell me what', 'what?s this', "what's this",
    )
    if not any(m in tl for m in explain_markers):
        return False
    if any(m in text for m in CODE_IN_REPLY_MARKERS) or 'def ' in text or 'import ' in tl:
        return True
    if 'code' in tl:
        return True
    return False


def is_code_generation_request(text):
    text_lower = text.lower()
    if any(t in text_lower for t in CODE_GENERATION_TRIGGERS):
        if 'can you code' in text_lower or 'do you code' in text_lower:
            return False
        return True
    if _CODE_LANG_PATTERN.search(text_lower):
        return True
    if re.search(r'\b(code|kod)\b', text_lower):
        return any(
            v in text_lower
            for v in ('write', 'give', 'show', 'generate', 'create', 'make', 'need', 'want', 'skriv', 'ge mig')
        )
    return False


def is_creative_task(text, memory=None):
    text_lower = text.lower()
    if is_code_generation_request(text):
        return True
    if any(t in text_lower for t in CREATIVE_TRIGGERS):
        return True
    if any(w in text_lower for w in ('letter', 'draft', 'poem', 'story', 'essay', 'brev')):
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
    history = memory.conversation_history[-4:]
    if not history:
        return False

    recent = ' '.join(m['text'] for m in history).lower()
    has_code = any(m in recent for m in CODE_IN_REPLY_MARKERS) or '```' in recent
    has_letter = any(w in recent for w in ('letter', 'draft', 'write a letter', 'help you with writing'))

    if has_code or has_letter:
        if any(w in text_lower for w in FOLLOW_UP_WORDS):
            return True
        if is_conversation_context_question(text_lower, memory):
            return True
        if len(text_lower.split()) > 8:
            return True

    if any(text_lower.startswith(s) for s in (
        'what is ', 'what are ', 'who is ', 'how does ', 'how do ',
        'vad är ', 'vem är ', 'hur fungerar ', 'tell me about ',
    )):
        return False
    return False


def is_greeting_only(text):
    from src.language import is_arabic_greeting

    if is_arabic_greeting(text):
        return True
    words = set(re.findall(r'\w+', text.lower())) - GREETING_WORDS
    return len(words) == 0


def is_factual_rag_candidate(text, memory):
    from src.language import is_arabic_text

    text_lower = text.lower()
    if is_conversation_context_question(text, memory):
        return False
    if is_creative_task(text, memory) or is_conversational(text, memory):
        return False
    if memory and memory.knowledge.should_block_search(text, memory.is_owner()):
        return False
    if is_arabic_text(text) and any(
        w in text for w in ('مجرة', 'معلومات', 'اسباب', 'أسباب', 'كأس', 'الحج', 'العمرة', 'متى')
    ):
        return False
    if any(t in text_lower for t in RAG_FACTUAL_TRIGGERS):
        return True
    factual_starts = ('what is ', 'what are ', 'who is ', 'how does ', 'vad är ', 'vem är ', 'hur fungerar ')
    if any(text_lower.startswith(s) for s in factual_starts):
        if not any(w in text_lower for w in ('letter', 'code', 'write', 'draft', 'friend', 'skriv')):
            return True
    return False


def should_use_search(text, memory):
    if is_conversation_context_question(text, memory):
        return False
    if is_creative_task(text, memory) or is_conversational(text, memory):
        return False
    if memory and memory.knowledge.should_block_search(text, memory.is_owner()):
        return False
    return True


def route_request(user_input, memory, is_analysis_fn=None, search=None):
    """
    Decide how Beru should answer:
    - memory: identity, Omar/Beru facts, corrections
    - brain: creative, conversational, reasoning
    - rag: high-confidence stored Q&A only
    - search: weather / general web facts
    - analysis: NER on long text
    """
    if is_conversation_context_question(user_input, memory):
        return ROUTE_BRAIN

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
