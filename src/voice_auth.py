"""Owner voice verification — replaces password gate for Omar."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np

from src.audio_util import SAMPLE_RATE, load_mono_16k

PROFILE_PATH = Path(__file__).resolve().parent.parent / 'data' / 'omar_voice_profile.json'


def voice_auth_enabled() -> bool:
    return os.getenv('BERU_VOICE_AUTH', '1').strip().lower() in ('1', 'true', 'yes', 'on')


def similarity_threshold() -> float:
    try:
        return float(os.getenv('BERU_VOICE_THRESHOLD', '0.82'))
    except ValueError:
        return 0.82


def is_available() -> bool:
    try:
        import librosa  # noqa: F401

        return True
    except ImportError:
        return False


def _embedding_from_samples(y: np.ndarray) -> Optional[np.ndarray]:
    import librosa

    mfcc = librosa.feature.mfcc(y=y, sr=SAMPLE_RATE, n_mfcc=24)
    delta = librosa.feature.delta(mfcc)
    stacked = np.vstack([np.mean(mfcc, axis=1), np.std(mfcc, axis=1), np.mean(delta, axis=1)])
    vec = stacked.flatten().astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm < 1e-6:
        return None
    return vec / norm


def _wav_embedding(audio_path: str) -> tuple[Optional[np.ndarray], Optional[str]]:
    y, err = load_mono_16k(audio_path)
    if y is None:
        return None, err
    emb = _embedding_from_samples(y)
    if emb is None:
        return None, 'could not build voice fingerprint'
    return emb, None


def is_enrolled() -> bool:
    if not PROFILE_PATH.exists():
        return False
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
        return bool(data.get('embeddings'))
    except (json.JSONDecodeError, OSError):
        return False


def _load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {'embeddings': [], 'sample_count': 0}
    return json.loads(PROFILE_PATH.read_text(encoding='utf-8'))


def _save_profile(profile: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding='utf-8')


def enroll_audio_paths(paths: list[str]) -> dict:
    """Add one or more enrollment clips; returns status dict."""
    if not is_available():
        return {'ok': False, 'error': 'librosa not installed. Run: pip install librosa soundfile'}

    added = 0
    vectors = []
    failures = []
    for i, path in enumerate(paths):
        emb, err = _wav_embedding(path)
        if emb is not None:
            vectors.append(emb.tolist())
            added += 1
        else:
            failures.append({'clip': i + 1, 'reason': err or 'unknown'})

    if not vectors:
        detail = failures[0]['reason'] if failures else 'no clips received'
        return {
            'ok': False,
            'error': f'No usable audio in enrollment clips. {detail}',
            'failures': failures,
        }

    profile = _load_profile()
    profile['embeddings'] = vectors
    profile['sample_count'] = added
    profile['engine'] = 'librosa_mfcc'
    _save_profile(profile)
    out = {'ok': True, 'samples': added, 'enrolled': True}
    if failures:
        out['skipped'] = failures
    return out


def verify_audio_path(audio_path: str) -> tuple[bool, float]:
    """Return (match, similarity score 0–1)."""
    if not is_enrolled():
        return False, 0.0
    emb, _err = _wav_embedding(audio_path)
    if emb is None:
        return False, 0.0

    profile = _load_profile()
    stored = [np.array(v, dtype=np.float32) for v in profile.get('embeddings', [])]
    if not stored:
        return False, 0.0

    scores = [float(np.dot(emb, ref)) for ref in stored]
    best = max(scores)
    return best >= similarity_threshold(), best


def auth_status(memory=None) -> dict:
    from src.audio_util import _ffmpeg_available

    status = {
        'voice_auth_enabled': voice_auth_enabled(),
        'voice_auth_available': is_available(),
        'voice_enrolled': is_enrolled(),
        'threshold': similarity_threshold(),
        'engine': 'librosa_mfcc',
        'ffmpeg_available': _ffmpeg_available(),
    }
    if memory is not None:
        status['session_identified'] = memory.is_session_identified()
        status['is_owner'] = memory.is_owner()
        status['awaiting_voice_wake'] = memory.is_awaiting_voice_wake()
        status['voice_verified'] = memory.is_voice_verified()
    return status
