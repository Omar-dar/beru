import torch
import random
import re
import os
from dotenv import load_dotenv
from transformers import GPT2LMHeadModel, GPT2Tokenizer

from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.deep_brain import DeepBrain
from src.language import detect_language, resolve_turn_language
from src.router import (
    route_request, ROUTE_BRAIN, ROUTE_RAG, ROUTE_SEARCH, ROUTE_ANALYSIS,
)

load_dotenv()

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! I need to learn more about that.",
    "I do not have enough knowledge about that yet but I am always learning!",
]

FALLBACKS_AR = [
    "هذا سؤال مثير للاهتمام! لا أزال أتعلم عن هذا الموضوع.",
    "لست متأكداً من ذلك بعد. اسألني شيئاً آخر!",
]

FALLBACKS_SV = [
    "Det är en intressant fråga! Jag lär mig fortfarande.",
    "Jag är inte säker på det ännu. Fråga mig något annat!",
    "Bra fråga! Jag behöver lära mig mer om det.",
    "Jag vet inte tillräckligt om det ännu men jag lär mig hela tiden!",
]

PROTECTED_USERS = {
    "Omar": os.getenv("TILD_OMAR_PASSWORD", "tild123")
}


def load_tild():
    print("Loading Tild's brain...")
    tokenizer = GPT2Tokenizer.from_pretrained("models/tild_v2")
    model = GPT2LMHeadModel.from_pretrained("models/tild_v2")
    model.eval()
    return model, tokenizer


def is_good_response(response):
    if len(response) < 3:
        return False
    if len(response.split()) < 2:
        return False
    if "###" in response:
        return False
    if len(set(response.split())) < 2:
        return False
    return True


