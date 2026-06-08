"""Append Netlify / guest chats to disk for training data review."""

import os
import re
from datetime import datetime
from pathlib import Path

_DEFAULT_DIR = Path(__file__).resolve().parent.parent / 'data' / 'collected_conversations'


def collection_enabled():
    return os.getenv('BERU_COLLECT_CONVERSATIONS', '1').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )


def _enabled():
    return collection_enabled()


def _exclude_owner():
    return os.getenv('BERU_COLLECT_EXCLUDE_OWNER', '1').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )


def collect_dir():
    raw = (os.getenv('BERU_COLLECT_DIR') or '').strip()
    return Path(raw) if raw else _DEFAULT_DIR


def _safe_session_id(session_id):
    sid = (session_id or 'anonymous').strip()
    sid = re.sub(r'[^\w.\-]+', '_', sid)[:120]
    return sid or 'anonymous'


def _session_path(session_id):
    return collect_dir() / f'{_safe_session_id(session_id)}.txt'


def _write_header(path, *, session_id, memory, source, new_chat):
    user_label = 'unknown'
    if memory:
        user_label = (
            memory.get_user_full_name()
            or memory.get_user_name()
            or ('Omar (owner)' if memory.is_owner() else 'unknown')
        )
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    with path.open('a', encoding='utf-8') as f:
        if new_chat and size > 0:
            f.write('\n--- new chat ---\n\n')
        if size == 0:
            f.write(
                f'# session_id: {session_id}\n'
                f'# user: {user_label}\n'
                f'# started: {datetime.now().isoformat(timespec="seconds")}\n'
                f'# format: user: / beru: (one pair per turn)\n'
                f'# label good/bad by moving this file under good/ or bad/ when done\n\n'
            )
        if source:
            f.write(f'# last_source: {source}\n\n')


def collect_turn(
    *,
    session_id,
    user_message,
    beru_response,
    memory=None,
    source=None,
    new_chat=False,
):
    """
  Append one exchange. Skips empty text and optionally skips Omar (owner).
    """
    if not _enabled():
        return None

    if memory and _exclude_owner() and memory.is_owner():
        return None

    user_message = (user_message or '').strip()
    beru_response = (beru_response or '').strip()
    if not user_message and not beru_response:
        return None

    directory = collect_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _session_path(session_id)

    if not path.exists() or new_chat:
        _write_header(
            path,
            session_id=session_id,
            memory=memory,
            source=source,
            new_chat=new_chat and path.exists(),
        )

    block = ''
    if user_message:
        block += f'user: {user_message}\n'
    if beru_response:
        block += f'beru: {beru_response}\n'
    block += '\n'

    with path.open('a', encoding='utf-8') as f:
        f.write(block)

    return str(path)
