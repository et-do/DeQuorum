"""Postgres-backed store for signed contributions, votes, lineages, and review status.

See `dequorum.identity.store.IdentityStore` for the two construction modes
(caller-owned connection vs. auto-borrowed-from-pool). Schema is owned by
Alembic migrations under `dequorum.db.migrations`.

Foreign-key ordering: `contributions.lineage_id` references
`contribution_lineages(lineage_id)`, so every `add()` ensures the lineage
row exists before inserting the contribution.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from types import TracebackType

import psycopg

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


_CONTRIBUTION_COLS = (
    "contribution_id, lineage_id, version_number, parent_version, "
    "expert_id, contributor_id, primary_category_id, "
    "text, citations_json, "
    "sig_node_id, sig_input_hash, sig_output_hash, sig_digest, "
    "status"
)


class ContributionStore:
    """CRUD over contributions + lineages + votes + review status."""

    def __init__(self, conn: psycopg.Connection | None = None) -> None:
        if conn is None:
            from dequorum.db import get_pool

            self._conn = get_pool().getconn()
            self._conn.autocommit = True
            self._owns_conn = True
        else:
            self._conn = conn
            self._owns_conn = False

    def close(self) -> None:
        if self._owns_conn:
            from dequorum.db import get_pool

            self._conn.autocommit = False
            get_pool().putconn(self._conn)
            self._owns_conn = False

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

        # FK order: lineage row must exist before the contribution.
        self._conn.execute(
            "INSERT INTO contribution_lineages "
            "(lineage_id, current_contribution_id, created_at) "
            "VALUES (%s, NULL, 0) ON CONFLICT (lineage_id) DO NOTHING",
            (c.lineage_id,),
        )
        self._conn.execute(
            """INSERT INTO contributions
            (contribution_id, lineage_id, version_number, parent_version,
             expert_id, contributor_id, primary_category_id, text, citations_json,
             sig_node_id, sig_input_hash, sig_output_hash, sig_digest, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (contribution_id) DO UPDATE SET
                lineage_id          = EXCLUDED.lineage_id,
                version_number      = EXCLUDED.version_number,
                parent_version      = EXCLUDED.parent_version,
                expert_id           = EXCLUDED.expert_id,
                contributor_id      = EXCLUDED.contributor_id,
                primary_category_id = EXCLUDED.primary_category_id,
                text                = EXCLUDED.text,
                citations_json      = EXCLUDED.citations_json,
                sig_node_id         = EXCLUDED.sig_node_id,
                sig_input_hash      = EXCLUDED.sig_input_hash,
                sig_output_hash     = EXCLUDED.sig_output_hash,
                sig_digest          = EXCLUDED.sig_digest,
                status              = EXCLUDED.status""",
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
        if status == STATUS_APPROVED:
            self._set_lineage_current(c.lineage_id, c.contribution_id)

    def get(self, contribution_id: str) -> Contribution | None:
        row = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE contribution_id = %s",
            (contribution_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_expert(
        self, expert_id: str, *, status: str | None = None
    ) -> list[Contribution]:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        sql = f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE expert_id = %s"
        params: tuple = (expert_id,)
        if status is not None:
            sql += " AND status = %s"
            params = (expert_id, status)
        sql += " ORDER BY contribution_id"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def list_by_status(self, status: str) -> list[Contribution]:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions WHERE status = %s "
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
            "FROM contributions WHERE primary_category_id = %s"
        )
        params: tuple = (category_id,)
        if status is not None:
            sql += " AND status = %s"
            params = (category_id, status)
        sql += " ORDER BY contribution_id"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def list_by_contributor(self, contributor_id: str) -> list[Contribution]:
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} "
            "FROM contributions WHERE contributor_id = %s ORDER BY contribution_id",
            (contributor_id,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def get_status(self, contribution_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT status FROM contributions WHERE contribution_id = %s",
            (contribution_id,),
        ).fetchone()
        return row[0] if row else None

    def set_status(self, contribution_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        self._conn.execute(
            "UPDATE contributions SET status = %s WHERE contribution_id = %s",
            (status, contribution_id),
        )
        # Maintain lineage's current pointer when promoting/demoting.
        if status == STATUS_APPROVED:
            row = self._conn.execute(
                "SELECT lineage_id FROM contributions WHERE contribution_id = %s",
                (contribution_id,),
            ).fetchone()
            if row:
                self._set_lineage_current(row[0], contribution_id)
        elif status == STATUS_REJECTED:
            # If the rejected one was current, clear the pointer.
            row = self._conn.execute(
                "SELECT lineage_id FROM contributions WHERE contribution_id = %s",
                (contribution_id,),
            ).fetchone()
            if row:
                self._conn.execute(
                    "UPDATE contribution_lineages SET current_contribution_id = NULL "
                    "WHERE lineage_id = %s AND current_contribution_id = %s",
                    (row[0], contribution_id),
                )

    # --- lineages ---

    def _set_lineage_current(self, lineage_id: str, contribution_id: str) -> None:
        """Mark `contribution_id` current for its lineage and supersede the prior one.

        The lineage row is guaranteed to exist by the FK invariant — every
        contribution insert ensures the lineage row first.
        """
        prev = self._conn.execute(
            "SELECT current_contribution_id FROM contribution_lineages "
            "WHERE lineage_id = %s",
            (lineage_id,),
        ).fetchone()
        if prev and prev[0] and prev[0] != contribution_id:
            self._conn.execute(
                "UPDATE contributions SET status = %s WHERE contribution_id = %s",
                (STATUS_SUPERSEDED, prev[0]),
            )
        self._conn.execute(
            "UPDATE contribution_lineages SET current_contribution_id = %s "
            "WHERE lineage_id = %s",
            (contribution_id, lineage_id),
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
                 WHERE l.lineage_id = %s""",
            (lineage_id,),
        ).fetchone()
        return _row_to_contribution(row) if row else None

    def list_for_lineage(self, lineage_id: str) -> list[Contribution]:
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} "
            "FROM contributions WHERE lineage_id = %s ORDER BY version_number",
            (lineage_id,),
        ).fetchall()
        return [_row_to_contribution(r) for r in rows]

    def latest_version_for_lineage(self, lineage_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM contributions "
            "WHERE lineage_id = %s",
            (lineage_id,),
        ).fetchone()
        assert row is not None
        return int(row[0])

    # --- votes ---

    def add_vote(self, vote: Vote) -> None:
        self._conn.execute(
            """INSERT INTO votes
            (vote_id, contribution_id, voter_id, score,
             sig_node_id, sig_input_hash, sig_output_hash, sig_digest)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (contribution_id, voter_id) DO UPDATE SET
                score           = EXCLUDED.score,
                sig_node_id     = EXCLUDED.sig_node_id,
                sig_input_hash  = EXCLUDED.sig_input_hash,
                sig_output_hash = EXCLUDED.sig_output_hash,
                sig_digest      = EXCLUDED.sig_digest""",
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
                 FROM votes WHERE contribution_id = %s AND voter_id = %s""",
            (contribution_id, voter_id),
        ).fetchone()
        return _row_to_vote(row) if row else None

    def votes_for(self, contribution_id: str) -> list[Vote]:
        rows = self._conn.execute(
            """SELECT vote_id, contribution_id, voter_id, score,
                      sig_node_id, sig_input_hash, sig_output_hash, sig_digest
                 FROM votes WHERE contribution_id = %s ORDER BY voter_id""",
            (contribution_id,),
        ).fetchall()
        return [_row_to_vote(r) for r in rows]

    def vote_tally(self, contribution_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(score), 0) FROM votes WHERE contribution_id = %s",
            (contribution_id,),
        ).fetchone()
        assert row is not None
        return int(row[0])

    # --- iteration ---

    def __iter__(self) -> Iterator[Contribution]:
        rows = self._conn.execute(
            f"SELECT {_CONTRIBUTION_COLS} FROM contributions ORDER BY contribution_id"
        ).fetchall()
        return iter(_row_to_contribution(r) for r in rows)

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM contributions").fetchone()
        assert row is not None
        return int(row[0])


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
