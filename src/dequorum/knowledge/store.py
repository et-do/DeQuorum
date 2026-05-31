"""SQLite-backed store for signed contributions, votes, and review status."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from dequorum.core.node import Signature
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.status import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    VALID_STATUSES,
)
from dequorum.review.vote import Vote

__all__ = [
    "STATUS_APPROVED",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "VALID_STATUSES",
    "ContributionStore",
]

_TABLES = """
CREATE TABLE IF NOT EXISTS contributions (
    contribution_id TEXT PRIMARY KEY,
    expert_id TEXT NOT NULL,
    contributor_id TEXT NOT NULL,
    text TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    sig_node_id TEXT NOT NULL,
    sig_input_hash TEXT NOT NULL,
    sig_output_hash TEXT NOT NULL,
    sig_digest TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS votes (
    vote_id TEXT PRIMARY KEY,
    contribution_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK(score IN (-1, 0, 1)),
    sig_node_id TEXT NOT NULL,
    sig_input_hash TEXT NOT NULL,
    sig_output_hash TEXT NOT NULL,
    sig_digest TEXT NOT NULL,
    UNIQUE(contribution_id, voter_id)
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_contributions_expert ON contributions(expert_id);
CREATE INDEX IF NOT EXISTS idx_contributions_status ON contributions(status);
CREATE INDEX IF NOT EXISTS idx_votes_contribution ON votes(contribution_id);
"""


class ContributionStore:
    """CRUD over contributions + votes + review status. SQLite-backed."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_TABLES)
        self._migrate_legacy_schema()
        self._conn.executescript(_INDEXES)

    def _migrate_legacy_schema(self) -> None:
        """Pre-Week-3 DBs lack the status column; add it and treat legacy rows as approved."""  # noqa: E501
        cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(contributions)").fetchall()
        }
        if "status" not in cols:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE contributions ADD COLUMN status TEXT NOT NULL "
                    "DEFAULT 'approved'"
                )

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

    # --- contributions ---

    def add(self, c: Contribution, status: str = STATUS_PENDING) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO contributions
                (contribution_id, expert_id, contributor_id, text, citations_json,
                 sig_node_id, sig_input_hash, sig_output_hash, sig_digest, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    status,
                ),
            )

    def get(self, contribution_id: str) -> Contribution | None:
        row = self._conn.execute(
            "SELECT * FROM contributions WHERE contribution_id = ?",
            (contribution_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_expert(
        self, expert_id: str, *, status: str | None = None
    ) -> list[Contribution]:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        sql = "SELECT * FROM contributions WHERE expert_id = ?"
        params: tuple = (expert_id,)
        if status is not None:
            sql += " AND status = ?"
            params = (expert_id, status)
        sql += " ORDER BY contribution_id"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def list_by_status(self, status: str) -> list[Contribution]:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        rows = self._conn.execute(
            "SELECT * FROM contributions WHERE status = ? ORDER BY contribution_id",
            (status,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def get_status(self, contribution_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM contributions WHERE contribution_id = ?",
            (contribution_id,),
        ).fetchone()
        return row[0] if row else None

    def set_status(self, contribution_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        with self._conn:
            self._conn.execute(
                "UPDATE contributions SET status = ? WHERE contribution_id = ?",
                (status, contribution_id),
            )

    # --- votes ---

    def add_vote(self, vote: Vote) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT INTO votes
                (vote_id, contribution_id, voter_id, score,
                 sig_node_id, sig_input_hash, sig_output_hash, sig_digest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contribution_id, voter_id) DO UPDATE SET
                    score = excluded.score,
                    sig_node_id = excluded.sig_node_id,
                    sig_input_hash = excluded.sig_input_hash,
                    sig_output_hash = excluded.sig_output_hash,
                    sig_digest = excluded.sig_digest""",
                (
                    vote.vote_id,
                    vote.contribution_id,
                    vote.voter_id,
                    vote.score,
                    vote.signature.node_id,
                    vote.signature.input_hash,
                    vote.signature.output_hash,
                    vote.signature.digest,
                ),
            )

    def get_vote(self, contribution_id: str, voter_id: str) -> Vote | None:
        row = self._conn.execute(
            """SELECT vote_id, contribution_id, voter_id, score,
                      sig_node_id, sig_input_hash, sig_output_hash, sig_digest
                 FROM votes WHERE contribution_id = ? AND voter_id = ?""",
            (contribution_id, voter_id),
        ).fetchone()
        return _row_to_vote(row) if row else None

    def votes_for(self, contribution_id: str) -> list[Vote]:
        rows = self._conn.execute(
            """SELECT vote_id, contribution_id, voter_id, score,
                      sig_node_id, sig_input_hash, sig_output_hash, sig_digest
                 FROM votes WHERE contribution_id = ? ORDER BY voter_id""",
            (contribution_id,),
        ).fetchall()
        return [_row_to_vote(r) for r in rows]

    def vote_tally(self, contribution_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(score), 0) FROM votes WHERE contribution_id = ?",
            (contribution_id,),
        ).fetchone()
        return int(row[0])

    # --- iteration ---

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


def _row_to_vote(row: tuple) -> Vote:
    return Vote(
        vote_id=row[0],
        contribution_id=row[1],
        voter_id=row[2],
        score=int(row[3]),
        signature=Signature(
            node_id=row[4],
            input_hash=row[5],
            output_hash=row[6],
            digest=row[7],
        ),
    )
