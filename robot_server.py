import socket
import whisper
import subprocess
import tempfile
import os
import wave
import struct

from src.pipeline import BeruPipeline

MIC_RATE = 16000
SPK_RATE = 22050
PORT = 5001

print("Loading Whisper...")
whisper_model = whisper.load_model("small", device="cpu")
print("Whisper ready!")

pipeline = BeruPipeline(load_model=False)


def audio_to_wav(audio_data, sample_rate, path):
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)


def text_to_speech(text):
    if len(text) > 100:
        text = text[:100]

    with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as f:
        tmp_path = f.name

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

        turn = pipeline.chat_turn(text, format_for_ui=False)
        response = turn['response']
        print(f"Beru: {response}")

        print("Converting to speech...")
        speech_data = text_to_speech(response)
        print(f"Speech size: {len(speech_data)} bytes")

        resp_size = len(speech_data)
        try:
            conn.send(struct.pack('<I', resp_size))
            sent = 0
            while sent < resp_size:
                chunk = min(4096, resp_size - sent)
                conn.send(speech_data[sent:sent + chunk])
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
