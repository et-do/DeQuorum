"""Postgres-backed store for the category taxonomy.

See `dequorum.identity.store.IdentityStore` for the two construction
modes (caller-owned connection vs. auto-borrowed-from-pool). Schema is
owned by Alembic migrations under `dequorum.db.migrations`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import TracebackType

import psycopg

from dequorum.taxonomy.category import Category

_COLS = (
    "category_id, parent_id, display_name, description, "
    "system_prompt, specialty_tags_json, example_questions_json"
)


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
            (category_id, parent_id, display_name, description,
             system_prompt, specialty_tags_json, example_questions_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (category_id) DO UPDATE SET
                parent_id              = EXCLUDED.parent_id,
                display_name           = EXCLUDED.display_name,
                description            = EXCLUDED.description,
                system_prompt          = EXCLUDED.system_prompt,
                specialty_tags_json    = EXCLUDED.specialty_tags_json,
                example_questions_json = EXCLUDED.example_questions_json""",
            (
                category.category_id,
                category.parent_id,
                category.display_name,
                category.description,
                category.system_prompt,
                json.dumps(list(category.specialty_tags)),
                json.dumps(list(category.example_questions)),
            ),
        )

    def get(self, category_id: str) -> Category | None:
        row = self._conn.execute(
            f"SELECT {_COLS} FROM categories WHERE category_id = %s",
            (category_id,),
        ).fetchone()
        return _row_to_category(row) if row else None

    def all(self) -> list[Category]:
        rows = self._conn.execute(
            f"SELECT {_COLS} FROM categories ORDER BY category_id"
        ).fetchall()
        return [_row_to_category(r) for r in rows]

    def routable(self) -> list[Category]:
        """Categories that carry a persona — the universe the router
        ranks against. Non-routable categories exist only as
        organizational parents in the taxonomy tree."""
        rows = self._conn.execute(
            f"SELECT {_COLS} FROM categories "
            "WHERE system_prompt <> '' ORDER BY category_id"
        ).fetchall()
        return [_row_to_category(r) for r in rows]

    def children_of(self, category_id: str | None) -> list[Category]:
        if category_id is None:
            rows = self._conn.execute(
                f"SELECT {_COLS} FROM categories "
                "WHERE parent_id IS NULL ORDER BY category_id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"SELECT {_COLS} FROM categories "
                "WHERE parent_id = %s ORDER BY category_id",
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
    specialty_tags = tuple(json.loads(row[5] or "[]"))
    example_questions = tuple(json.loads(row[6] or "[]"))
    return Category(
        category_id=row[0],
        parent_id=row[1],
        display_name=row[2],
        description=row[3] or "",
        system_prompt=row[4] or "",
        specialty_tags=specialty_tags,
        example_questions=example_questions,
    )
