"""Latency tuning — read BERU_FAST=1 or per-stage env vars."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = '0') -> bool:
    return os.getenv(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


def fast_mode() -> bool:
    return _truthy('BERU_FAST', '0')


def debug_timing() -> bool:
    return _truthy('BERU_DEBUG_TIMING', '0')


def whisper_beam_size() -> int:
    if os.getenv('BERU_WHISPER_BEAM_SIZE'):
        return max(1, int(os.getenv('BERU_WHISPER_BEAM_SIZE', '5')))
    return 1 if fast_mode() else 3


def whisper_vad_filter() -> bool:
    if os.getenv('BERU_WHISPER_VAD') is not None:
        return _truthy('BERU_WHISPER_VAD', '1')
    return not fast_mode()


def ollama_num_predict_short() -> int:
    if os.getenv('BERU_OLLAMA_NUM_PREDICT_SHORT'):
        return int(os.getenv('BERU_OLLAMA_NUM_PREDICT_SHORT', '100'))
    return 60 if fast_mode() else 80


def ollama_context_messages() -> int:
    if os.getenv('BERU_OLLAMA_CONTEXT_MESSAGES'):
        return int(os.getenv('BERU_OLLAMA_CONTEXT_MESSAGES', '8'))
    return 6 if fast_mode() else 8


def computer_brain_nlu_enabled() -> bool:
    if os.getenv('BERU_COMPUTER_BRAIN_NLU') is not None:
        return _truthy('BERU_COMPUTER_BRAIN_NLU', '1')
    return not fast_mode()


def scrape_timeout_ms() -> int:
    if os.getenv('BERU_SCRAPE_TIMEOUT_MS'):
        return int(os.getenv('BERU_SCRAPE_TIMEOUT_MS', '12000'))
    return 8000 if fast_mode() else 12000
