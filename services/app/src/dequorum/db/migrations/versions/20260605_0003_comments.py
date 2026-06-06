"""comments on contributions

Revision ID: 0003_comments
Revises: 0002_chat
Create Date: 2026-06-05

Phase 1 of the contribution-governance work — see
docs/architecture/contribution-governance.md.

A `comments` row is a signed, append-only discussion node attached to
a contribution. Comments thread via `parent_comment_id`. Soft
redaction is supported (the row stays; body is hidden in API
responses); hard deletion is not part of the model.

Replacement (the user-facing "edit") is two-step at the table level:
the new comment carries `replaces_comment_id` pointing at the
original, AND the original row's `replaced_by_comment_id` is updated
to point forward. This bidirectional link lets us render strikethrough
on the predecessor without re-walking the table.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_comments"
down_revision: str | Sequence[str] | None = "0002_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE comments (
            comment_id              TEXT PRIMARY KEY,
            contribution_id         TEXT NOT NULL
                                    REFERENCES contributions(contribution_id)
                                    ON DELETE CASCADE,
            parent_comment_id       TEXT
                                    REFERENCES comments(comment_id),
            author_id               TEXT NOT NULL,
            body                    TEXT NOT NULL,
            line_anchor_start       INTEGER,
            line_anchor_end         INTEGER,
            created_at              BIGINT NOT NULL,
            redacted_at             BIGINT,
            redacted_by             TEXT,
            replaces_comment_id     TEXT
                                    REFERENCES comments(comment_id),
            replaced_by_comment_id  TEXT
                                    REFERENCES comments(comment_id),
            sig_node_id             TEXT NOT NULL,
            sig_input_hash          TEXT NOT NULL,
            sig_output_hash         TEXT NOT NULL,
            sig_digest              TEXT NOT NULL,
            CONSTRAINT line_anchor_pair CHECK (
                (line_anchor_start IS NULL AND line_anchor_end IS NULL)
                OR (line_anchor_start IS NOT NULL AND line_anchor_end IS NOT NULL
                    AND line_anchor_start >= 1
                    AND line_anchor_end >= line_anchor_start)
            ),
            CONSTRAINT redaction_pair CHECK (
                (redacted_at IS NULL AND redacted_by IS NULL)
                OR (redacted_at IS NOT NULL AND redacted_by IS NOT NULL)
            )
        )
    """)
    op.execute(
        "CREATE INDEX idx_comments_contribution "
        "ON comments(contribution_id, created_at)"
    )
    op.execute(
        "CREATE INDEX idx_comments_parent "
        "ON comments(parent_comment_id) "
        "WHERE parent_comment_id IS NOT NULL"
    )
    op.execute("CREATE INDEX idx_comments_author ON comments(author_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS comments")
