from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

sys.path.append('/Users/omardarwish/tild')

from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.ollama_brain import OllamaBrain
from chat.chat import get_response, detect_language, load_tild

app = Flask(__name__)
CORS(app)

print("Loading Tild brain...")
rag = TildRAG()
memory = TildMemory()
search = TildSearch()
ner = TildEntityRecognizer()
ollama = OllamaBrain()
model, tokenizer = load_tild()

# Clear session verification on startup
memory.user.pop('verified', None)
memory.save_memory()

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
    name = memory.get_user_name()

    if name == 'Omar':
        return jsonify({
            'response': 'Hey! Tild here. Is that you Omar? Say "I am Omar" to confirm.',
            'language': 'en',
            'known_user': False,
            'tone': 'formal'
        })
    elif name:
        return jsonify({
            'response': f'Hey! Is that you {name}?',
            'language': 'en',
            'known_user': False,
            'tone': 'formal'
        })
    else:
        return jsonify({
            'response': 'Hey! I am Tild. Who am I talking to?',
            'language': 'en',
            'known_user': False,
            'tone': 'formal'
        })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'No message'}), 400

    language = detect_language(message)
    tone = memory.get_tone()

    response = get_response(model, tokenizer, rag, memory, search, ner, message, language)

    if response in FALLBACKS or response in FALLBACKS_SV or response in FALLBACKS_AR:
        response = ollama.ask(message, language, tone=tone)

    return jsonify({'response': response, 'language': language, 'tone': tone})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Tild API is running'})

if __name__ == '__main__':
    app.run(port=8000, debug=False)