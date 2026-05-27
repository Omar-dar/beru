import torch
import random
import re
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch

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

def load_tild():
    print("Loading Tild's brain...")
    tokenizer = GPT2Tokenizer.from_pretrained('models/tild_v2')
    model = GPT2LMHeadModel.from_pretrained('models/tild_v2')
    model.eval()
    return model, tokenizer

def detect_language(text):
    swedish_chars = set('åäöÅÄÖ')
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
    swedish_words = {'vad', 'heter', 'jag', 'hur', 'vem', 'är', 'det',
                     'och', 'att', 'kan', 'du', 'inte', 'med', 'för',
                     'på', 'om', 'men', 'har', 'en', 'ett', 'var',
                     'när', 'vill', 'ska', 'vi', 'de', 'sig', 'som'}
    if any(c in swedish_chars for c in text):
        return 'sv'
    if any(c in arabic_chars for c in text):
        return 'ar'
    words = set(text.lower().split())
    if len(words.intersection(swedish_words)) >= 1:
        return 'sv'
    return 'en'

def is_good_response(response):
    if len(response) < 3:
        return False
    if len(response.split()) < 2:
        return False
    if '###' in response:
        return False
    if len(set(response.split())) < 2:
        return False
    return True

def detect_name(user_input_lower):
    skip_words = {'a', 'an', 'the', 'not', 'no', 'yes', 'ok', 'okay',
                  'here', 'sure', 'good', 'bad', 'just', 'only', 'also',
                  'very', 'really', 'so', 'too', 'up', 'out', 'on',
                  'tired', 'happy', 'sad', 'bored', 'stressed', 'excited'}
    name_patterns = [
        r"i am (\w+)",
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
    ]
    for pattern in name_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            name = match.group(1).capitalize()
            if name.lower() not in skip_words and len(name) > 1:
                return name
    return None

