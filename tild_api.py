from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

sys.path.append('/Users/omardarwish/tild')

from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.deep_brain import DeepBrain
from src.language import detect_language
from chat.chat import get_response, load_tild

app = Flask(__name__)
CORS(app)

print("Loading Tild brain...")
rag = TildRAG()
memory = TildMemory()
search = TildSearch()
ner = TildEntityRecognizer()
brain = DeepBrain()
model, tokenizer = load_tild()

print("Tild API ready!")

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! I need to learn more about that.",
    "I do not have enough knowledge about that yet but I am always learning!",
]

FALLBACKS_SV = [
    "Det är en intressant fråga! Jag lär mig fortfarande.",
    "Jag är inte säker på det ännu. Fråga mig något annat!",
    "Bra fråga! Jag behöver lära mig mer om det.",
    "Jag vet inte tillräckligt om det ännu men jag lär mig hela tiden!",
]

FALLBACKS_AR = [
    "هذا سؤال مثير للاهتمام! لا أزال أتعلم.",
    "لست متأكداً من ذلك بعد. اسألني شيئاً آخر!",
]

@app.route('/start', methods=['GET'])
def start():
    memory.start_session(clear_history=True)
    lang = 'en'
    return jsonify({
        'response': memory.greeting_for_session(lang),
        'language': lang,
        'known_user': memory.is_session_identified(),
        'awaiting_owner_confirm': memory.is_awaiting_owner_confirm(),
        'is_owner': memory.is_owner(),
        'tone': memory.get_tone(),
    })

@app.route('/clear', methods=['POST'])
def clear_chat():
    memory.start_session(clear_history=True)
    return jsonify({
        'status': 'ok',
        'response': memory.greeting_for_session(),
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').strip()
    new_chat = data.get('new_chat', False)

    if new_chat:
        memory.start_session(clear_history=True)

    if not message:
        return jsonify({'error': 'No message'}), 400

    language = detect_language(message)
    tone = memory.get_tone()
    memory.add_to_conversation('human', message)

    response = get_response(model, tokenizer, rag, memory, search, ner, message, language, brain=brain)

    memory.add_to_conversation('tild', response)

    return jsonify({
        'response': response,
        'language': language,
        'tone': tone,
        'user': memory.get_user_name(),
        'is_owner': memory.is_owner(),
        'session_identified': memory.is_session_identified(),
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Tild API is running'})

if __name__ == '__main__':
    app.run(port=8000, debug=False)