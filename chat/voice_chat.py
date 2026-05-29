import random
import re
import os
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import subprocess
from dotenv import load_dotenv
from transformers import GPT2LMHeadModel, GPT2Tokenizer

from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.ollama_brain import OllamaBrain

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


def detect_language(text):
    swedish_chars = set("åäöÅÄÖ")
    arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

    swedish_words = {
        "vad", "heter", "jag", "hur", "vem", "är", "det",
        "och", "att", "kan", "du", "inte", "med", "för",
        "på", "om", "men", "har", "en", "ett", "var",
        "när", "vill", "ska", "vi", "de", "sig", "som"
    }

    if any(c in swedish_chars for c in text):
        return "sv"

    if any(c in arabic_chars for c in text):
        return "ar"

    words = set(text.lower().split())

    if len(words.intersection(swedish_words)) >= 1:
        return "sv"

    return "en"


def detect_name(user_input_lower):
    skip_words = {
        "a", "an", "the", "not", "no", "yes", "ok", "okay",
        "here", "sure", "good", "bad", "just", "only", "also",
        "very", "really", "so", "too", "up", "out", "on",
        "tired", "happy", "sad", "bored", "stressed", "excited",
        "ledsen", "glad", "arg", "trött", "stressad", "sjuk",
        "inte"
    }

    ignore_phrases = [
        "jag är inte",
        "mitt namn är inte",
        "my name is not",
        "i am not"
    ]

    if any(phrase in user_input_lower for phrase in ignore_phrases):
        return None

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


def is_analysis_request(text):
    analysis_triggers = [
        "analysera", "analyse", "analyze", "hitta", "find",
        "identifiera", "identify", "vilka personer", "who is mentioned",
        "vem nämns", "tidslinje", "timeline", "samband", "connections",
        "mönster", "pattern", "sammanfatta", "summarize", "summera"
    ]

    text_lower = text.lower()
    return any(trigger in text_lower for trigger in analysis_triggers)


def get_tild_response(model, tokenizer, rag, memory, search, ner, user_input, language="en"):
    language = detect_language(user_input)
    user_input_lower = user_input.lower()

    if memory.user.get("pending_name"):
        pending_name = memory.user["pending_name"]
        pending_language = memory.user.get("pending_language", "en")

        if PROTECTED_USERS.get(pending_name) == user_input.strip():
            memory.user.pop("pending_name", None)
            memory.user.pop("pending_language", None)

            memory.set_user(pending_name, pending_language)
            memory.user["verified"] = True
            memory.save_memory()

            if pending_language == "sv":
                return f"Rätt lösenord! Hej {pending_name}. Hur kan jag hjälpa dig?"

            return f"Correct password! Hey {pending_name}. How can I help you?"

        memory.user.pop("pending_name", None)
        memory.user.pop("pending_language", None)
        memory.save_memory()

        if language == "sv":
            return "Fel lösenord! Jag kan inte verifiera din identitet."

        return "Wrong password! I cannot verify your identity."

    detected_name = detect_name(user_input_lower)

    if detected_name:
        if detected_name in PROTECTED_USERS:
            memory.user["pending_name"] = detected_name
            memory.user["pending_language"] = language
            memory.save_memory()

            if language == "sv":
                return f"Hej! Jag känner igen namnet {detected_name}. Vad är lösenordet?"

            return f"Hey! I recognize the name {detected_name}. What is the password?"

        memory.set_user(detected_name, language)

        if language == "sv":
            return f"Hej {detected_name}! Kul att lära känna dig. Hur kan jag hjälpa dig?"

        return f"Hey {detected_name}! Nice to meet you. How can I help you?"

    who_triggers = [
        "do you know who i am", "vet du vem jag är",
        "kommer du ihåg mig", "do you remember me",
        "who am i", "vem är jag", "minns du mig",
    ]

    if any(trigger in user_input_lower for trigger in who_triggers):
        name = memory.get_user_name()

        if name:
            if language == "sv":
                return f"Självklart! Du är {name}!"
            return f"Of course! You are {name}!"

        if language == "sv":
            return "Jag vet inte vem du är ännu! Vad heter du?"

        return "I do not know who you are yet! What is your name?"

    name_triggers = [
        "what is my name", "vad heter jag",
        "do you know my name", "vet du vad jag heter",
        "kommer du ihåg mitt namn", "do you remember my name"
    ]

    if any(trigger in user_input_lower for trigger in name_triggers):
        name = memory.get_user_name()

        if name:
            if language == "sv":
                return f"Du heter {name}!"
            return f"Your name is {name}!"

        if language == "sv":
            return "Du har inte berättat vad du heter! Vad heter du?"

        return "You have not told me your name yet! What is your name?"

    if memory.is_correction(user_input):
        return "Tack för korrigeringen! Jag kommer att komma ihåg det." if language == "sv" else "Thank you for correcting me! I will remember that."

    for correction in memory.corrections:
        q_words = set(correction["question"].lower().split())
        u_words = set(user_input.lower().split())

        if len(q_words.intersection(u_words)) >= 3:
            return correction["correct"]

    if len(user_input.split()) > 8 and is_analysis_request(user_input):
        rag_answer, score = rag.find_answer(user_input, threshold=0.70)

        if rag_answer and score > 0.70:
            print(f"[RAG match: {score:.2f}]")
            return rag_answer

        entities = ner.extract_entities(user_input)

        if entities["persons"] or entities["places"] or entities["dates"]:
            print("[Entity recognition used]")
            return ner.format_entities(entities, language)

    tild_keywords = [
        "tild", "who are you", "what are you", "about you",
        "your name", "your purpose", "whats your", "what's your",
        "built you", "made you", "created you", "your creator",
        "who made", "who built", "who created", "ur name",
        "your age", "how old are you", "where do you live",
        "what do you do", "what can you do", "are you an ai",
        "are you real", "are you human", "do you have feelings",
        "vem är du", "vad är du", "vad heter du", "vem skapade",
        "vem byggde", "var bor du", "hur gammal", "vad kan du",
        "berätta om dig", "hur fungerar du", "vad gör du"
    ]

    omar_keywords = [
        "omar darwish", "your creator", "who made you",
        "who built you", "who created you", "omar made",
        "omar built", "omar created", "vem är omar",
        "omar skapade", "omar byggde", "berätta om omar",
        "vad vet du om omar", "är omar smart"
    ]

    is_about_tild = any(word in user_input_lower for word in tild_keywords + omar_keywords)

    if search.should_search(user_input) and not is_about_tild:
        print("[Searching internet...]")

        result = search.search(user_input)

        if result:
            result = re.sub(r"\[\d+\]", "", result).strip()

            if len(result) > 150:
                result = result[:150] + "..."

            print(f"[Found: {result[:50]}...]")
            return search.format_response(result, user_input)

        if language == "sv":
            return "Jag försökte söka efter det men kunde inte ansluta just nu. Fråga mig något annat!"

        return "I tried searching for that but could not connect right now. Try asking me something else!"

    rag_answer, score = rag.find_answer(user_input)

    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        return rag_answer

    if language == "ar":
        return random.choice(FALLBACKS_AR)

    if language == "sv":
        return random.choice(FALLBACKS_SV)

    return random.choice(FALLBACKS)


