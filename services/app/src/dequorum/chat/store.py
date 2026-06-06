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
