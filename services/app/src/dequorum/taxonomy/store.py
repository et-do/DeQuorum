"""Postgres-backed store for the category taxonomy.

See `dequorum.identity.store.IdentityStore` for the two construction
modes (caller-owned connection vs. auto-borrowed-from-pool). Schema is
owned by Alembic migrations under `dequorum.db.migrations`.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType

import psycopg

from dequorum.taxonomy.category import Category


class CategoryStore:
    """CRUD over the category taxonomy."""

    def __init__(self, conn: psycopg.Connection | None = None) -> None:
        if conn is None:
            from dequorum.db import resolve_database_url

            self._conn = psycopg.connect(resolve_database_url(), autocommit=True)
            self._owns_conn = True
        else:
            self._conn = conn
            self._owns_conn = False

    def close(self) -> None:
        if self._owns_conn:
            self._conn.close()
            self._owns_conn = False

    def __enter__(self) -> CategoryStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def add(self, category: Category) -> None:
        self._conn.execute(
            """INSERT INTO categories
            (category_id, parent_id, display_name, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (category_id) DO UPDATE SET
                parent_id    = EXCLUDED.parent_id,
                display_name = EXCLUDED.display_name,
                description  = EXCLUDED.description""",
            (
                category.category_id,
                category.parent_id,
                category.display_name,
                category.description,
            ),
        )

    def get(self, category_id: str) -> Category | None:
        row = self._conn.execute(
            "SELECT category_id, parent_id, display_name, description "
            "FROM categories WHERE category_id = %s",
            (category_id,),
        ).fetchone()
        return _row_to_category(row) if row else None

    def all(self) -> list[Category]:
        rows = self._conn.execute(
            "SELECT category_id, parent_id, display_name, description "
            "FROM categories ORDER BY category_id"
        ).fetchall()
        return [_row_to_category(r) for r in rows]

    def children_of(self, category_id: str | None) -> list[Category]:
        if category_id is None:
            rows = self._conn.execute(
                "SELECT category_id, parent_id, display_name, description "
                "FROM categories WHERE parent_id IS NULL ORDER BY category_id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT category_id, parent_id, display_name, description "
                "FROM categories WHERE parent_id = %s ORDER BY category_id",
                (category_id,),
            ).fetchall()
        return [_row_to_category(r) for r in rows]

    def __iter__(self) -> Iterator[Category]:
        return iter(self.all())

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM categories").fetchone()
        assert row is not None
        return int(row[0])

    def __contains__(self, category_id: object) -> bool:
        if not isinstance(category_id, str):
            return False
        return self.get(category_id) is not None


def _row_to_category(row: tuple) -> Category:
    return Category(
        category_id=row[0],
        parent_id=row[1],
        display_name=row[2],
        description=row[3] or "",
    )
