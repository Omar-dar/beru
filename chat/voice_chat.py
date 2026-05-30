import os
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import subprocess
from dotenv import load_dotenv

from src.pipeline import TildPipeline
from src.language import detect_language

load_dotenv()


def speak(text, language="en"):
    print(f"Tild: {text}")
    voice = "Alva" if language == "sv" else "Samantha"
    subprocess.run(["say", "-v", voice, text])


def record_audio(duration=7, sample_rate=16000, silence_threshold=0.01, silence_duration=1.5):
    print("Speak now! Stops automatically when you stop talking.")

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
    pipeline = TildPipeline()

    print("Loading Whisper...")
    whisper_model = whisper.load_model("small", device="cpu")

    greeting = pipeline.start_session(clear_history=False)
    print(f"\nTild: {greeting}")
    speak(greeting)
    print("\nPress Enter to speak, type 'quit' to exit\n")

    while True:
        user_input = input("\nPress Enter to speak or type 'quit': ").strip()

        if user_input.lower() == "quit":
            farewell = "Vi ses bro!" if pipeline.memory.is_owner() else "Goodbye! It was great talking with you."
            speak(farewell)
            break

        audio, sample_rate = record_audio()
        text, whisper_language = transcribe_audio(audio, sample_rate, whisper_model)

        if not text or len(text.split()) < 2:
            speak("I did not hear you clearly. Please try again!")
            continue

        print(f"You said: {text}")
        result = pipeline.chat_turn(text, format_for_ui=False)
        speak(result['response'], result['language'])


if __name__ == "__main__":
    voice_chat()
