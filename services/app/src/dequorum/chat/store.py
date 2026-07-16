"""Postgres-backed store for chat sessions + messages.

Mirrors the construction pattern used by other stores in this package —
takes an explicit `psycopg.Connection`, or opens its own standalone
connection in no-arg mode for tests / quick scripts.
"""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass
from types import TracebackType

import psycopg

ROLE_USER = "user"
ROLE_NETWORK = "network"
_VALID_ROLES = {ROLE_USER, ROLE_NETWORK}

# Per-answer feedback is a thumbs signal: +1 helpful / -1 not. This is the quality
# ground truth the reliance-grounded payout measure reads — the grounding set is on
# the message, so rating -> message -> contributions (see build-direction.md).
VALID_FEEDBACK = (-1, 1)

DEFAULT_TITLE = "New chat"


@dataclass
class ChatSession:
    session_id: str
    contributor_id: str
    title: str
    created_at: int
    updated_at: int


@dataclass
class ChatMessage:
    message_id: str
    session_id: str
    role: str
    content: str
    response: dict | None
    created_at: int
    sequence_number: int


@dataclass(frozen=True, slots=True)
class MessageFeedback:
    message_id: str
    contributor_id: str
    rating: int  # -1 or +1
    comment: str | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class SettlementRecord:
    """Persisted payout for one answer (see economics.settlement.Settlement).
    Stored here keyed by message_id; the orchestration in economics.ledger builds
    it and passes primitives, so this store stays decoupled from economics."""

    message_id: str
    session_id: str
    revenue: float
    quality_factor: float
    contributors: dict[str, float]  # contributor_id -> payout
    reviewers: dict[str, float]
    host: float
    operator: float
    treasury: float
    created_at: int


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


