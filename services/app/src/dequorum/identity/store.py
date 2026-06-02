"""SQLite-backed store for contributors + agreements."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from dequorum.core.node import Signature
from dequorum.identity.agreement import (
    SEED_AGREEMENTS,
    AgreementVersion,
)
from dequorum.identity.contributor import Contributor, Tier

_TABLES = """
CREATE TABLE IF NOT EXISTS contributors (
    contributor_id        TEXT PRIMARY KEY,
    display_name          TEXT NOT NULL,
    public_key            BLOB NOT NULL,
    tier                  INTEGER NOT NULL,
    agreement_version     TEXT NOT NULL,
    agreement_sig_node    TEXT NOT NULL,
    agreement_sig_input   TEXT NOT NULL,
    agreement_sig_output  TEXT NOT NULL,
    agreement_sig_digest  TEXT NOT NULL,
    email_hash            TEXT,
    created_at            INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agreements (
    version       TEXT PRIMARY KEY,
    text          TEXT NOT NULL,
    text_hash     TEXT NOT NULL,
    effective_at  INTEGER NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_contributors_tier ON contributors(tier);
CREATE INDEX IF NOT EXISTS idx_contributors_email ON contributors(email_hash);
"""


class IdentityStore:
    """SQLite-backed store of contributors + the agreement versions they signed."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_TABLES)
        self._conn.executescript(_INDEXES)
        self._populate_seed_agreements()

    def _populate_seed_agreements(self) -> None:
        with self._conn:
            for a in SEED_AGREEMENTS:
                self._conn.execute(
                    "INSERT OR IGNORE INTO agreements "
                    "(version, text, text_hash, effective_at) VALUES (?, ?, ?, ?)",
                    (a.version, a.text, a.text_hash, a.effective_at),
                )

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> IdentityStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- agreements ---

    def get_agreement(self, version: str) -> AgreementVersion | None:
        row = self._conn.execute(
            "SELECT version, text, effective_at FROM agreements WHERE version = ?",
            (version,),
        ).fetchone()
        if row is None:
            return None
        return AgreementVersion(version=row[0], text=row[1], effective_at=row[2])

    # --- contributors ---

    def add(self, contributor: Contributor) -> None:
        sig = contributor.agreement_signature
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO contributors (
                    contributor_id, display_name, public_key, tier,
                    agreement_version,
                    agreement_sig_node, agreement_sig_input,
                    agreement_sig_output, agreement_sig_digest,
                    email_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    contributor.contributor_id,
                    contributor.display_name,
                    contributor.public_key,
                    int(contributor.tier),
                    contributor.agreement_version,
                    sig.node_id,
                    sig.input_hash,
                    sig.output_hash,
                    sig.digest,
                    contributor.email_hash,
                    contributor.created_at,
                ),
            )

    def get(self, contributor_id: str) -> Contributor | None:
        row = self._conn.execute(
            "SELECT * FROM contributors WHERE contributor_id = ?",
            (contributor_id,),
        ).fetchone()
        return _row_to_contributor(row) if row else None

    def list_all(self) -> list[Contributor]:
        rows = self._conn.execute(
            "SELECT * FROM contributors ORDER BY contributor_id"
        ).fetchall()
        return [_row_to_contributor(r) for r in rows]

    def set_tier(self, contributor_id: str, tier: Tier) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE contributors SET tier = ? WHERE contributor_id = ?",
                (int(tier), contributor_id),
            )

    def __iter__(self) -> Iterator[Contributor]:
        return iter(self.list_all())

    def __len__(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM contributors").fetchone()[0]
        )


def _row_to_contributor(row: tuple) -> Contributor:
    return Contributor(
        contributor_id=row[0],
        display_name=row[1],
        public_key=row[2],
        tier=Tier(int(row[3])),
        agreement_version=row[4],
        agreement_signature=Signature(
            node_id=row[5],
            input_hash=row[6],
            output_hash=row[7],
            digest=row[8],
        ),
        email_hash=row[9],
        created_at=int(row[10]),
    )
