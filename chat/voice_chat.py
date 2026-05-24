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

def get_tild_response(model, tokenizer, rag, memory, user_input, language='en'):
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
        if correction['question'].lower() in user_input.lower():
            return correction['correct']

    # Try RAG
    rag_answer, score = rag.find_answer(user_input, threshold=0.65)
    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        return rag_answer

    # Use context + language model
    context = memory.get_context()
    prompt = f"{context}### Human: {user_input}\n### Tild:"
    inputs = tokenizer.encode(prompt, return_tensors='pt')

    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=80,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
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
    subprocess.run(['say', '-v', 'Karen', text])

def record_audio(duration=5, sample_rate=16000):
    print(f"Recording for {duration} seconds... Speak now!")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    print("Recording done!")
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

    print("Loading Whisper...")
    whisper_model = whisper.load_model("small", device="cpu")

    print("\nTild is ready! Press Enter to speak, type 'quit' to exit\n")
    speak("Hello! I am Tild. Press enter and speak to me!")

    while True:
        user_input = input("\nPress Enter to speak (or type 'quit'): ").strip()

        if user_input.lower() == 'quit':
            speak("Goodbye! It was great talking with you.")
            break

        audio, sample_rate = record_audio(duration=5)
        text, language = transcribe_audio(audio, sample_rate, whisper_model)

        if not text:
            speak("I did not hear anything. Try again!")
            continue

        print(f"You said: {text}")
        memory.add_to_conversation('human', text)
        response = get_tild_response(model, tokenizer, rag, memory, text, language)
        memory.add_to_conversation('tild', response)
        speak(response, language)

if __name__ == '__main__':
    voice_chat()