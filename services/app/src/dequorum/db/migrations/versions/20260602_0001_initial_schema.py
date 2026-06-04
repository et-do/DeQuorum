"""initial schema: contributors, agreements, categories, contributions, lineages, votes

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-02

Translated from the original SQLite DDL embedded in the store classes:
  - TEXT -> TEXT
  - INTEGER -> INTEGER (or BIGINT where it holds a unix timestamp)
  - BLOB -> BYTEA
  - SQLite's `INSERT OR REPLACE` rewritten in the stores as
    `INSERT ... ON CONFLICT (...) DO UPDATE SET ...` (no schema change needed)
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- identity ---
    op.execute("""
        CREATE TABLE agreements (
            version       TEXT PRIMARY KEY,
            text          TEXT NOT NULL,
            text_hash     TEXT NOT NULL,
            effective_at  BIGINT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE contributors (
            contributor_id        TEXT PRIMARY KEY,
            display_name          TEXT NOT NULL,
            public_key            BYTEA NOT NULL,
            tier                  INTEGER NOT NULL,
            agreement_version     TEXT NOT NULL REFERENCES agreements(version),
            agreement_sig_node    TEXT NOT NULL,
            agreement_sig_input   TEXT NOT NULL,
            agreement_sig_output  TEXT NOT NULL,
            agreement_sig_digest  TEXT NOT NULL,
            email_hash            TEXT,
            created_at            BIGINT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_contributors_tier ON contributors(tier)")
    op.execute("CREATE INDEX idx_contributors_email ON contributors(email_hash)")

    # --- taxonomy ---
    op.execute("""
        CREATE TABLE categories (
            category_id   TEXT PRIMARY KEY,
            parent_id     TEXT REFERENCES categories(category_id),
            display_name  TEXT NOT NULL,
            description   TEXT NOT NULL DEFAULT ''
        )
    """)
    op.execute("CREATE INDEX idx_categories_parent ON categories(parent_id)")

    # --- knowledge ---
    op.execute("""
        CREATE TABLE contribution_lineages (
            lineage_id              TEXT PRIMARY KEY,
            current_contribution_id TEXT,
            created_at              BIGINT NOT NULL DEFAULT 0
        )
    """)
    op.execute("""
        CREATE TABLE contributions (
            contribution_id      TEXT PRIMARY KEY,
            lineage_id           TEXT NOT NULL REFERENCES contribution_lineages(lineage_id),
            version_number       INTEGER NOT NULL DEFAULT 1,
            parent_version       INTEGER,
            expert_id            TEXT NOT NULL,
            contributor_id       TEXT NOT NULL,
            primary_category_id  TEXT NOT NULL DEFAULT 'uncategorized',
            text                 TEXT NOT NULL,
            citations_json       TEXT NOT NULL,
            sig_node_id          TEXT NOT NULL,
            sig_input_hash       TEXT NOT NULL,
            sig_output_hash      TEXT NOT NULL,
            sig_digest           TEXT NOT NULL,
            status               TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    op.execute("CREATE INDEX idx_contributions_expert      ON contributions(expert_id)")
    op.execute("CREATE INDEX idx_contributions_status      ON contributions(status)")
    op.execute(
        "CREATE INDEX idx_contributions_lineage     ON contributions(lineage_id)"
    )
    op.execute(
        "CREATE INDEX idx_contributions_category    ON contributions(primary_category_id)"
    )
    op.execute(
        "CREATE INDEX idx_contributions_contributor ON contributions(contributor_id)"
    )

    op.execute("""
        CREATE TABLE votes (
            vote_id          TEXT PRIMARY KEY,
            contribution_id  TEXT NOT NULL REFERENCES contributions(contribution_id),
            voter_id         TEXT NOT NULL,
            score            INTEGER NOT NULL CHECK (score IN (-1, 0, 1)),
            sig_node_id      TEXT NOT NULL,
            sig_input_hash   TEXT NOT NULL,
            sig_output_hash  TEXT NOT NULL,
            sig_digest       TEXT NOT NULL,
            UNIQUE (contribution_id, voter_id)
        )
    """)
    op.execute("CREATE INDEX idx_votes_contribution ON votes(contribution_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS votes")
    op.execute("DROP TABLE IF EXISTS contributions")
    op.execute("DROP TABLE IF EXISTS contribution_lineages")
    op.execute("DROP TABLE IF EXISTS categories")
    op.execute("DROP TABLE IF EXISTS contributors")
    op.execute("DROP TABLE IF EXISTS agreements")
