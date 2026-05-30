"""SQLite-backed store for signed contributions."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from ai_playground.contributions import Contribution
from ai_playground.core.node import Signature

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contributions (
    contribution_id TEXT PRIMARY KEY,
    expert_id TEXT NOT NULL,
    contributor_id TEXT NOT NULL,
    text TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    sig_node_id TEXT NOT NULL,
    sig_input_hash TEXT NOT NULL,
    sig_output_hash TEXT NOT NULL,
    sig_digest TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contributions_expert ON contributions(expert_id);
"""


class ContributionStore:
    """CRUD over contributions. In-memory by default; pass a path for file-backed."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> ContributionStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def add(self, c: Contribution) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO contributions
                (contribution_id, expert_id, contributor_id, text, citations_json,
                 sig_node_id, sig_input_hash, sig_output_hash, sig_digest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    c.contribution_id,
                    c.expert_id,
                    c.contributor_id,
                    c.text,
                    json.dumps(list(c.citations)),
                    c.signature.node_id,
                    c.signature.input_hash,
                    c.signature.output_hash,
                    c.signature.digest,
                ),
            )

    def get(self, contribution_id: str) -> Contribution | None:
        row = self._conn.execute(
            "SELECT * FROM contributions WHERE contribution_id = ?",
            (contribution_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_expert(self, expert_id: str) -> list[Contribution]:
        rows = self._conn.execute(
            "SELECT * FROM contributions WHERE expert_id = ? ORDER BY contribution_id",
            (expert_id,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def __iter__(self) -> Iterator[Contribution]:
        rows = self._conn.execute(
            "SELECT * FROM contributions ORDER BY contribution_id"
        ).fetchall()
        return iter(_row_to_contribution(r) for r in rows)

    def __len__(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM contributions").fetchone()[0]
        )


def _row_to_contribution(row: tuple) -> Contribution:
    return Contribution(
        contribution_id=row[0],
        expert_id=row[1],
        contributor_id=row[2],
        text=row[3],
        citations=tuple(json.loads(row[4])),
        signature=Signature(
            node_id=row[5],
            input_hash=row[6],
            output_hash=row[7],
            digest=row[8],
        ),
    )
