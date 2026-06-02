"""SQLite-backed store for signed contributions, votes, lineages, and review status."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from dequorum.core.node import Signature
from dequorum.knowledge.contribution import UNCATEGORIZED_ID, Contribution
from dequorum.knowledge.status import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
    VALID_STATUSES,
)
from dequorum.review.vote import Vote

__all__ = [
    "STATUS_APPROVED",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "STATUS_SUPERSEDED",
    "UNCATEGORIZED_ID",
    "VALID_STATUSES",
    "ContributionStore",
]

_TABLES = """
CREATE TABLE IF NOT EXISTS contributions (
    contribution_id TEXT PRIMARY KEY,
    lineage_id TEXT NOT NULL,
    version_number INTEGER NOT NULL DEFAULT 1,
    parent_version INTEGER,
    expert_id TEXT NOT NULL,
    contributor_id TEXT NOT NULL,
    primary_category_id TEXT NOT NULL DEFAULT 'uncategorized',
    text TEXT NOT NULL,
    citations_json TEXT NOT NULL,
    sig_node_id TEXT NOT NULL,
    sig_input_hash TEXT NOT NULL,
    sig_output_hash TEXT NOT NULL,
    sig_digest TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS contribution_lineages (
    lineage_id TEXT PRIMARY KEY,
    current_contribution_id TEXT,
    created_at INTEGER NOT NULL DEFAULT 0
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
CREATE INDEX IF NOT EXISTS idx_contributions_lineage ON contributions(lineage_id);
CREATE INDEX IF NOT EXISTS idx_contributions_category ON contributions(primary_category_id);
CREATE INDEX IF NOT EXISTS idx_contributions_contributor ON contributions(contributor_id);
CREATE INDEX IF NOT EXISTS idx_votes_contribution ON votes(contribution_id);
"""


_CONTRIBUTION_COLS = (
    "contribution_id, lineage_id, version_number, parent_version, "
    "expert_id, contributor_id, primary_category_id, "
    "text, citations_json, "
    "sig_node_id, sig_input_hash, sig_output_hash, sig_digest, "
    "status"
)


_LEGACY_FIELD_DEFAULTS: dict[str, tuple[str, str]] = {
    # column_name: (type clause, default value)
    "status": ("TEXT NOT NULL DEFAULT 'approved'", "approved"),
    "lineage_id": ("TEXT NOT NULL DEFAULT ''", ""),
    "version_number": ("INTEGER NOT NULL DEFAULT 1", "1"),
    "parent_version": ("INTEGER", ""),
    "primary_category_id": (
        "TEXT NOT NULL DEFAULT 'uncategorized'",
        "uncategorized",
    ),
}


class ContributionStore:
    """CRUD over contributions + lineages + votes + review status. SQLite-backed."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_TABLES)
        self._migrate_legacy_schema()
        self._conn.executescript(_INDEXES)
        self._backfill_lineages_for_legacy_rows()

    def _migrate_legacy_schema(self) -> None:
        """Pre-v0.2 DBs lack lineage / category / status columns. Add them as needed."""
        cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(contributions)").fetchall()
        }
        with self._conn:
            for name, (type_clause, _) in _LEGACY_FIELD_DEFAULTS.items():
                if name not in cols:
                    self._conn.execute(
                        f"ALTER TABLE contributions ADD COLUMN {name} {type_clause}"
                    )

    def _backfill_lineages_for_legacy_rows(self) -> None:
        """Give legacy rows (where lineage_id == '') a derived lineage based on contribution_id."""
        legacy = self._conn.execute(
            "SELECT contribution_id FROM contributions WHERE lineage_id = ''"
        ).fetchall()
        if not legacy:
            return
        with self._conn:
            for (cid,) in legacy:
                lineage_id = f"lin:legacy-{cid[:16]}"
                self._conn.execute(
                    "UPDATE contributions SET lineage_id = ?, version_number = 1 "
                    "WHERE contribution_id = ?",
                    (lineage_id, cid),
                )
                self._conn.execute(
                    "INSERT OR IGNORE INTO contribution_lineages "
                    "(lineage_id, current_contribution_id, created_at) VALUES (?, ?, 0)",
                    (lineage_id, cid),
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
                (contribution_id, lineage_id, version_number, parent_version,
                 expert_id, contributor_id, primary_category_id, text, citations_json,
                 sig_node_id, sig_input_hash, sig_output_hash, sig_digest, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    c.contribution_id,
                    c.lineage_id,
                    c.version_number,
                    c.parent_version,
                    c.expert_id,
                    c.contributor_id,
                    c.primary_category_id,
                    c.text,
                    json.dumps(list(c.citations)),
                    c.signature.node_id,
                    c.signature.input_hash,
                    c.signature.output_hash,
                    c.signature.digest,
                    status,
                ),
            )
            # Ensure a lineage row exists; only set current_contribution_id if approved.
            self._conn.execute(
                "INSERT OR IGNORE INTO contribution_lineages "
                "(lineage_id, current_contribution_id, created_at) "
                "VALUES (?, NULL, 0)",
                (c.lineage_id,),
            )
            if status == STATUS_APPROVED:
                self._set_lineage_current_locked(c.lineage_id, c.contribution_id)

    def get(self, contribution_id: str) -> Contribution | None:
        row = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE contribution_id = ?",
            (contribution_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_expert(
        self, expert_id: str, *, status: str | None = None
    ) -> list[Contribution]:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        sql = f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE expert_id = ?"
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
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE status = ? "
            "ORDER BY contribution_id",
            (status,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def list_by_category(
        self, category_id: str, *, status: str | None = None
    ) -> list[Contribution]:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        sql = (
            f"SELECT {_CONTRIBUTION_COLS} "
            "FROM contributions WHERE primary_category_id = ?"
        )
        params: tuple = (category_id,)
        if status is not None:
            sql += " AND status = ?"
            params = (category_id, status)
        sql += " ORDER BY contribution_id"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def list_by_contributor(self, contributor_id: str) -> list[Contribution]:
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} "
            "FROM contributions WHERE contributor_id = ? ORDER BY contribution_id",
            (contributor_id,),
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
            # Maintain lineage's current pointer when promoting/demoting.
            if status == STATUS_APPROVED:
                row = self._conn.execute(
                    "SELECT lineage_id FROM contributions WHERE contribution_id = ?",
                    (contribution_id,),
                ).fetchone()
                if row:
                    self._set_lineage_current_locked(row[0], contribution_id)
            elif status == STATUS_REJECTED:
                # If the rejected one was current, clear the pointer.
                row = self._conn.execute(
                    "SELECT lineage_id FROM contributions WHERE contribution_id = ?",
                    (contribution_id,),
                ).fetchone()
                if row:
                    self._conn.execute(
                        "UPDATE contribution_lineages SET current_contribution_id = NULL "
                        "WHERE lineage_id = ? AND current_contribution_id = ?",
                        (row[0], contribution_id),
                    )

    # --- lineages ---

    def _set_lineage_current_locked(
        self, lineage_id: str, contribution_id: str
    ) -> None:
        """Inside an existing transaction: mark `contribution_id` current; supersede others."""
        prev = self._conn.execute(
            "SELECT current_contribution_id FROM contribution_lineages "
            "WHERE lineage_id = ?",
            (lineage_id,),
        ).fetchone()
        if prev and prev[0] and prev[0] != contribution_id:
            self._conn.execute(
                "UPDATE contributions SET status = ? WHERE contribution_id = ?",
                (STATUS_SUPERSEDED, prev[0]),
            )
        self._conn.execute(
            "INSERT INTO contribution_lineages "
            "(lineage_id, current_contribution_id, created_at) "
            "VALUES (?, ?, 0) "
            "ON CONFLICT(lineage_id) DO UPDATE SET "
            "current_contribution_id = excluded.current_contribution_id",
            (lineage_id, contribution_id),
        )

    def current_for_lineage(self, lineage_id: str) -> Contribution | None:
        row = self._conn.execute(
            """SELECT c.contribution_id, c.lineage_id, c.version_number, c.parent_version,
                      c.expert_id, c.contributor_id, c.primary_category_id,
                      c.text, c.citations_json,
                      c.sig_node_id, c.sig_input_hash, c.sig_output_hash, c.sig_digest,
                      c.status
                 FROM contributions c
                 JOIN contribution_lineages l
                   ON l.current_contribution_id = c.contribution_id
                 WHERE l.lineage_id = ?""",
            (lineage_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_lineage(self, lineage_id: str) -> list[Contribution]:
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} "
            "FROM contributions WHERE lineage_id = ? ORDER BY version_number",
            (lineage_id,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def latest_version_for_lineage(self, lineage_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM contributions "
            "WHERE lineage_id = ?",
            (lineage_id,),
        ).fetchone()
        return int(row[0])

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
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions ORDER BY contribution_id"
        ).fetchall()
        return iter(_row_to_contribution(r) for r in rows)

    def __len__(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM contributions").fetchone()[0]
        )


def _row_to_contribution(row: tuple) -> Contribution:
    return Contribution(
        contribution_id=row[0],
        lineage_id=row[1],
        version_number=int(row[2]),
        parent_version=int(row[3]) if row[3] is not None else None,
        expert_id=row[4],
        contributor_id=row[5],
        primary_category_id=row[6],
        text=row[7],
        citations=tuple(json.loads(row[8])),
        signature=Signature(
            node_id=row[9],
            input_hash=row[10],
            output_hash=row[11],
            digest=row[12],
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
