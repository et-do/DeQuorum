"""chat sessions + messages

Revision ID: 0002_chat
Revises: 0001_initial
Create Date: 2026-06-04

Tables that back the chat UI in `/app/ask`. A session is a thread of
alternating user / network messages tied to a contributor_id (or
"anonymous" when no account is signed up yet).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_chat"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE chat_sessions (
            session_id      TEXT PRIMARY KEY,
            contributor_id  TEXT NOT NULL,
            title           TEXT NOT NULL DEFAULT 'New chat',
            created_at      BIGINT NOT NULL,
            updated_at      BIGINT NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX idx_chat_sessions_contributor "
        "ON chat_sessions(contributor_id, updated_at DESC)"
    )

    op.execute("""
        CREATE TABLE chat_messages (
            message_id      TEXT PRIMARY KEY,
            session_id      TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            role            TEXT NOT NULL CHECK (role IN ('user', 'network')),
            content         TEXT NOT NULL,
            response_json   TEXT,
            created_at      BIGINT NOT NULL,
            sequence_number INTEGER NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX idx_chat_messages_session "
        "ON chat_messages(session_id, sequence_number)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS chat_sessions")
