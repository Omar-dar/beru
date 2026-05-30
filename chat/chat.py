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
from src.language import detect_language
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
}


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


def get_response(model, tokenizer, rag, memory, search, ner, user_input, language="en", brain=None):
    language = detect_language(user_input)
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
                return memory.owner_greeting(pending_language)

            memory.set_user(pending_name, pending_language)
            return memory.formal_greeting(pending_name, pending_language)

        memory.clear_pending_name()
        if language == "sv":
            return "Fel lösenord! Jag kan inte verifiera din identitet. Vem är du?"
        return "Wrong password! I cannot verify your identity. Who are you?"

    # Must know who is talking before anything else
    if not memory.is_session_identified():
        # Waiting for user to disambiguate duplicate full names
        if memory.is_awaiting_disambiguation():
            matched_id = memory.resolve_disambiguation(user_input)
            if matched_id:
                memory.confirm_disambiguation(matched_id, language)
                return memory.welcome_back_greeting(matched_id, language)
            return memory.ask_disambiguation_retry(language)

        # Waiting for full name after first name only
        if memory.is_awaiting_full_name():
            full_name = detect_full_name(user_input_lower)
            if full_name and len(full_name.split()) >= 2:
                memory.session['awaiting_full_name'] = False
                return memory.handle_guest_registration(full_name, language)

            partial = memory.session.get('partial_first_name')
            single = detect_name(user_input_lower)
            if single and not partial:
                memory.begin_full_name_collection(partial_first_name=single, language=language)
                return memory.ask_full_name(language, partial_first_name=single)
            return memory.ask_full_name(language, partial_first_name=partial)

        # Waiting for Omar to confirm identity
        if memory.is_awaiting_owner_confirm():
            detected_name = detect_name(user_input_lower)
            full_name = detect_full_name(user_input_lower)

            if memory.is_affirmative(user_input) or detected_name == 'Omar':
                memory.clear_awaiting_owner_confirm()
                memory.set_pending_name('Omar', language)
                return memory.ask_owner_password(language)

            if memory.is_negative(user_input):
                memory.clear_awaiting_owner_confirm()
                return memory.ask_to_identify(language)

            if full_name and detected_name != 'Omar':
                memory.clear_awaiting_owner_confirm()
                return memory.handle_guest_registration(full_name, language)

            if detected_name and detected_name != 'Omar':
                memory.clear_awaiting_owner_confirm()
                memory.begin_full_name_collection(partial_first_name=detected_name, language=language)
                return memory.ask_full_name(language, partial_first_name=detected_name)

            return memory.ask_owner_confirm_again(language)

        full_name = detect_full_name(user_input_lower)
        detected_name = detect_name(user_input_lower)

        if detected_name in PROTECTED_USERS:
            memory.set_pending_name(detected_name, language)
            if language == "sv":
                return f"Hej! Jag känner igen namnet {detected_name}. Vad är lösenordet?"
            return f"Hey! I recognize the name {detected_name}. What is the password?"

        if full_name and len(full_name.split()) >= 2 and detected_name != 'Omar':
            return memory.handle_guest_registration(full_name, language)

        if detected_name and detected_name != 'Omar':
            memory.begin_full_name_collection(partial_first_name=detected_name, language=language)
            return memory.ask_full_name(language, partial_first_name=detected_name)

        return memory.ask_to_identify(language)

    # Identity and name questions
    if memory.is_identity_question(user_input):
        return memory.answer_identity(language)

    if memory.is_name_question(user_input):
        return memory.answer_name_question(language)

    if memory.is_trust_question(user_input):
        return memory.answer_trust_question(language)

    if memory.is_memory_question(user_input):
        return memory.answer_memory_question(language)

    if memory.is_past_conversation_question(user_input):
        return memory.answer_past_conversation_question(language)

    if memory.is_owner_users_question(user_input):
        return memory.answer_owner_users_question(user_input, language)

    if memory.is_owner():
        if memory.is_omar_forget_instruction(user_input):
            return memory.handle_forget_instruction(user_input, language)
        if memory.is_omar_remember_instruction(user_input):
            return memory.handle_remember_instruction(user_input, language)
        if memory.is_omar_recall_instructions(user_input):
            return memory.answer_omar_recall_instructions(language)

    if memory.is_asking_about_self(user_input):
        return memory.answer_about_self(language)

    if memory.is_asking_about_other_person(user_input):
        return memory.answer_about_other_person(user_input, language)

    if memory.is_casual_conversation_reply(user_input):
        return memory.answer_casual_reply(language)

    # Permanent knowledge — Tild identity and Omar facts
    knowledge_answer = memory.answer_from_knowledge(user_input, language)
    if knowledge_answer:
        print("[Knowledge memory used]")
        return knowledge_answer

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
                    return "Tack för korrigeringen! Jag kommer att komma ihåg det."
                if language == "ar":
                    return "شكراً على التصحيح! سأتذكر ذلك."
                return "Thank you for correcting me! I will remember that."

            if language == "sv":
                return "Jag förstår att jag hade fel! Kan du berätta det rätta svaret?"
            if language == "ar":
                return "أفهم أنني كنت مخطئاً! هل يمكنك إخباري بالإجابة الصحيحة؟"
            return "I understand I was wrong! Can you tell me the correct answer?"

    correction_answer = memory.find_correction(user_input)
    if correction_answer:
        return correction_answer

    # Router — decide memory vs RAG vs search vs deep brain
    route = route_request(user_input, memory, is_analysis_fn=is_analysis_request, search=search)

    if route == ROUTE_ANALYSIS:
        rag_answer, score = rag.find_answer(user_input, threshold=0.92, quiet=True)
        if rag_answer and score >= 0.92:
            print(f"[RAG match: {score:.2f}]")
            return rag_answer
        entities = ner.extract_entities(user_input)
        if entities["persons"] or entities["places"] or entities["dates"]:
            print("[Entity recognition used]")
            return ner.format_entities(entities, language)

    if route == ROUTE_SEARCH:
        print("[Searching internet...]")
        result = search.search(user_input)
        if result:
            result = re.sub(r"\[\d+\]", "", result).strip()
            if len(result) > 150:
                result = result[:150] + "..."
            print(f"[Found: {result[:50]}...]")
            return search.format_response(result, user_input)
        if language == "sv":
            return "Jag försökte söka efter det men kunde inte ansluta just nu."
        if language == "ar":
            return "حاولت البحث لكن لم أتمكن من الاتصال الآن."
        return "I tried searching for that but could not connect right now."

    if route == ROUTE_RAG:
        rag_answer, score = rag.find_answer(user_input, threshold=0.92)
        if rag_answer and score >= 0.92:
            print(f"[RAG match: {score:.2f}]")
            return rag_answer
        route = ROUTE_BRAIN

    if route == ROUTE_BRAIN and brain:
        print("[Tild thinking...]")
        return brain.ask(user_input, language, tone=tone, memory=memory)

    if language == "ar":
        return random.choice(FALLBACKS_AR)
    if language == "sv":
        return random.choice(FALLBACKS_SV)
    return random.choice(FALLBACKS)


def chat():
    model, tokenizer = load_tild()
    rag = TildRAG()
    memory = TildMemory()
    search = TildSearch()
    ner = TildEntityRecognizer()
    brain = DeepBrain()

    greeting = memory.greeting_for_session()
    print(f"Tild: {greeting}\n")
    print("Type your message (or 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "quit":
            if memory.is_owner():
                print("Tild: Vi ses bro!")
            elif memory.is_session_identified():
                print("Tild: Goodbye! It was great talking with you.")
            else:
                print("Tild: Goodbye!")
            break

        language = detect_language(user_input)
        tone = memory.get_tone()
        memory.add_to_conversation("human", user_input)

        response = get_response(
            model, tokenizer, rag, memory,
            search, ner, user_input, language, brain=brain
        )

        memory.add_to_conversation("tild", response)
        print(f"Tild: {response}\n")


if __name__ == "__main__":
    chat()