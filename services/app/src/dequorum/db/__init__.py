"""Postgres connection pool, schema migrations, and per-store connection helpers.

The whole app talks to a single Postgres database. A `psycopg_pool.ConnectionPool`
is created once at startup and shared across requests. Stores take a `Connection`
borrowed from the pool, do their work inside a transaction, and the caller is
responsible for returning the connection to the pool (the `open_*_store` context
managers below handle this).

Schema lives in Alembic migrations under `dequorum.db.migrations`. The app
runs `alembic upgrade head` on startup (see `dequorum.db.migrate.upgrade_to_head`)
so a fresh Postgres database becomes ready-to-use without any manual step.
"""

from __future__ import annotations

from dequorum.db.pool import (
    DEFAULT_DATABASE_URL,
    close_pool,
    get_pool,
    init_pool,
    open_category_store,
    open_contribution_store,
    open_identity_store,
    resolve_database_url,
)

__all__ = [
    "DEFAULT_DATABASE_URL",
    "close_pool",
    "get_pool",
    "init_pool",
    "open_category_store",
    "open_contribution_store",
    "open_identity_store",
    "resolve_database_url",
]
