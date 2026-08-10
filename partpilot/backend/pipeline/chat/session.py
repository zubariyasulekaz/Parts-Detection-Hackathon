"""In-memory chat sessions.

A session is the server's memory of one conversation: the candidates it
started from, the answers given so far, and the question currently on the
table. Sessions live in process memory — appropriate for a single-worker
deployment and this catalog's size; a multi-worker deployment would move
this behind Redis or the database without changing the interface.

The store is bounded (oldest sessions evicted past `MAX_SESSIONS`) and
sessions expire after `SESSION_TTL_SECONDS` of inactivity, so an abandoned
browser tab cannot grow the process forever.
"""

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from backend.core.exceptions import ChatSessionNotFound
from backend.pipeline.chat.engine import Answer, ChatCandidate, Question

MAX_SESSIONS = 1000
SESSION_TTL_SECONDS = 6 * 60 * 60


@dataclass
class ChatTurn:
    """One completed exchange: what was asked, and what the user did about it.

    A skip ("Not sure") is a turn like any other — it happened, it is part of
    the transcript, and it changes what gets asked next. Keeping answers and
    skips in one ordered list is what lets the client replay the conversation
    in the order it actually occurred.
    """

    facet: str
    prompt: str
    #: The chosen option, or None when the user skipped this question.
    answer: Answer | None = None

    @property
    def skipped(self) -> bool:
        return self.answer is None

    @property
    def label(self) -> str:
        return self.answer.label if self.answer is not None else "Not sure"


@dataclass
class ChatSession:
    """One conversation's server-side state."""

    session_id: str
    #: Ranked by similarity, best first — the order mismatch detection relies on.
    candidates: list[ChatCandidate]
    #: Every exchange so far, in order — answers and skips alike.
    turns: list[ChatTurn] = field(default_factory=list)
    #: The question currently offered, so an answer can be validated against
    #: exactly what was asked rather than trusting the client.
    current_question: Question | None = None
    last_touched: float = field(default_factory=time.monotonic)

    @property
    def answers(self) -> list[Answer]:
        """Only the turns that narrowed the field — what the engine filters on."""
        return [turn.answer for turn in self.turns if turn.answer is not None]

    @property
    def skipped(self) -> list[str]:
        """Facets the user said "Not sure" to — never asked again."""
        return [turn.facet for turn in self.turns if turn.answer is None]


class ChatSessionStore:
    """Thread-safe bounded store of active chat sessions."""

    def __init__(self) -> None:
        self._sessions: OrderedDict[str, ChatSession] = OrderedDict()
        self._lock = threading.Lock()

    def create(self, candidates: list[ChatCandidate]) -> ChatSession:
        session = ChatSession(session_id=uuid.uuid4().hex, candidates=candidates)
        with self._lock:
            self._prune()
            self._sessions[session.session_id] = session
            while len(self._sessions) > MAX_SESSIONS:
                self._sessions.popitem(last=False)
        return session

    def get(self, session_id: str) -> ChatSession:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                raise ChatSessionNotFound(f"Chat session {session_id!r} does not exist or has expired.")
            session.last_touched = time.monotonic()
            self._sessions.move_to_end(session_id)
            return session

    def _prune(self) -> None:
        """Drop sessions idle past the TTL. Caller holds the lock."""
        cutoff = time.monotonic() - SESSION_TTL_SECONDS
        expired = [sid for sid, s in self._sessions.items() if s.last_touched < cutoff]
        for sid in expired:
            del self._sessions[sid]
