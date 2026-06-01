import os
from pathlib import Path

from src.conversation_collector import collect_turn, collect_dir


def test_collect_turn_format(tmp_path, monkeypatch):
    monkeypatch.setenv('TILD_COLLECT_CONVERSATIONS', '1')
    monkeypatch.setenv('TILD_COLLECT_DIR', str(tmp_path))
    monkeypatch.setenv('TILD_COLLECT_EXCLUDE_OWNER', '0')

    path = collect_turn(
        session_id='test-session-1',
        user_message='Hello',
        tild_response='Hi there!',
        source='gate',
    )
    assert path
    text = Path(path).read_text(encoding='utf-8')
    assert 'user: Hello' in text
    assert 'tild: Hi there!' in text