def detect_name(user_input_lower):
    from src.memory import GREETING_WORDS, OWNER_NAME, TildMemory

    if looks_like_question(user_input_lower):
        return None

    if TildMemory.looks_like_yes_or_no(user_input_lower):
        return None

    if 'omar darwish' in user_input_lower:
        return OWNER_NAME

    skip_words = {
        "a", "an", "the", "not", "no", "yes", "ok", "okay",
        "here", "sure", "good", "bad", "just", "only", "also",
        "very", "really", "so", "too", "up", "out", "on",
        "tired", "happy", "sad", "bored", "stressed", "excited",
        "ledsen", "glad", "arg", "trött", "stressad", "sjuk",
        "inte", "telling", "trying", "going", "doing", "thinking",
        "working", "talking", "asking", "saying", "looking",
        "coming", "getting", "having", "making", "taking",
        "serious", "kidding", "joking", "back", "home", "new",
        "old", "big", "small", "right", "wrong", "late", "early",
    } | GREETING_WORDS

    ignore_phrases = [
        "jag är inte",
        "mitt namn är inte",
        "my name is not",
        "i am not",
        "i am just",
        "i am so",
        "i am very",
        "i am really",
        "i am back",
        "i am here",
        "i am new",
        "i am trying",
        "i am telling",
        "i am going",
        "i am doing",
        "i am thinking",
        "i am working",
        "i am looking",
        "i am getting",
        "i am having",
        "i am having", "i am here to",      
        "i am happy to",                      
        "i am glad to",                        
        "i am able to",                        
        "i am trying to",                   
    ]

    if any(phrase in user_input_lower for phrase in ignore_phrases):
        return None

    name_patterns = [
        r"i am (\w+)",
        r"i'm (\w+)",
        r"im (\w+)",
        r"my name is (\w+)",
        r"jag heter (\w+)",
        r"mitt namn är (\w+)",
        r"this is (\w+)",
        r"(\w+) here",
        r"(\w+) speaking",
        r"it is (\w+)",
        r"its (\w+)",
        r"jag är (\w+)",
        r"det är (\w+)",
        r"call me (\w+)",
        r"kalla mig (\w+)",
        r"^(\w+)$",  # just a single word like "Omar"
        r"yes it is (\w+)",
        r"yes i am (\w+)",
        r"it is me (\w+)",
        r"talking to (\w+)",
        r"this is (\w+)",
        r"(\w+) is here",
        r"(\w+) speaking",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in skip_words and len(name) > 1:
                return name

    return None


NAME_INTRO_PREFIXES = [
    r"^no,?\s+",
    r"^no it is\s+",
    r"^no i'm\s+",
    r"^no im\s+",
    r"^(?:i am|i'm|im|my name is|call me|this is|it is|it's|its|jag heter|mitt namn är|jag är|det är|kalla mig)\s+",
]

NAME_FILLER_WORDS = {
    "a", "an", "the", "not", "no", "yes", "ok", "okay", "it", "its", "it's",
    "is", "me", "here", "sure", "good", "bad", "just", "only", "also", "very",
    "really", "this", "that", "i", "im", "am", "my", "name", "call", "speaking",
    "what", "when", "where", "why", "how", "who", "which", "about", "document",
    "pdf", "file", "upload", "summarize", "summary", "tell", "explain", "describe",
    "main", "points", "page", "pages", "the", "does", "say", "mean", "your",
    "vet", "du", "vad", "jag", "gjorde", "gjort", "idag", "today", "know", "did",
    "have", "berätta", "kommer", "kan", "men", "och", "sen", "bara", "att",
}

QUESTION_STARTERS = (
    'what ', 'who ', 'where ', 'when ', 'why ', 'how ', 'which ', 'can ', 'could ',
    'would ', 'should ', 'is ', 'are ', 'do ', 'does ', 'did ', 'will ', 'tell me',
    'explain ', 'describe ', 'summarize', 'summarise', 'list ', 'show me',
    'vad ', 'vem ', 'hur ', 'när ', 'varför ', 'kan du', 'berätta', 'vet du',
    'do you know', 'know what',
)

QUESTION_PHRASES = (
    'vet du vad', 'kan du', 'do you know', 'what did i', 'what have i',
    'vad gjorde jag', 'vad har jag gjort', 'gjorde jag idag', 'gjort jag idag',
    'vad jag gjorde', 'what i did today', 'did i do today',
)


def looks_like_question(text_lower):
    """Avoid treating questions as person names during identity gate."""
    text = text_lower.strip().strip('.!,')
    if not text:
        return False
    if text.endswith('?'):
        return True
    if any(text.startswith(s) for s in QUESTION_STARTERS):
        return True
    if any(p in text for p in QUESTION_PHRASES):
        return True
    try:
        from src.document_index import TildDocumentIndex
        if TildDocumentIndex.is_document_question(text):
            return True
    except Exception:
        pass
    return False


def _strip_name_intro(text_lower):
    text = text_lower.strip().strip('.!,')
    for prefix in NAME_INTRO_PREFIXES:
        text = re.sub(prefix, '', text, count=1)
    return text.strip()


def _title_name_words(words):
    return ' '.join(w.capitalize() for w in words)


def is_valid_full_name(full_name):
    words = full_name.lower().split()
    if len(words) < 2:
        return False
    return not any(w in NAME_FILLER_WORDS for w in words)


def detect_full_name(user_input_lower):
    """Detect a multi-word full name from user input."""
    from src.memory import GREETING_WORDS, OWNER_NAME

    if looks_like_question(user_input_lower):
        return None

    if 'omar darwish' in user_input_lower:
        return OWNER_NAME + ' Darwish'

    skip_words = NAME_FILLER_WORDS | GREETING_WORDS
    stripped = _strip_name_intro(user_input_lower)
    words = [w for w in stripped.split() if w not in skip_words and len(w) > 1]

    if len(words) >= 2:
        full_name = _title_name_words(words)
        if is_valid_full_name(full_name):
            return full_name

    return None


def is_analysis_request(text):
    analysis_triggers = [
        "analysera", "analyse", "analyze", "hitta", "find",
        "identifiera", "identify", "vilka personer", "who is mentioned",
        "vem nämns", "tidslinje", "timeline", "samband", "connections",
        "mönster", "pattern", "sammanfatta", "summarize", "summera"
    ]
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in analysis_triggers)


def try_remember_from_document(user_input, rag, memory, brain, language):
    """Save facts from the active PDF into Omar's memory."""
    index = getattr(rag, 'document_index', None)
    if not brain or not index or not memory.is_owner():
        return None
    if not index.is_remember_from_document_intent(user_input):
        return None

    doc_id = index.resolve_document_id(memory)
    if not doc_id:
        if language == 'sv':
            return 'Ladda upp PDF:en först bro, sen kan jag spara info från den.', 'document'
        return 'Upload the PDF first bro, then I can save info from it.', 'document'

    print(f"[Document remember: doc={doc_id}]")
    return memory.remember_facts_from_document(
        brain, index, doc_id, language
    ), 'document'


