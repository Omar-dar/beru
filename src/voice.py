"""Free local/cloudless voice: faster-whisper (STT) + Edge neural TTS (EN/SV/AR)."""

import asyncio
import os
import platform
import subprocess
import tempfile
import threading

_stt_model = None
_stt_lock = threading.Lock()

SUPPORTED_AUDIO_EXTENSIONS = {
    '.wav', '.webm', '.ogg', '.mp3', '.m4a', '.mp4', '.flac', '.mpeg', '.mpga',
}

# Microsoft Edge neural voices — free via edge-tts, no API key
EDGE_VOICES = {
    'en': 'en-US-JennyNeural',
    'sv': 'sv-SE-SofieNeural',
    'ar': 'ar-SA-ZariyahNeural',
}

MACOS_VOICES = {
    'en': 'Samantha',
    'sv': 'Alva',
    'ar': 'Majed',
}

# Helps Whisper with accent and language (especially Swedish / Arabic)
STT_INITIAL_PROMPTS = {
    'en': (
        'Clear English speech. Casual conversation. '
        'The speaker may mix in Swedish or Arabic words sometimes.'
    ),
    'sv': (
        'Tydlig svenska. Jag pratar svenska. Naturlig svensk accent. '
        'Talaren kan blanda in engelska ord ibland.'
    ),
    'ar': (
        'محادثة عربية واضحة. اللغة العربية الفصحى أو العامية. '
        'قد يخلط المتحدث كلمات إنجليزية أو سويدية أحياناً.'
    ),
}


def _stt_backend():
    return os.getenv('BERU_STT_BACKEND', 'faster-whisper').strip().lower()


def _tts_backend():
    return os.getenv('BERU_TTS_BACKEND', 'edge').strip().lower()


def _whisper_model_name():
    return os.getenv('BERU_WHISPER_MODEL', 'medium')


def is_tts_available():
    if _tts_backend() == 'edge':
        return True
    return _tts_backend() == 'macos' and platform.system() == 'Darwin'


def is_server_tts_available():
    """Alias for older API checks."""
    return is_tts_available()


def capabilities():
    return {
        'stt': True,
        'stt_engine': _stt_backend(),
        'whisper_model': _whisper_model_name(),
        'whisper_compute_type': os.getenv('BERU_WHISPER_COMPUTE_TYPE', 'int8'),
        'tts_engine': _tts_backend(),
        'tts_server': is_tts_available(),
        'tts_voices': EDGE_VOICES if _tts_backend() == 'edge' else MACOS_VOICES,
        'tts_note': (
            'Default: faster-whisper (medium) + edge-tts neural voices — free, no API keys. '
            'Set BERU_STT_BACKEND=whisper or BERU_TTS_BACKEND=macos to use older stack.'
        ),
        'supported_upload_extensions': sorted(SUPPORTED_AUDIO_EXTENSIONS),
        'recommended_record_format': 'audio/webm or audio/wav',
        'sample_rate_hint_hz': 16000,
        'language_hints': ['en', 'sv', 'ar'],
    }


def preload_stt_model():
    """Load speech model once (optional at API startup)."""
    _get_stt_model()


def _get_stt_model():
    global _stt_model
    if _stt_model is not None:
        return _stt_model

    with _stt_lock:
        if _stt_model is not None:
            return _stt_model

        backend = _stt_backend()
        model_name = _whisper_model_name()

        if backend == 'faster-whisper':
            from faster_whisper import WhisperModel

            device = os.getenv('BERU_WHISPER_DEVICE', 'cpu')
            compute_type = os.getenv('BERU_WHISPER_COMPUTE_TYPE', 'int8')
            print(
                f'Loading faster-whisper "{model_name}" '
                f'(device={device}, compute={compute_type})...'
            )
            _stt_model = ('faster-whisper', WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
            ))
        else:
            import whisper

            device = os.getenv('BERU_WHISPER_DEVICE', 'cpu')
            print(f'Loading openai-whisper "{model_name}" ({device})...')
            _stt_model = ('whisper', whisper.load_model(model_name, device=device))

        print('Speech recognition ready.')
    return _stt_model


