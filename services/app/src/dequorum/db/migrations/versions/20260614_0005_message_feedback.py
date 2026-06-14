"""per-answer feedback

Revision ID: 0005_message_feedback
Revises: 0004_categories_carry_personas
Create Date: 2026-06-14

Captures a user's quality rating on a network answer. This is the quality signal
the faithful credit/payout measure needs (whitepaper §8.6; docs/architecture/
build-direction.md): an answer's grounding set already lives on
`chat_messages.response_json`, so feedback -> message -> grounded contributions
links a rating back to the contributors who shaped the answer. One rating per
(message, contributor), upsertable. Rows cascade-delete with their message.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_message_feedback"
down_revision: str | Sequence[str] | None = "0004_categories_carry_personas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE message_feedback (
            message_id      TEXT NOT NULL REFERENCES chat_messages(message_id) ON DELETE CASCADE,
            contributor_id  TEXT NOT NULL,
            rating          INTEGER NOT NULL CHECK (rating IN (-1, 1)),
            comment         TEXT,
            created_at      BIGINT NOT NULL,
            updated_at      BIGINT NOT NULL,
            PRIMARY KEY (message_id, contributor_id)
        )
    """)
    op.execute(
        "CREATE INDEX idx_message_feedback_message ON message_feedback(message_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS message_feedback")