def try_answer_from_document(user_input, rag, memory, brain, language, tone):
    """Answer using uploaded PDF chunks when a document is active in the session."""
    if not brain or not getattr(rag, 'document_index', None):
        return None

    index = rag.document_index
    is_doc_q = index.is_document_question(user_input)
    doc_id = index.resolve_document_id(memory)

    if not doc_id:
        if is_doc_q:
            if language == 'sv':
                return 'Ladda upp en PDF först bro, sen kan jag svara om den.', 'document'
            return 'Upload a PDF first bro, then I can answer questions about it.', 'document'
        return None

    if not is_doc_q:
        hits = index.search(user_input, doc_id=doc_id, top_k=5)
        if not hits or hits[0]['score'] < 0.32:
            return None
    else:
        hits = index.chunks_for_document(doc_id)

    if not hits:
        name = memory.get_active_document_name() or 'the document'
        if language == 'sv':
            return f'Jag har inget indexerat innehåll i {name} ännu.', 'document'
        return f"I have no indexed content in {name} yet.", 'document'

    context = index.format_context(hits, language=language)
    print(f"[Document RAG: {len(hits)} chunk(s), doc={doc_id}, doc_q={is_doc_q}]")
    return brain.ask(
        user_input, language, tone=tone, memory=memory, document_context=context
    ), 'document'