class ChatStore:
    def __init__(self, conn: psycopg.Connection | None = None) -> None:
        if conn is None:
            from dequorum.db import resolve_database_url

            self._conn = psycopg.connect(resolve_database_url(), autocommit=True)
            self._owns_conn = True
        else:
            self._conn = conn
            self._owns_conn = False

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()
            self._owns_conn = False

    def __enter__(self) -> ChatStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- sessions ---

    def create_session(
        self,
        contributor_id: str,
        title: str = DEFAULT_TITLE,
    ) -> ChatSession:
        now = int(time.time())
        session_id = _new_id("ses")
        self._conn.execute(
            "INSERT INTO chat_sessions "
            "(session_id, contributor_id, title, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (session_id, contributor_id, title, now, now),
        )
        return ChatSession(
            session_id=session_id,
            contributor_id=contributor_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def get_session(self, session_id: str) -> ChatSession | None:
        row = self._conn.execute(
            "SELECT session_id, contributor_id, title, created_at, updated_at "
            "FROM chat_sessions WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        return _row_to_session(row) if row else None

    def list_sessions(self, contributor_id: str) -> list[ChatSession]:
        rows = self._conn.execute(
            "SELECT session_id, contributor_id, title, created_at, updated_at "
            "FROM chat_sessions WHERE contributor_id = %s "
            "ORDER BY updated_at DESC",
            (contributor_id,),
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        result = self._conn.execute(
            "DELETE FROM chat_sessions WHERE session_id = %s",
            (session_id,),
        )
        return (result.rowcount or 0) > 0

    def set_session_title(self, session_id: str, title: str) -> None:
        self._conn.execute(
            "UPDATE chat_sessions SET title = %s, updated_at = %s "
            "WHERE session_id = %s",
            (title, int(time.time()), session_id),
        )

    def touch_session(self, session_id: str) -> None:
        self._conn.execute(
            "UPDATE chat_sessions SET updated_at = %s WHERE session_id = %s",
            (int(time.time()), session_id),
        )

    # --- messages ---

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        response: dict | None = None,
    ) -> ChatMessage:
        if role not in _VALID_ROLES:
            raise ValueError(f"invalid chat role: {role!r}")
        now = int(time.time())
        message_id = _new_id("msg")
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_number), -1) + 1 "
            "FROM chat_messages WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        seq = int(row[0]) if row else 0
        response_json = json.dumps(response) if response is not None else None
        self._conn.execute(
            "INSERT INTO chat_messages "
            "(message_id, session_id, role, content, response_json, "
            " created_at, sequence_number) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (message_id, session_id, role, content, response_json, now, seq),
        )
        self.touch_session(session_id)
        return ChatMessage(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            response=response,
            created_at=now,
            sequence_number=seq,
        )

    def list_messages(self, session_id: str) -> list[ChatMessage]:
        rows = self._conn.execute(
            "SELECT message_id, session_id, role, content, response_json, "
            "created_at, sequence_number "
            "FROM chat_messages WHERE session_id = %s "
            "ORDER BY sequence_number",
            (session_id,),
        ).fetchall()
        return [_row_to_message(r) for r in rows]

    def get_message(self, message_id: str) -> ChatMessage | None:
        row = self._conn.execute(
            "SELECT message_id, session_id, role, content, response_json, "
            "created_at, sequence_number "
            "FROM chat_messages WHERE message_id = %s",
            (message_id,),
        ).fetchone()
        return _row_to_message(row) if row else None

    # --- per-answer feedback (the quality signal for attribution/payout) ---

    def set_feedback(
        self,
        message_id: str,
        contributor_id: str,
        rating: int,
        comment: str | None = None,
    ) -> MessageFeedback:
        """Record or update a user's rating of a network answer. Upserts so a user
        can change their mind; `created_at` is preserved across updates."""
        if rating not in VALID_FEEDBACK:
            raise ValueError(
                f"invalid feedback rating {rating!r}; expected one of {VALID_FEEDBACK}"
            )
        now = int(time.time())
        self._conn.execute(
            "INSERT INTO message_feedback "
            "(message_id, contributor_id, rating, comment, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (message_id, contributor_id) DO UPDATE SET "
            "rating = EXCLUDED.rating, comment = EXCLUDED.comment, "
            "updated_at = EXCLUDED.updated_at",
            (message_id, contributor_id, rating, comment, now, now),
        )
        fb = self.get_feedback(message_id, contributor_id)
        assert fb is not None
        return fb

    def get_feedback(
        self, message_id: str, contributor_id: str
    ) -> MessageFeedback | None:
        row = self._conn.execute(
            "SELECT message_id, contributor_id, rating, comment, created_at, "
            "updated_at FROM message_feedback "
            "WHERE message_id = %s AND contributor_id = %s",
            (message_id, contributor_id),
        ).fetchone()
        return _row_to_feedback(row) if row else None

    def feedback_summary(self, message_id: str) -> dict:
        """Aggregate rating for an answer — what the payout layer reads as the
        quality signal: net = sum of ±1 ratings, count = number of raters."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(rating), 0), COUNT(*) "
            "FROM message_feedback WHERE message_id = %s",
            (message_id,),
        ).fetchone()
        assert row is not None
        return {"net": int(row[0]), "count": int(row[1])}

    # --- settlement ledger (the payout for an answer) ---

    def record_settlement(
        self,
        message_id: str,
        session_id: str,
        *,
        revenue: float,
        quality_factor: float,
        contributors: dict[str, float],
        reviewers: dict[str, float],
        host: float,
        operator: float,
        treasury: float,
    ) -> SettlementRecord:
        """Persist (or re-persist) the payout split for an answer. Idempotent per
        message_id, so re-settling overwrites."""
        now = int(time.time())
        self._conn.execute(
            "INSERT INTO settlements (message_id, session_id, revenue, "
            "quality_factor, contributors_json, reviewers_json, host, operator, "
            "treasury, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (message_id) DO UPDATE SET "
            "session_id = EXCLUDED.session_id, revenue = EXCLUDED.revenue, "
            "quality_factor = EXCLUDED.quality_factor, "
            "contributors_json = EXCLUDED.contributors_json, "
            "reviewers_json = EXCLUDED.reviewers_json, host = EXCLUDED.host, "
            "operator = EXCLUDED.operator, treasury = EXCLUDED.treasury, "
            "created_at = EXCLUDED.created_at",
            (
                message_id,
                session_id,
                revenue,
                quality_factor,
                json.dumps(contributors),
                json.dumps(reviewers),
                host,
                operator,
                treasury,
                now,
            ),
        )
        rec = self.get_settlement(message_id)
        assert rec is not None
        return rec

    def get_settlement(self, message_id: str) -> SettlementRecord | None:
        row = self._conn.execute(
            "SELECT message_id, session_id, revenue, quality_factor, "
            "contributors_json, reviewers_json, host, operator, treasury, "
            "created_at FROM settlements WHERE message_id = %s",
            (message_id,),
        ).fetchone()
        return _row_to_settlement(row) if row else None

    def list_settlements(self, session_id: str) -> list[SettlementRecord]:
        """The payout journal for a session, oldest-first (uses
        idx_settlements_session). The read side of the audit boundary."""
        rows = self._conn.execute(
            "SELECT message_id, session_id, revenue, quality_factor, "
            "contributors_json, reviewers_json, host, operator, treasury, "
            "created_at FROM settlements WHERE session_id = %s "
            "ORDER BY created_at, message_id",
            (session_id,),
        ).fetchall()
        return [_row_to_settlement(r) for r in rows]

    def __iter__(self) -> Iterator[ChatSession]:
        # Convenience: iterate over all sessions (newest-first across all
        # contributors). Useful for fixture inspection.
        rows = self._conn.execute(
            "SELECT session_id, contributor_id, title, created_at, updated_at "
            "FROM chat_sessions ORDER BY updated_at DESC"
        ).fetchall()
        return iter(_row_to_session(r) for r in rows)


def _row_to_session(row: tuple) -> ChatSession:
    return ChatSession(
        session_id=row[0],
        contributor_id=row[1],
        title=row[2],
        created_at=int(row[3]),
        updated_at=int(row[4]),
    )


def _row_to_message(row: tuple) -> ChatMessage:
    response_json = row[4]
    response = json.loads(response_json) if response_json else None
    return ChatMessage(
        message_id=row[0],
        session_id=row[1],
        role=row[2],
        content=row[3],
        response=response,
        created_at=int(row[5]),
        sequence_number=int(row[6]),
    )


def _row_to_feedback(row: tuple) -> MessageFeedback:
    return MessageFeedback(
        message_id=row[0],
        contributor_id=row[1],
        rating=int(row[2]),
        comment=row[3],
        created_at=int(row[4]),
        updated_at=int(row[5]),
    )


def _row_to_settlement(row: tuple) -> SettlementRecord:
    return SettlementRecord(
        message_id=row[0],
        session_id=row[1],
        revenue=float(row[2]),
        quality_factor=float(row[3]),
        contributors=json.loads(row[4]),
        reviewers=json.loads(row[5]),
        host=float(row[6]),
        operator=float(row[7]),
        treasury=float(row[8]),
        created_at=int(row[9]),
    )
