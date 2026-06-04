"""Run Alembic migrations programmatically.

Called from app startup (`dequorum.web.app` lifespan) and from the
`dequorum db upgrade` CLI subcommand. Keeps the migration tooling within
the Python package so there's no separate alembic CLI invocation needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _alembic_config(database_url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    url = database_url or os.environ.get(
        "DEQUORUM_DATABASE_URL",
        "postgresql://dequorum_app:dev-only-not-for-prod@localhost:5432/dequorum",
    )
    # SQLAlchemy maps `postgresql://` to the psycopg2 dialect by default, but
    # we only install psycopg (v3). The `+psycopg` suffix selects the v3
    # dialect. The plain `postgresql://` form keeps working for psycopg3's own
    # pool (which doesn't care about the scheme suffix).
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def upgrade_to_head(database_url: str | None = None) -> None:
    """Run `alembic upgrade head` against the configured database URL."""
    command.upgrade(_alembic_config(database_url), "head")


def downgrade_to_base(database_url: str | None = None) -> None:
    """Run `alembic downgrade base`. Dev/test convenience only."""
    command.downgrade(_alembic_config(database_url), "base")
