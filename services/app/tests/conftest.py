"""Shared pytest fixtures.

Test isolation strategy:

  - Session-scoped pool against the compose `db` service's `dequorum_test`
    database. Migrations are applied once at session start.
  - Function-scoped `autouse` fixture truncates all tables before each test.
    Tests can construct `ContributionStore()` / `IdentityStore()` /
    `CategoryStore()` with no arguments and get a clean DB; the no-arg form
    auto-borrows a connection from the pool with autocommit=True (see the
    store classes' module docstrings).

Override `DEQUORUM_TEST_DATABASE_URL` to point at a different test database
(e.g. for local non-compose dev). Default works inside the compose `app`
container.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from hypothesis import settings

from dequorum.db import close_pool, get_pool, init_pool
from dequorum.db.migrate import upgrade_to_head

settings.register_profile("default", max_examples=50, deadline=None)
settings.load_profile("default")


_TEST_DATABASE_URL = os.environ.get(
    "DEQUORUM_TEST_DATABASE_URL",
    "postgresql://dequorum_app:dev-only-not-for-prod@db:5432/dequorum_test",
)

# Truncation order is irrelevant with CASCADE, but listing every user-defined
# table makes "what's in the DB" explicit. Keep in sync with the Alembic
# migration in dequorum/db/migrations/versions/.
_USER_TABLES = (
    "votes",
    "contributions",
    "contribution_lineages",
    "categories",
    "contributors",
    "agreements",
)


@pytest.fixture(scope="session", autouse=True)
def _pg_pool() -> Iterator[None]:
    """Initialize the connection pool + run migrations once per test session."""
    init_pool(_TEST_DATABASE_URL)
    upgrade_to_head(_TEST_DATABASE_URL)
    yield
    close_pool()


@pytest.fixture(autouse=True)
def _truncate_between_tests() -> Iterator[None]:
    """Wipe all user tables before each test for isolation."""
    pool = get_pool()
    truncate_sql = f"TRUNCATE TABLE {', '.join(_USER_TABLES)} RESTART IDENTITY CASCADE"
    with pool.connection() as conn:
        conn.execute(truncate_sql)
    yield


@pytest.fixture
def db_conn() -> Iterator[object]:
    """Per-test connection from the pool (for tests that want explicit control).

    Most tests don't need this — they use the no-arg store constructors and
    rely on the autouse truncation fixture for isolation. Use `db_conn` when
    you specifically need to share a connection across multiple stores in one
    test to observe transactional semantics.
    """
    pool = get_pool()
    with pool.connection() as conn:
        yield conn
