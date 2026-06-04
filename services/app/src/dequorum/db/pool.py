"""Module-level connection pool + per-store context managers.

The pool is lazily created on first `get_pool()` call and torn down by
`close_pool()` (called from the FastAPI app lifespan). CLI commands that
only need one connection can use `init_pool()` once at startup and rely
on the pool to be closed at interpreter exit.

Each `open_*_store` context manager checks out a connection, hands it to
the relevant store class, and releases the connection on exit.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from psycopg_pool import ConnectionPool

if TYPE_CHECKING:
    from psycopg import Connection

    from dequorum.identity.store import IdentityStore
    from dequorum.knowledge.store import ContributionStore
    from dequorum.taxonomy.store import CategoryStore


DEFAULT_DATABASE_URL = (
    "postgresql://dequorum_app:dev-only-not-for-prod@localhost:5432/dequorum"
)


_pool: ConnectionPool | None = None


def init_pool(database_url: str | None = None) -> ConnectionPool:
    """Initialize (or replace) the module-level pool.

    `database_url=None` reads `DEQUORUM_DATABASE_URL` from the environment,
    falling back to `DEFAULT_DATABASE_URL` for plain `dequorum` CLI use
    against a locally-running compose `db` service.
    """
    global _pool
    url = database_url or os.environ.get("DEQUORUM_DATABASE_URL", DEFAULT_DATABASE_URL)
    if _pool is not None:
        _pool.close()
    _pool = ConnectionPool(conninfo=url, min_size=1, max_size=10, open=True)
    return _pool


def get_pool() -> ConnectionPool:
    """Return the existing pool, creating one from env defaults if needed."""
    if _pool is None:
        return init_pool()
    return _pool


def close_pool() -> None:
    """Close the pool and clear the module reference. Idempotent."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def _connection() -> Iterator[Connection]:
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


@contextmanager
def open_contribution_store() -> Iterator[ContributionStore]:
    from dequorum.knowledge.store import ContributionStore

    with _connection() as conn:
        yield ContributionStore(conn)


@contextmanager
def open_identity_store() -> Iterator[IdentityStore]:
    from dequorum.identity.store import IdentityStore

    with _connection() as conn:
        yield IdentityStore(conn)


@contextmanager
def open_category_store() -> Iterator[CategoryStore]:
    from dequorum.taxonomy.store import CategoryStore

    with _connection() as conn:
        yield CategoryStore(conn)