def _transcribe_faster_whisper(model, path, *, language_hint=None):
    lang = language_hint if language_hint in ('en', 'sv', 'ar') else None
    prompt = STT_INITIAL_PROMPTS.get(lang or '', '') or None

    kwargs = {
        'beam_size': 5,
        'vad_filter': True,
        'condition_on_previous_text': False,
    }
    if lang:
        kwargs['language'] = lang
    if prompt:
        kwargs['initial_prompt'] = prompt

    segments, info = model.transcribe(path, **kwargs)
    parts = []
    for seg in segments:
        parts.append(seg.text)
    text = ''.join(parts).strip()
    detected = info.language or lang or 'en'
    return text, detected, len(parts)


def _transcribe_openai_whisper(model, path, *, language_hint=None):
    options = {
        'task': 'transcribe',
        'condition_on_previous_text': False,
    }
    if language_hint in ('en', 'sv', 'ar'):
        options['language'] = language_hint
        options['initial_prompt'] = STT_INITIAL_PROMPTS[language_hint]

    result = model.transcribe(path, **options)
    text = (result.get('text') or '').strip()
    detected = result.get('language') or language_hint or 'en'
    return text, detected, len(result.get('segments') or [])


def transcribe_file(path, *, language_hint=None):
    """
    Transcribe audio file.
    Returns dict: text, language, segment_count.
    """
    backend, model = _get_stt_model()

    if backend == 'faster-whisper':
        text, detected, seg_count = _transcribe_faster_whisper(
            model, path, language_hint=language_hint
        )
    else:
        text, detected, seg_count = _transcribe_openai_whisper(
            model, path, language_hint=language_hint
        )

    return {
        'text': text,
        'language': detected,
        'segment_count': seg_count,
    }


async def _edge_tts_to_file(text, voice, out_path):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def _edge_voice_for_language(language):
    key = f'BERU_EDGE_VOICE_{language.upper()}'
    return os.getenv(key) or EDGE_VOICES.get(language, EDGE_VOICES['en'])


def synthesize_speech(text, language='en', *, max_chars=2000):
    """
    Synthesize speech bytes and MIME type.
    Default: edge-tts MP3 (natural multilingual). Fallback: macOS say WAV.
    """
    from src.text_style import strip_long_dashes

    text = strip_long_dashes((text or '').strip())
    if not text:
        raise ValueError('Empty text')

    if len(text) > max_chars:
        text = text[:max_chars] + '…'

    backend = _tts_backend()

    if backend == 'edge':
        voice = _edge_voice_for_language(language)
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            mp3_path = tmp.name
        try:
            asyncio.run(_edge_tts_to_file(text, voice, mp3_path))
            with open(mp3_path, 'rb') as f:
                return f.read(), 'audio/mpeg'
        finally:
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)

    if backend == 'macos' and platform.system() == 'Darwin':
        return synthesize_wav_macos(text, language), 'audio/wav'

    raise RuntimeError(
        f'TTS backend "{backend}" is not available. Install edge-tts (pip install edge-tts) '
        'or use BERU_TTS_BACKEND=macos on macOS.'
    )


def synthesize_wav(text, language='en', *, max_chars=2000):
    """Backward-compatible: returns WAV bytes (macOS only) or MP3 from edge as WAV unavailable."""
    data, mime = synthesize_speech(text, language, max_chars=max_chars)
    if mime == 'audio/wav':
        return data
    raise RuntimeError(
        'Default TTS is edge-tts (MP3). Use synthesize_speech() or /voice/speak Accept header.'
    )


def synthesize_wav_macos(text, language='en', *, max_chars=2000):
    """macOS only: render text to 16-bit mono WAV via `say` + ffmpeg."""
    if platform.system() != 'Darwin':
        raise RuntimeError('macOS TTS is only available on Darwin.')

    voice = MACOS_VOICES.get(language, MACOS_VOICES['en'])

    with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as tmp:
        aiff_path = tmp.name

    wav_path = aiff_path.replace('.aiff', '.wav')

    try:
        subprocess.run(
            ['say', '-v', voice, '-o', aiff_path, text],
            check=True,
            capture_output=True,
        )
        proc = subprocess.run(
            [
                'ffmpeg', '-y', '-i', aiff_path,
                '-ar', '22050', '-ac', '1',
                '-acodec', 'pcm_s16le', wav_path,
            ],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                'ffmpeg failed. Install ffmpeg (brew install ffmpeg) for macOS TTS.'
            )
        with open(wav_path, 'rb') as f:
            return f.read()
    finally:
        for p in (aiff_path, wav_path):
            if os.path.exists(p):
                os.unlink(p)