def speak(text, language="en"):
    print(f"Tild: {text}")

    voice = "Samantha"

    if language == "sv":
        voice = "Alva"

    subprocess.run(["say", "-v", voice, text])


def record_audio(duration=7, sample_rate=16000, silence_threshold=0.01, silence_duration=1.5):
    print("Speak now! Stops automatically when you stop talking.")

    chunk_size = int(sample_rate * 0.1)
    max_chunks = int(duration * sample_rate / chunk_size)
    silence_chunks = int(silence_duration * sample_rate / chunk_size)

    recorded = []
    silent_count = 0
    started_speaking = False

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )

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
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, sample_rate)

    result = whisper_model.transcribe(temp_path, task="transcribe")

    detected_language = result["language"]
    text = result["text"].strip()

    print(f"Detected language: {detected_language}")

    os.unlink(temp_path)

    return text, detected_language


def voice_chat():
    model, tokenizer = load_tild()
    rag = TildRAG()
    memory = TildMemory()
    search = TildSearch()
    ner = TildEntityRecognizer()
    ollama = OllamaBrain()

    print("Loading Whisper...")
    whisper_model = whisper.load_model("small", device="cpu")

    print("\nTild is ready! Press Enter to speak, type 'quit' to exit\n")
    speak("Hello! I am Tild. Press enter and speak to me!")

    while True:
        user_input = input("\nPress Enter to speak or type 'quit': ").strip()

        if user_input.lower() == "quit":
            speak("Goodbye! It was great talking with you.")
            break

        audio, sample_rate = record_audio()
        text, whisper_language = transcribe_audio(audio, sample_rate, whisper_model)

        if not text or len(text.split()) < 2:
            speak("I did not hear you clearly. Please try again!")
            continue

        print(f"You said: {text}")

        language = detect_language(text)

        memory.add_to_conversation("human", text)

        response = get_tild_response(
            model,
            tokenizer,
            rag,
            memory,
            search,
            ner,
            text,
            language
        )

        if response in FALLBACKS or response in FALLBACKS_SV or response in FALLBACKS_AR:
            response = ollama.ask(text, language)

        memory.add_to_conversation("tild", response)

        speak(response, language)


if __name__ == "__main__":
    voice_chat()