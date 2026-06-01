"""Per-browser API session state (identity gate, chat history) for multi-device Netlify use."""

from __future__ import annotations

import threading
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

_client_session_id: ContextVar[Optional[str]] = ContextVar('tild_client_session_id', default=None)


@dataclass
class ClientState:
    session: dict
    conversation_history: list


class ClientSessionStore:
    """One identity + conversation history per X-Tild-Session-Id / session_id."""

    def __init__(self, memory):
        self._memory = memory
        self._lock = threading.Lock()
        self._by_id: dict[str, ClientState] = {}

    def get(self, session_id: str) -> ClientState:
        sid = (session_id or '').strip()
        if not sid:
            raise ValueError('empty client session id')
        with self._lock:
            if sid not in self._by_id:
                session = self._memory._empty_session()
                if self._memory.is_owner_permanently_verified():
                    session['awaiting_owner_confirm'] = True
                self._by_id[sid] = ClientState(session=session, conversation_history=[])
            return self._by_id[sid]

    def clear_session(self, session_id: str, *, clear_history: bool = True) -> ClientState:
        """Reset identity gate for this browser (e.g. POST /clear)."""
        state = self.get(session_id)
        prev_doc_id = state.session.get('active_document_id')
        prev_doc_name = state.session.get('active_document_name')
        state.session = self._memory._empty_session()
        if prev_doc_id:
            state.session['active_document_id'] = prev_doc_id
            state.session['active_document_name'] = prev_doc_name
        if self._memory.is_owner_permanently_verified():
            state.session['awaiting_owner_confirm'] = True
        if clear_history:
            state.conversation_history = []
        return state


def get_bound_client_session_id() -> Optional[str]:
    return _client_session_id.get()


def bind_client_session(session_id: Optional[str]):
    """Return a context token; call reset_client_session(token) when done."""
    sid = (session_id or '').strip() or None
    return _client_session_id.set(sid)


def reset_client_session(token) -> None:
    _client_session_id.reset(token)
