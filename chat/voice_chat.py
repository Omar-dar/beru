import torch
import tiktoken
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import random
import tempfile
import subprocess
import os
from src.config import TildConfig
from src.model import Tild

cfg = TildConfig()

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! Omar needs to train me more on that topic.",
    "I do not have enough knowledge about that yet but I am always learning!",
    "That is beyond what I know right now. But tell me more!",
    "Omar has not trained me on that yet! But I am getting smarter every day.",
]

# Arabic fallbacks
FALLBACKS_AR = [
    "هذا سؤال مثير للاهتمام! لا أزال أتعلم عن هذا الموضوع.",
    "لست متأكداً من ذلك بعد. اسألني شيئاً آخر!",
    "سؤال جيد! عمر يحتاج أن يدربني أكثر على هذا الموضوع.",
    "لا أعرف الكافي عن ذلك بعد، لكنني أتعلم دائماً!",
]

# Swedish fallbacks
FALLBACKS_SV = [
    "Det är en intressant fråga! Jag lär mig fortfarande om det ämnet.",
    "Jag är inte säker på det ännu. Fråga mig något annat!",
    "Bra fråga! Omar behöver träna mig mer på det ämnet.",
    "Jag vet inte tillräckligt om det ännu, men jag lär mig hela tiden!",
]

def load_tild():
    checkpoint = torch.load(cfg.model_path, map_location=cfg.device)
    vocab_size = checkpoint['vocab_size']
    encoding = checkpoint['encoding']
    enc = tiktoken.get_encoding(encoding)
    model = Tild(vocab_size).to(cfg.device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    return model, enc

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

def speak(text, language='en'):
    print(f"Tild: {text}")
    subprocess.run(['say', '-v', 'Karen', text])

def get_tild_response(model, enc, user_input, language='en'):
    prompt = f"### Human: {user_input}\n### Tild:"
    tokens = enc.encode(prompt, disallowed_special=())
    context = torch.tensor([tokens], dtype=torch.long, device=cfg.device)

    with torch.no_grad():
        output = model.generate(context, max_new_tokens=80)

    generated = enc.decode(output[0].tolist())
    response = generated[len(prompt):].split('\n')[0].strip()

    if not is_good_response(response):
        if language == 'ar':
            response = random.choice(FALLBACKS_AR)
        elif language == 'sv':
            response = random.choice(FALLBACKS_SV)
        else:
            response = random.choice(FALLBACKS)

    return response

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
    print("Loading Tild's brain...")
    model, enc = load_tild()

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
        response = get_tild_response(model, enc, text, language)
        speak(response, language)

if __name__ == '__main__':
    voice_chat()    