def get_response(
    model,
    tokenizer,
    rag,
    memory,
    search,
    ner,
    user_input,
    language="en",
    brain=None,
    *,
    language_hint=None,
):
    """Return (response_text, source) where source tracks how the answer was produced."""
    in_gate = (
        not memory.is_session_identified()
        or memory.get_pending_name()
        or memory.is_awaiting_full_name()
        or memory.is_awaiting_disambiguation()
    )
    language = resolve_turn_language(
        user_input,
        hint=language_hint,
        session_language=memory.session.get('language'),
        in_gate=in_gate,
    )
    memory.session['language'] = language
    user_input_lower = user_input.lower()
    tone = memory.get_tone()

    # Password check for protected users (e.g. Omar)
    pending_name = memory.get_pending_name()
    if pending_name:
        pending_language = memory.session.get("pending_language", "en")

        stored = PROTECTED_USERS.get(pending_name)
        if stored and TildMemory.passwords_match(user_input, stored):
            memory.clear_pending_name()
            if pending_name == "Omar":
                memory.mark_as_owner(pending_language)
                return memory.owner_greeting(pending_language), 'gate'

            memory.set_user(pending_name, pending_language)
            return memory.formal_greeting(pending_name, pending_language), 'gate'

        memory.clear_pending_name()
        if language == "sv":
            return "Fel lösenord! Jag kan inte verifiera din identitet. Vem är du?", 'gate'
        return "Wrong password! I cannot verify your identity. Who are you?", 'gate'

    # Must know who is talking before anything else
    if not memory.is_session_identified():
        if memory.is_today_activity_question(user_input):
            return memory.respond_today_question_before_identify(language), 'gate'

        # Waiting for user to disambiguate duplicate full names
        if memory.is_awaiting_disambiguation():
            matched_id = memory.resolve_disambiguation(user_input)
            if matched_id:
                memory.confirm_disambiguation(matched_id, language)
                return memory.welcome_back_greeting(matched_id, language), 'gate'
            return memory.ask_disambiguation_retry(language), 'gate'

        # Waiting for full name after first name only
        if memory.is_awaiting_full_name():
            full_name = detect_full_name(user_input_lower)
            if full_name and len(full_name.split()) >= 2:
                memory.session['awaiting_full_name'] = False
                return memory.handle_guest_registration(full_name, language), 'gate'

            partial = memory.session.get('partial_first_name')
            single = detect_name(user_input_lower)
            if single and not partial:
                memory.begin_full_name_collection(partial_first_name=single, language=language)
                return memory.ask_full_name(language, partial_first_name=single), 'gate'
            return memory.ask_full_name(language, partial_first_name=partial), 'gate'

        # Waiting for Omar to confirm identity
        if memory.is_awaiting_owner_confirm():
            detected_name = detect_name(user_input_lower)
            full_name = detect_full_name(user_input_lower)

            if memory.is_affirmative(user_input) or detected_name == 'Omar':
                memory.clear_awaiting_owner_confirm()
                memory.set_pending_name('Omar', language)
                return memory.ask_owner_password(language), 'gate'

            if memory.is_negative(user_input):
                memory.clear_awaiting_owner_confirm()
                return memory.ask_to_identify(language), 'gate'

            if full_name and detected_name != 'Omar':
                if looks_like_question(user_input_lower):
                    return memory.ask_owner_confirm_again(language), 'gate'
                memory.clear_awaiting_owner_confirm()
                return memory.handle_guest_registration(full_name, language), 'gate'

            if detected_name and detected_name != 'Omar':
                memory.clear_awaiting_owner_confirm()
                memory.begin_full_name_collection(partial_first_name=detected_name, language=language)
                return memory.ask_full_name(language, partial_first_name=detected_name), 'gate'

            return memory.ask_owner_confirm_again(language), 'gate'

        full_name = detect_full_name(user_input_lower)
        detected_name = detect_name(user_input_lower)

        if detected_name in PROTECTED_USERS:
            memory.set_pending_name(detected_name, language)
            if language == "sv":
                return f"Hej! Jag känner igen namnet {detected_name}. Vad är lösenordet?", 'gate'
            return f"Hey! I recognize the name {detected_name}. What is the password?", 'gate'

        if full_name and len(full_name.split()) >= 2 and detected_name != 'Omar':
            if looks_like_question(user_input_lower):
                return memory.ask_to_identify(language), 'gate'
            return memory.handle_guest_registration(full_name, language), 'gate'

        if detected_name and detected_name != 'Omar':
            memory.begin_full_name_collection(partial_first_name=detected_name, language=language)
            return memory.ask_full_name(language, partial_first_name=detected_name), 'gate'

        return memory.ask_to_identify(language), 'gate'

    # PDF document questions — before generic handlers (avoid brain hallucinating Tild rules)
    index = getattr(rag, 'document_index', None)
    if index and index.is_pre_upload_document_intent(user_input):
        return memory.answer_pre_upload_document_intent(language), 'memory'

    remember_answer = try_remember_from_document(
        user_input, rag, memory, brain, language
    )
    if remember_answer:
        return remember_answer

    doc_answer = try_answer_from_document(
        user_input, rag, memory, brain, language, tone
    )
    if doc_answer:
        return doc_answer

    # Identity and name questions
    if memory.is_time_question(user_input):
        return memory.answer_time_question(language), 'memory'

    if memory.is_conversation_partner_question(user_input):
        return memory.answer_conversation_partner(language), 'memory'

    if memory.is_owner_today_question(user_input):
        return memory.answer_owner_today_question(language), 'memory'

    if memory.is_owner() and memory.is_owner_day_chat_followup(user_input):
        return memory.answer_owner_day_chat_followup(user_input, language), 'memory'

    if memory.is_owner() and memory.is_owner_today_narration(user_input):
        return memory.handle_owner_today_narration(user_input, language), 'memory'

    if memory.is_owner_profile_short_request(user_input):
        return memory.answer_owner_profile_short(language), 'memory'

    if memory.is_owner() and memory.is_date_clarification(user_input):
        return memory.handle_date_clarification(user_input, language), 'memory'

    if memory.is_identity_question(user_input):
        return memory.answer_identity(language), 'memory'

    if memory.is_name_question(user_input):
        return memory.answer_name_question(language), 'memory'

    if memory.is_trust_question(user_input):
        return memory.answer_trust_question(language), 'memory'

    if memory.is_memory_question(user_input):
        return memory.answer_memory_question(language), 'memory'

    if memory.is_past_conversation_question(user_input):
        return memory.answer_past_conversation_question(language), 'memory'

    if memory.is_owner_users_question(user_input):
        return memory.answer_owner_users_question(user_input, language), 'memory'

    if memory.is_owner():
        if memory.is_omar_forget_instruction(user_input):
            return memory.handle_forget_instruction(user_input, language), 'memory'
        if memory.is_omar_remember_instruction(user_input):
            return memory.handle_remember_instruction(user_input, language), 'memory'
        if memory.is_omar_recall_instructions(user_input):
            return memory.answer_omar_recall_instructions(language), 'memory'

    if memory.is_asking_about_self(user_input):
        return memory.answer_about_self(language), 'memory'

    if memory.is_asking_about_other_person(user_input):
        return memory.answer_about_other_person(user_input, language), 'memory'

    if memory.is_casual_conversation_reply(user_input):
        return memory.answer_casual_reply(language), 'memory'

    if memory.is_tild_activity_question(user_input):
        return memory.answer_tild_activity_question(language), 'memory'

    if memory.is_tild_experience_question(user_input):
        return memory.answer_tild_experience_question(language), 'memory'

    # Permanent knowledge — Tild identity and Omar facts
    knowledge_answer = memory.answer_from_knowledge(user_input, language)
    if knowledge_answer:
        print("[Knowledge memory used]")
        return knowledge_answer, 'knowledge'

    # Correction check
    if memory.is_correction(user_input):
        last_exchange = [m for m in memory.conversation_history if m["role"] == "tild"]
        last_question = [m for m in memory.conversation_history if m["role"] == "human"]

        if last_exchange and last_question:
            wrong_answer = last_exchange[-1]["text"]
            question = last_question[-2]["text"] if len(last_question) >= 2 else last_question[-1]["text"]
            correct = memory.extract_correction(user_input)

            if correct:
                memory.add_correction(wrong_answer, correct, question)
                if memory.is_owner():
                    memory.add_omar_fact(correct)
                if language == "sv":
                    return "Tack för korrigeringen! Jag kommer att komma ihåg det.", 'correction'
                if language == "ar":
                    return "شكراً على التصحيح! سأتذكر ذلك.", 'correction'
                return "Thank you for correcting me! I will remember that.", 'correction'

            if language == "sv":
                return "Jag förstår att jag hade fel! Kan du berätta det rätta svaret?", 'correction'
            if language == "ar":
                return "أفهم أنني كنت مخطئاً! هل يمكنك إخباري بالإجابة الصحيحة؟", 'correction'
            return "I understand I was wrong! Can you tell me the correct answer?", 'correction'

    correction_answer = memory.find_correction(user_input)
    if correction_answer:
        return correction_answer, 'memory'

    # Router — decide memory vs RAG vs search vs deep brain
    route = route_request(user_input, memory, is_analysis_fn=is_analysis_request, search=search)

    if route == ROUTE_ANALYSIS:
        rag_answer, score = rag.find_answer(user_input, threshold=0.92, quiet=True)
        if rag_answer and score >= 0.92:
            print(f"[RAG match: {score:.2f}]")
            return rag_answer, 'rag'
        entities = ner.extract_entities(user_input)
        if entities["persons"] or entities["places"] or entities["dates"]:
            print("[Entity recognition used]")
            return ner.format_entities(entities, language), 'analysis'

    if route == ROUTE_SEARCH:
        print("[Searching internet...]")
        result = search.search(user_input)
        if result:
            result = re.sub(r"\[\d+\]", "", result).strip()
            if len(result) > 150:
                result = result[:150] + "..."
            print(f"[Found: {result[:50]}...]")
            return search.format_response(result, user_input), 'search'
        if language == "sv":
            return "Jag försökte söka efter det men kunde inte ansluta just nu.", 'search'
        if language == "ar":
            return "حاولت البحث لكن لم أتمكن من الاتصال الآن.", 'search'
        return "I tried searching for that but could not connect right now.", 'search'

    if route == ROUTE_RAG:
        rag_answer, score = rag.find_answer(user_input, threshold=0.92)
        if rag_answer and score >= 0.92:
            print(f"[RAG match: {score:.2f}]")
            return rag_answer, 'rag'
        route = ROUTE_BRAIN

    if route == ROUTE_BRAIN and brain:
        print("[Tild thinking...]")
        document_context = ""
        index = getattr(rag, 'document_index', None)
        if index and memory:
            doc_id = index.resolve_document_id(memory)
            if doc_id and index.is_document_question(user_input):
                hits = index.chunks_for_document(doc_id)
                if hits:
                    document_context = index.format_context(hits, language=language)
            elif doc_id:
                hits = index.search(user_input, doc_id=doc_id, top_k=3, min_score=0.28)
                if hits:
                    document_context = index.format_context(hits, language=language)
        return brain.ask(
            user_input, language, tone=tone, memory=memory, document_context=document_context
        ), 'brain'

    if language == "ar":
        return random.choice(FALLBACKS_AR), 'fallback'
    if language == "sv":
        return random.choice(FALLBACKS_SV), 'fallback'
    return random.choice(FALLBACKS), 'fallback'


def chat():
    from src.pipeline import TildPipeline

    pipeline = TildPipeline()

    greeting = pipeline.start_session(clear_history=False)
    print(f"Tild: {greeting}\n")
    print("Type your message (or 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            if pipeline.memory.is_owner():
                print("Tild: Vi ses bro!")
            elif pipeline.memory.is_session_identified():
                print("Tild: Goodbye! It was great talking with you.")
            else:
                print("Tild: Goodbye!")
            break

        result = pipeline.chat_turn(user_input, format_for_ui=False)
        print(f"Tild: {result['response']}\n")


if __name__ == "__main__":
    chat()