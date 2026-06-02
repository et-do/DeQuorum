"""SQLite-backed store for the category taxonomy."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from dequorum.taxonomy.category import Category

_TABLES = """
CREATE TABLE IF NOT EXISTS categories (
    category_id   TEXT PRIMARY KEY,
    parent_id     TEXT,
    display_name  TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (parent_id) REFERENCES categories(category_id)
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
"""


class CategoryStore:
    """SQLite-backed CRUD over the category taxonomy."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_TABLES)
        self._conn.executescript(_INDEXES)

    def close(self) -> None:
        self._conn.close()

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
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO categories "
                "(category_id, parent_id, display_name, description) "
                "VALUES (?, ?, ?, ?)",
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
            "FROM categories WHERE category_id = ?",
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
                "FROM categories WHERE parent_id = ? ORDER BY category_id",
                (category_id,),
            ).fetchall()
        return [_row_to_category(r) for r in rows]

    def __iter__(self) -> Iterator[Category]:
        return iter(self.all())

    def __len__(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0])

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
