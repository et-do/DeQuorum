"""per-query settlements (the payout ledger)

Revision ID: 0006_settlements
Revises: 0005_message_feedback
Create Date: 2026-06-14

One row per settled answer: the revenue split computed by
`economics.settlement.settle_query` from the answer's grounding set + feedback.
Keyed by message_id (one settlement per answer; re-settling upserts). Contributor
and reviewer payouts are stored as JSON maps; the role totals as columns.

Money is DOUBLE PRECISION here to mirror the float-based CostModel of the
prototype; production hardening should move to integer minor units (cents) or
NUMERIC to avoid float drift. Cascades with the message it settles.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_settlements"
down_revision: str | Sequence[str] | None = "0005_message_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE settlements (
            message_id        TEXT PRIMARY KEY
                                 REFERENCES chat_messages(message_id) ON DELETE CASCADE,
            session_id        TEXT NOT NULL,
            revenue           DOUBLE PRECISION NOT NULL,
            quality_factor    DOUBLE PRECISION NOT NULL,
            contributors_json TEXT NOT NULL,
            reviewers_json    TEXT NOT NULL,
            host              DOUBLE PRECISION NOT NULL,
            operator          DOUBLE PRECISION NOT NULL,
            treasury          DOUBLE PRECISION NOT NULL,
            created_at        BIGINT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_settlements_session ON settlements(session_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS settlements")