def get_response(model, tokenizer, rag, memory, search, user_input, language='en'):
    language = detect_language(user_input)
    user_input_lower = user_input.lower()

    # Detect any user introducing themselves
    detected_name = detect_name(user_input_lower)
    if detected_name:
        memory.set_user(detected_name, language)
        if detected_name == 'Omar':
            if language == 'sv':
                return "Hej Omar! Kul att prata med min skapare. Hur kan jag hjälpa dig?"
            else:
                return "Hey Omar! Great to talk to my creator. How can I help you?"
        else:
            if language == 'sv':
                return f"Hej {detected_name}! Kul att lära känna dig. Hur kan jag hjälpa dig?"
            else:
                return f"Hey {detected_name}! Nice to meet you. How can I help you?"

    # Respond when asked who they are
    who_triggers = [
        'do you know who i am', 'vet du vem jag är',
        'kommer du ihåg mig', 'do you remember me',
        'who am i', 'vem är jag', 'minns du mig',
    ]
    if any(trigger in user_input_lower for trigger in who_triggers):
        name = memory.get_user_name()
        if name:
            if name == 'Omar':
                if language == 'sv':
                    return f"Självklart! Du är {name}, min skapare!"
                else:
                    return f"Of course! You are {name}, my creator!"
            else:
                if language == 'sv':
                    return f"Självklart! Du är {name}!"
                else:
                    return f"Of course! You are {name}!"
        else:
            if language == 'sv':
                return "Jag vet inte vem du är ännu! Vad heter du?"
            else:
                return "I do not know who you are yet! What is your name?"

    # Respond to name questions
    name_triggers = [
        'what is my name', 'vad heter jag',
        'do you know my name', 'vet du vad jag heter',
        'kommer du ihåg mitt namn', 'do you remember my name'
    ]
    if any(trigger in user_input_lower for trigger in name_triggers):
        name = memory.get_user_name()
        if name:
            if name == 'Omar':
                if language == 'sv':
                    return f"Du heter {name}! Du är min skapare och du byggde mig från grunden."
                else:
                    return f"Your name is {name}! You are my creator and you built me from scratch."
            else:
                if language == 'sv':
                    return f"Du heter {name}! Kul att ha dig här."
                else:
                    return f"Your name is {name}! Great to have you here."
        else:
            if language == 'sv':
                return "Du har inte berättat vad du heter! Vad heter du?"
            else:
                return "You have not told me your name yet! What is your name?"

    # Check correction
    if memory.is_correction(user_input):
        last_exchange = [m for m in memory.conversation_history if m['role'] == 'tild']
        last_question = [m for m in memory.conversation_history if m['role'] == 'human']

        if last_exchange and last_question:
            wrong_answer = last_exchange[-1]['text']
            question = last_question[-2]['text'] if len(last_question) >= 2 else last_question[-1]['text']
            correct = memory.extract_correction(user_input)

            if correct:
                memory.add_correction(wrong_answer, correct, question)
                if language == 'sv':
                    return "Tack för korrigeringen! Jag kommer att komma ihåg det."
                elif language == 'ar':
                    return "شكراً على التصحيح! سأتذكر ذلك."
                else:
                    return "Thank you for correcting me! I will remember that."
            else:
                if language == 'sv':
                    return "Jag förstår att jag hade fel! Kan du berätta det rätta svaret?"
                elif language == 'ar':
                    return "أفهم أنني كنت مخطئاً! هل يمكنك إخباري بالإجابة الصحيحة؟"
                else:
                    return "I understand I was wrong! Can you tell me the correct answer?"

    # Check corrections memory
    for correction in memory.corrections:
        q_words = set(correction['question'].lower().split())
        u_words = set(user_input.lower().split())
        common = q_words.intersection(u_words)
        if len(common) >= 3:
            return correction['correct']

    # Check if question is about Tild or Omar
    tild_keywords = [
        'tild', 'who are you', 'what are you', 'about you',
        'your name', 'your purpose', 'whats your', "what's your",
        'built you', 'made you', 'created you', 'your creator',
        'who made', 'who built', 'who created', 'ur name',
        'your age', 'how old are you', 'where do you live',
        'what do you do', 'what can you do', 'are you an ai',
        'are you real', 'are you human', 'do you have feelings',
        'vem är du', 'vad är du', 'vad heter du', 'vem skapade',
        'vem byggde', 'var bor du', 'hur gammal', 'vad kan du',
        'berätta om dig', 'hur fungerar du', 'vad gör du'
    ]
    omar_keywords = [
        'omar darwish', 'your creator', 'who made you',
        'who built you', 'who created you', 'omar made',
        'omar built', 'omar created', 'vem är omar',
        'omar skapade', 'omar byggde', 'berätta om omar',
        'vad vet du om omar', 'är omar smart'
    ]
    is_about_tild = any(word in user_input_lower for word in tild_keywords + omar_keywords)

    # Search internet for external questions only
    if search.should_search(user_input) and not is_about_tild:
        print("[Searching internet...]")
        result = search.search(user_input)
        if result:
            result = re.sub(r'\[\d+\]', '', result).strip()
            if len(result) > 150:
                result = result[:150] + "..."
            print(f"[Found: {result[:50]}...]")
            return search.format_response(result, user_input)
        else:
            if language == 'sv':
                return "Jag försökte söka efter det men kunde inte ansluta just nu. Fråga mig något annat!"
            elif language == 'ar':
                return "حاولت البحث لكن لم أتمكن من الاتصال الآن. اسألني شيئاً آخر!"
            else:
                return "I tried searching for that but could not connect right now. Try asking me something else!"

    # RAG
    rag_answer, score = rag.find_answer(user_input, threshold=0.55)
    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        return rag_answer

    # Fallback based on language
    if language == 'ar':
        return random.choice(FALLBACKS_AR)
    elif language == 'sv':
        return random.choice(FALLBACKS_SV)
    else:
        return random.choice(FALLBACKS)

def chat():
    model, tokenizer = load_tild()
    rag = TildRAG()
    memory = TildMemory()
    search = TildSearch()
    print("Tild is ready! Type your message (or 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print("Tild: Goodbye! It was great talking with you.")
            break

        language = detect_language(user_input)
        memory.add_to_conversation('human', user_input)
        response = get_response(model, tokenizer, rag, memory, search, user_input, language)
        memory.add_to_conversation('tild', response)
        print(f"Tild: {response}\n")

if __name__ == '__main__':
    chat()