import torch
import random
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import subprocess
import os
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
]

def load_tild():
    print("Loading Tild's brain...")
    tokenizer = GPT2Tokenizer.from_pretrained('models/tild_v2')
    model = GPT2LMHeadModel.from_pretrained('models/tild_v2')
    model.eval()
    return model, tokenizer

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

def get_tild_response(model, tokenizer, rag, memory, search, user_input, language='en'):
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
                return "Thank you for correcting me! I will remember that."
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
        'are you real', 'are you human', 'do you have feelings'
    ]
    omar_keywords = [
        'omar darwish', 'your creator', 'who made you',
        'who built you', 'who created you', 'omar made',
        'omar built', 'omar created'
    ]
    is_about_tild = any(word in user_input.lower() for word in tild_keywords + omar_keywords)

    # Search internet for external questions only
    if search.should_search(user_input) and not is_about_tild:
        print("[Searching internet...]")
        result = search.search(user_input)
        if result:
            # Clean result — remove citations like [4][5]
            import re
            result = re.sub(r'\[\d+\]', '', result).strip()
            # Keep it short
            if len(result) > 150:
                result = result[:150] + "..."
            print(f"[Found: {result[:50]}...]")
            return search.format_response(result, user_input)
        else:
            return "I tried searching for that but could not connect right now. Try asking me something else!"

    # RAG for Tild specific questions
    rag_answer, score = rag.find_answer(user_input, threshold=0.65)
    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        return rag_answer

    # Language model fallback
    context = memory.get_context()
    prompt = f"{context}### Human: {user_input}\n### Tild:"
    inputs = tokenizer.encode(prompt, return_tensors='pt')

    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=50,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.3,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.encode('\n')[0]
        )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response = generated[len(prompt):].split('\n')[0].strip()

    if not is_good_response(response):
        if language == 'ar':
            response = random.choice(FALLBACKS_AR)
        elif language == 'sv':
            response = random.choice(FALLBACKS_SV)
        else:
            response = random.choice(FALLBACKS)

    return response

def speak(text, language='en'):
    print(f"Tild: {text}")
    subprocess.run(['say', '-v', 'Samantha', text])

def record_audio(duration=7, sample_rate=16000, silence_threshold=0.01, silence_duration=1.5):
    print("Speak now! (stops automatically when you stop talking)")

    chunk_size = int(sample_rate * 0.1)
    max_chunks = int(duration * sample_rate / chunk_size)
    silence_chunks = int(silence_duration * sample_rate / chunk_size)

    recorded = []
    silent_count = 0
    started_speaking = False

    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype=np.float32)
    stream.start()

    for _ in range(max_chunks):
        chunk, _ = stream.read(chunk_size)
        recorded.append(chunk)

        volume = np.abs(chunk).mean()

        if volume > silence_threshold:
            started_speaking = True
            silent_count = 0
        elif started_speaking:
            silent_count += 1
            if silent_count >= silence_chunks:
                print("Recording done!")
                break

    stream.stop()
    stream.close()

    if not recorded:
        return np.zeros((1, 1), dtype=np.float32), sample_rate

    audio = np.concatenate(recorded, axis=0)
    return audio, sample_rate

def transcribe_audio(audio, sample_rate, whisper_model):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sample_rate)

    result = whisper_model.transcribe(temp_path, task="transcribe")
    detected_language = result['language']
    text = result['text'].strip()

    print(f"Detected language: {detected_language}")
    os.unlink(temp_path)
    return text, detected_language

def voice_chat():
    model, tokenizer = load_tild()
    rag = TildRAG()
    memory = TildMemory()
    search = TildSearch()

    print("Loading Whisper...")
    whisper_model = whisper.load_model("small", device="cpu")

    print("\nTild is ready! Press Enter to speak, type 'quit' to exit\n")
    speak("Hello! I am Tild. Press enter and speak to me!")

    while True:
        user_input = input("\nPress Enter to speak (or type 'quit'): ").strip()

        if user_input.lower() == 'quit':
            speak("Goodbye! It was great talking with you.")
            break

        audio, sample_rate = record_audio()
        text, language = transcribe_audio(audio, sample_rate, whisper_model)

        if not text or len(text.split()) < 2:
            speak("I did not hear you clearly. Please try again!")
            continue

        print(f"You said: {text}")
        memory.add_to_conversation('human', text)
        response = get_tild_response(model, tokenizer, rag, memory, search, text, language)
        memory.add_to_conversation('tild', response)
        speak(response, language)

if __name__ == '__main__':
    voice_chat()