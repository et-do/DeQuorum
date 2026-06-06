"""categories carry personas; drop expert_id from contributions

Revision ID: 0004_categories_carry_personas
Revises: 0003_comments
Create Date: 2026-06-06

Collapses the Expert layer into the Category taxonomy. Persona
metadata that used to live on Expert (system prompt, specialty tags,
example questions) now lives directly on the Category that the
contributions for that domain are filed under. Routing picks a
category; the category carries the prompt; the contribution chain is
already grounded in the same category.

Reasoning for the merge: at the v0.1 seed scale, every Expert was
isomorphic to exactly one leaf Category. The two-layer structure
introduced ceremony without earning it. Hierarchical Categories
already represent the same domain organization with parent-child
relationships, so promoting the persona onto Category collapses two
concepts into one.

Schema changes:
  - categories.system_prompt        TEXT NOT NULL DEFAULT ''
  - categories.specialty_tags_json  TEXT NOT NULL DEFAULT '[]'
  - categories.example_questions_json TEXT NOT NULL DEFAULT '[]'
  - contributions: DROP COLUMN expert_id
  - contributions: DROP INDEX idx_contributions_expert
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_categories_carry_personas"
down_revision: str | Sequence[str] | None = "0003_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE categories ADD COLUMN system_prompt TEXT NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE categories "
        "ADD COLUMN specialty_tags_json TEXT NOT NULL DEFAULT '[]'"
    )
    op.execute(
        "ALTER TABLE categories "
        "ADD COLUMN example_questions_json TEXT NOT NULL DEFAULT '[]'"
    )

    # Drop expert routing key. `primary_category_id` is now the only
    # domain key on a contribution; routing returns category ids
    # directly.
    op.execute("DROP INDEX IF EXISTS idx_contributions_expert")
    op.execute("ALTER TABLE contributions DROP COLUMN IF EXISTS expert_id")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE contributions ADD COLUMN expert_id TEXT NOT NULL DEFAULT 'unknown'"
    )
    op.execute("CREATE INDEX idx_contributions_expert ON contributions(expert_id)")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS example_questions_json")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS specialty_tags_json")
    op.execute("ALTER TABLE categories DROP COLUMN IF EXISTS system_prompt")
