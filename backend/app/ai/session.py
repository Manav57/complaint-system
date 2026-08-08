"""In-memory session store for conversational complaint intake.

Same-day-deadline scope: a plain dict keyed by ``session_id`` — no new DB table,
no Redis. Each session accumulates extracted fields and the message history as
the user converses (initial message -> extract workflow, follow-ups -> amend
workflow). Sessions are lost on process restart, which is acceptable for the
demo scope.
"""
import threading
import uuid
from typing import Any

_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

# Bounded store: evict the oldest session when the cap is hit so a long-running
# demo server cannot grow without bound.
_MAX_SESSIONS = 200


def create_session() -> dict:
    """Create a new session and return it (fields + messages empty)."""
    session_id = uuid.uuid4().hex
    session: dict[str, Any] = {"session_id": session_id, "fields": {}, "messages": []}
    with _lock:
        if len(_sessions) >= _MAX_SESSIONS:
            _sessions.pop(next(iter(_sessions)))  # oldest (dicts keep insertion order)
        _sessions[session_id] = session
    return session


def get_session(session_id: str) -> dict | None:
    """Return the session dict or None if it does not exist."""
    with _lock:
        return _sessions.get(session_id)


def update_session_fields(session_id: str, changes: dict) -> dict | None:
    """Merge changed fields into the session, appending nothing to history.

    Returns the session, or None if the session does not exist.
    """
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        session["fields"].update(changes or {})
        return session


def append_message(session_id: str, role: str, text: str) -> None:
    """Append a chat message to the session history (best effort)."""
    with _lock:
        session = _sessions.get(session_id)
        if session is not None:
            session["messages"].append({"role": role, "text": text})
