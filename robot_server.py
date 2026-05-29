import socket
import whisper
import subprocess
import tempfile
import os
import wave
import struct
import sys

sys.path.append('/Users/omardarwish/tild')
from src.rag import TildRAG
from src.memory import TildMemory
from src.search import TildSearch
from src.entities import TildEntityRecognizer
from src.ollama_brain import OllamaBrain

MIC_RATE = 16000
SPK_RATE = 22050
PORT = 5001

print("Loading Whisper...")
whisper_model = whisper.load_model("small", device="cpu")
print("Whisper ready!")

print("Loading Tild brain...")
rag = TildRAG()
memory = TildMemory()
search = TildSearch()
ner = TildEntityRecognizer()
print("Tild brain ready!")

print("Loading Ollama backup...")
brain = OllamaBrain(model="llama3.2:3b")
print("Ollama ready!")

def detect_language(text):
    swedish_chars = set('åäöÅÄÖ')
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
    swedish_words = {'hej', 'vad', 'hur', 'jag', 'det', 'är', 'kan',
                     'du', 'inte', 'och', 'att', 'för', 'på', 'om'}
    if any(c in swedish_chars for c in text):
        return 'sv'
    if any(c in arabic_chars for c in text):
        return 'ar'
    words = set(text.lower().split())
    if len(words.intersection(swedish_words)) >= 1:
        return 'sv'
    return 'en'

def audio_to_wav(audio_data, sample_rate, path):
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

def text_to_speech(text):
    # Keep short for ESP32 memory
    if len(text) > 100:
        text = text[:100]

    with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as f:
        tmp_path = f.name

    # Generate speech
    subprocess.run(['say', '-r', '150', '-o', tmp_path, text])

    pcm_path = tmp_path.replace('.aiff', '.raw')
    subprocess.run([
        'ffmpeg', '-y', '-i', tmp_path,
        '-ar', str(SPK_RATE),
        '-ac', '1',
        '-acodec', 'pcm_s16le',
        '-f', 's16le',
        pcm_path
    ], capture_output=True)

    with open(pcm_path, 'rb') as f:
        pcm_data = f.read()

    os.unlink(tmp_path)
    os.unlink(pcm_path)
    return pcm_data

def get_ai_response(text, language):
    print(f"You said: {text}")

    rag_answer, score = rag.find_answer(text, threshold=0.55)
    if rag_answer:
        print(f"[Tild RAG match: {score:.2f}]")
        memory.add_to_conversation('human', text)
        memory.add_to_conversation('tild', rag_answer)
        return rag_answer

    analysis_triggers = [
        'analysera', 'analyze', 'hitta', 'find',
        'identifiera', 'identify', 'vilka personer',
        'tidslinje', 'timeline', 'samband', 'monster'
    ]
    if len(text.split()) > 8 and any(t in text.lower() for t in analysis_triggers):
        entities = ner.extract_entities(text)
        if entities['persons'] or entities['places'] or entities['dates']:
            print(f"[Entity recognition used]")
            result = ner.format_entities(entities, language)
            memory.add_to_conversation('human', text)
            memory.add_to_conversation('tild', result)
            return result

    print("[Ollama backup used]")
    response = brain.ask(text, language)
    memory.add_to_conversation('human', text)
    memory.add_to_conversation('tild', response)
    return response

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', PORT))
server.listen(5)
print(f"\nServer listening on port {PORT}...")
print("Waiting for ESP32...\n")

while True:
    conn, addr = server.accept()
    print(f"ESP32 connected from {addr}")

    try:
        size_bytes = conn.recv(4)
        if len(size_bytes) < 4:
            print("Invalid size received!")
            conn.close()
            continue
        size = struct.unpack('<I', size_bytes)[0]
        print(f"Receiving {size} bytes of audio...")

        audio_data = b''
        while len(audio_data) < size:
            chunk = conn.recv(min(4096, size - len(audio_data)))
            if not chunk:
                break
            audio_data += chunk
        print(f"Received {len(audio_data)} bytes")

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
        audio_to_wav(audio_data, MIC_RATE, wav_path)

        print("Transcribing with Whisper...")
        result = whisper_model.transcribe(wav_path)
        text = result['text'].strip()
        os.unlink(wav_path)
        print(f"Transcribed: {text}")

        if not text:
            text = "hello"

        language = detect_language(text)
        print(f"Language: {language}")

        response = get_ai_response(text, language)
        print(f"Tild: {response}")

        print("Converting to speech...")
        speech_data = text_to_speech(response)
        print(f"Speech size: {len(speech_data)} bytes")

        resp_size = len(speech_data)
        try:
            conn.send(struct.pack('<I', resp_size))
            sent = 0
            while sent < resp_size:
                chunk = min(4096, resp_size - sent)
                conn.send(speech_data[sent:sent+chunk])
                sent += chunk
            print(f"Sent {resp_size} bytes of speech back!")
        except BrokenPipeError:
            print("ESP32 disconnected before receiving response!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\nWaiting for ESP32...\n")