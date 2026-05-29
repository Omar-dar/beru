from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import re

sys.path.append('/Users/omardarwish/tild')

from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.ollama_brain import OllamaBrain

app = Flask(__name__)
CORS(app)

PROTECTED_USERS = {
    'Omar': os.getenv('TILD_OMAR_PASSWORD', 'tild123')
}

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! I need to learn more about that.",
]

FALLBACKS_SV = [
    "Det är en intressant fråga! Jag lär mig fortfarande.",
    "Jag är inte säker på det ännu. Fråga mig något annat!",
    "Bra fråga! Jag behöver lära mig mer om det.",
]

FALLBACKS_AR = [
    "هذا سؤال مثير للاهتمام! لا أزال أتعلم.",
    "لست متأكداً من ذلك بعد. اسألني شيئاً آخر!",
]

print("Loading Tild brain...")
rag = TildRAG()
memory = TildMemory()
search = TildSearch()
ner = TildEntityRecognizer()
ollama = OllamaBrain()
print("Tild API ready!")

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

def get_response(user_input):
    import random
    language = detect_language(user_input)
    user_input_lower = user_input.lower()

    # Password check
    if memory.user.get('pending_name'):
        pending_name = memory.user['pending_name']
        pending_language = memory.user.get('pending_language', 'en')
        if PROTECTED_USERS.get(pending_name) == user_input.strip():
            memory.user.pop('pending_name', None)
            memory.user.pop('pending_language', None)
            memory.set_user(pending_name, pending_language)
            memory.user['verified'] = True
            memory.save_memory()
            if pending_name == 'Omar':
                return 'Rätt lösenord! Hej Omar, min skapare!' if pending_language == 'sv' else 'Correct password! Hey Omar, my creator!'
            return f'Rätt lösenord! Hej {pending_name}!' if pending_language == 'sv' else f'Correct password! Hey {pending_name}!'
        memory.user.pop('pending_name', None)
        memory.user.pop('pending_language', None)
        memory.save_memory()
        return 'Fel lösenord!' if language == 'sv' else 'Wrong password!'

    # Name detection
    from chat.chat import detect_name
    detected_name = detect_name(user_input_lower)
    if detected_name:
        if detected_name in PROTECTED_USERS:
            if memory.user.get('name') == detected_name and memory.user.get('verified'):
                return f'Hej {detected_name}! Du är redan inloggad.' if language == 'sv' else f'Hey {detected_name}! You are already logged in.'
            memory.user['pending_name'] = detected_name
            memory.user['pending_language'] = language
            memory.save_memory()
            return f'Hej! Jag känner igen namnet {detected_name}. Vad är lösenordet?' if language == 'sv' else f'Hey! I recognize the name {detected_name}. What is the password?'
        memory.set_user(detected_name, language)
        return f'Hej {detected_name}! Kul att lära känna dig.' if language == 'sv' else f'Hey {detected_name}! Nice to meet you.'

    # RAG
    rag_answer, score = rag.find_answer(user_input, threshold=0.55)
    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        memory.add_to_conversation('human', user_input)
        memory.add_to_conversation('tild', rag_answer)
        return rag_answer

    # Ollama fallback
    print("[Ollama backup used]")
    response = ollama.ask(user_input, language)
    memory.add_to_conversation('human', user_input)
    memory.add_to_conversation('tild', response)
    return response

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'No message'}), 400
    language = detect_language(message)
    response = get_response(message)
    return jsonify({'response': response, 'language': language})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Tild API is running'})

if __name__ == '__main__':
    app.run(port=8000, debug=False)