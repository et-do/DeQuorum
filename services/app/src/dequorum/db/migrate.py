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
    """Run `alembic upgrade head` against the configured database URL.

    Defensive: if the database already has populated tables but the
    `alembic_version` table is empty (a state that previously caused
    container startup to crash with "relation already exists"),
    auto-stamp to the latest revision known to match the existing
    schema before running `upgrade head`. This makes startup
    idempotent across recovery scenarios where alembic state and
    physical schema have drifted.
    """
    cfg = _alembic_config(database_url)
    _heal_alembic_baseline(cfg, database_url)
    command.upgrade(cfg, "head")


def downgrade_to_base(database_url: str | None = None) -> None:
    """Run `alembic downgrade base`. Dev/test convenience only."""
    command.downgrade(_alembic_config(database_url), "base")


# Tables created by each migration, in order. Newest revisions go at
# the end. The auto-heal logic below scans the live DB in reverse order
# and stamps to the latest revision whose tables are all present —
# which is the revision the schema actually represents.
_REV_TABLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "0001_initial",
        (
            "agreements",
            "contributors",
            "categories",
            "contribution_lineages",
            "contributions",
            "votes",
        ),
    ),
    ("0002_chat", ("chat_sessions", "chat_messages")),
    ("0003_comments", ("comments",)),
    # 0004 isn't a new table — it's a column shape change. The heal
    # logic only stamps revisions whose tables fully exist, which is
    # fine: once the app boots and runs `upgrade head`, alembic
    # advances the head normally. We add 0004 here as documentation
    # of the latest known revision; the table tuple is empty so
    # _heal_alembic_baseline never stamps to it directly.
    ("0004_categories_carry_personas", ()),
)


def _heal_alembic_baseline(cfg: Config, database_url: str | None) -> None:
    """If `alembic_version` is empty but schema tables exist, stamp to
    the highest revision whose tables are all present so the next
    `upgrade head` only applies the missing revisions.

    Background: an earlier debugging step wiped `alembic_version`
    without wiping the data tables. On restart, the lifespan tried to
    re-run `0001_initial` and crashed with "relation agreements
    already exists." This stamps the right baseline to unblock that
    case without losing data.
    """
    import psycopg

    from dequorum.db.pool import resolve_database_url

    url = resolve_database_url(database_url)
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            row = conn.execute(
                "SELECT to_regclass('public.alembic_version')"
            ).fetchone()
            if row is None or row[0] is None:
                # alembic_version table doesn't exist yet — fresh DB,
                # let upgrade create it.
                return
            row = conn.execute("SELECT COUNT(*) FROM alembic_version").fetchone()
            if row is None or int(row[0]) > 0:
                # Already stamped — normal startup path.
                return
            # Empty alembic_version. Walk revisions newest → oldest;
            # stamp to the first revision whose tables are ALL present.
            target: str | None = None
            for rev, tables in reversed(_REV_TABLES):
                if not tables:
                    # Schema-shape-only revisions (e.g. column adds /
                    # drops) don't introduce tables we can probe for.
                    # Skip — the heal logic will land on the last
                    # revision that DID introduce tables, and the
                    # subsequent `upgrade head` will replay any pure
                    # column-shape revisions on top.
                    continue
                all_present = all(
                    conn.execute("SELECT to_regclass(%s)", (f"public.{t}",)).fetchone()[
                        0
                    ]
                    is not None
                    for t in tables
                )
                if all_present:
                    target = rev
                    break
            if target is None:
                # No revision's tables match — fresh DB or wildly
                # inconsistent state. Leave alembic_version empty and
                # let upgrade run from base.
                return
            command.stamp(cfg, target)
    except Exception:
        # Heal step is best-effort. If anything goes wrong we let the
        # caller's `upgrade head` produce the real error message.
        pass
