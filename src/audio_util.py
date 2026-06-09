"""Load browser mic clips (WebM/MP4/WAV) as 16 kHz mono for voice auth."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

import numpy as np

SAMPLE_RATE = 16000
MIN_SECONDS = float(os.getenv('BERU_VOICE_MIN_SECONDS', '0.35'))


def _ffmpeg_exe() -> Optional[str]:
    path = shutil.which('ffmpeg')
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _ffmpeg_available() -> bool:
    return _ffmpeg_exe() is not None


def convert_to_wav_16k(audio_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Decode any supported upload to a temp WAV file.
    Returns (wav_path, error_message).
    """
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return None, (
            'ffmpeg not found — install ffmpeg or run: pip install imageio-ffmpeg'
        )

    out = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    out.close()
    proc = subprocess.run(
        [
            ffmpeg, '-y', '-loglevel', 'error',
            '-i', audio_path,
            '-ar', str(SAMPLE_RATE),
            '-ac', '1',
            '-f', 'wav',
            out.name,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or 'ffmpeg decode failed').strip()
        if os.path.exists(out.name):
            os.unlink(out.name)
        return None, err[:240]
    if os.path.getsize(out.name) < 200:
        os.unlink(out.name)
        return None, 'decoded audio too short'
    return out.name, None


def load_mono_16k(audio_path: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Load audio as float32 mono @ 16 kHz.
    Returns (samples, error_message).
    """
    cleanup: list[str] = []
    try:
        wav_path, ff_err = convert_to_wav_16k(audio_path)
        load_path = audio_path
        if wav_path:
            cleanup.append(wav_path)
            load_path = wav_path
        elif ff_err and _needs_ffmpeg(audio_path):
            return None, ff_err

        try:
            import soundfile as sf

            y, sr = sf.read(load_path, dtype='float32', always_2d=False)
        except Exception:
            import librosa

            y, sr = librosa.load(load_path, sr=SAMPLE_RATE, mono=True)

        if y is None:
            return None, 'empty audio'
        y = np.asarray(y, dtype=np.float32).flatten()
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        if sr != SAMPLE_RATE and len(y) > 0:
            import librosa

            y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)

        min_samples = int(SAMPLE_RATE * MIN_SECONDS)
        if len(y) < min_samples:
            secs = len(y) / SAMPLE_RATE
            return None, f'clip too short ({secs:.1f}s — need ~{MIN_SECONDS:.1f}s+)'

        peak = float(np.max(np.abs(y)))
        if peak < 1e-4:
            return None, 'clip too quiet — speak closer to the mic'

        return y, None
    except Exception as exc:
        return None, str(exc)[:240]
    finally:
        for p in cleanup:
            try:
                os.unlink(p)
            except OSError:
                pass


def _needs_ffmpeg(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {'.webm', '.ogg', '.mp4', '.m4a', '.mp3', '.mpeg', '.mpga', '.opus'}
