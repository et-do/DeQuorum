"""Postgres-backed store for contributors + agreements.

Two construction modes:

  - `IdentityStore(conn)` — borrow a `psycopg.Connection` from the caller.
    Production code uses this via `dequorum.db.open_identity_store()`,
    which checks the connection out of the pool and manages transaction
    boundaries (commit on success, rollback on exception).

  - `IdentityStore()` — auto-borrow a connection from the global pool with
    autocommit=True. The store owns the connection and releases it back
    on `close()` / `__exit__`. Convenient for tests and quick scripts; do
    not use in production code paths because each statement commits
    independently.

Schema is owned by Alembic migrations under `dequorum.db.migrations`;
construction here does NOT create tables. Run `dequorum db upgrade` (or
let the FastAPI app startup hook run) first.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType

import psycopg

from dequorum.core.node import Signature
from dequorum.identity.agreement import (
    SEED_AGREEMENTS,
    AgreementVersion,
)
from dequorum.identity.contributor import Contributor, Tier


class IdentityStore:
    """CRUD over contributors + the agreement versions they signed."""

    def __init__(self, conn: psycopg.Connection | None = None) -> None:
        if conn is None:
            # No-arg mode opens a STANDALONE connection (not a pool checkout)
            # so tests can do `store = X()` without leaking pool slots when
            # they forget to call .close(). The connection closes on GC.
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

    def __enter__(self) -> IdentityStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def ensure_seed_agreements(self) -> None:
        """Insert the module-level SEED_AGREEMENTS if they don't already exist.

        Called once at app startup. Safe to re-run; conflicts are no-ops.
        """
        for a in SEED_AGREEMENTS:
            self._conn.execute(
                "INSERT INTO agreements (version, text, text_hash, effective_at) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (version) DO NOTHING",
                (a.version, a.text, a.text_hash, a.effective_at),
            )

    # --- agreements ---

    def get_agreement(self, version: str) -> AgreementVersion | None:
        row = self._conn.execute(
            "SELECT version, text, effective_at FROM agreements WHERE version = %s",
            (version,),
        ).fetchone()
        if row is None:
            return None
        return AgreementVersion(version=row[0], text=row[1], effective_at=row[2])

    # --- contributors ---

    def add(self, contributor: Contributor) -> None:
        sig = contributor.agreement_signature
        self._conn.execute(
            """INSERT INTO contributors (
                contributor_id, display_name, public_key, tier,
                agreement_version,
                agreement_sig_node, agreement_sig_input,
                agreement_sig_output, agreement_sig_digest,
                email_hash, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (contributor_id) DO UPDATE SET
                display_name         = EXCLUDED.display_name,
                public_key           = EXCLUDED.public_key,
                tier                 = EXCLUDED.tier,
                agreement_version    = EXCLUDED.agreement_version,
                agreement_sig_node   = EXCLUDED.agreement_sig_node,
                agreement_sig_input  = EXCLUDED.agreement_sig_input,
                agreement_sig_output = EXCLUDED.agreement_sig_output,
                agreement_sig_digest = EXCLUDED.agreement_sig_digest,
                email_hash           = EXCLUDED.email_hash,
                created_at           = EXCLUDED.created_at""",
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
            "SELECT contributor_id, display_name, public_key, tier, "
            "agreement_version, agreement_sig_node, agreement_sig_input, "
            "agreement_sig_output, agreement_sig_digest, email_hash, created_at "
            "FROM contributors WHERE contributor_id = %s",
            (contributor_id,),
        ).fetchone()
        return _row_to_contributor(row) if row else None

    def list_all(self) -> list[Contributor]:
        rows = self._conn.execute(
            "SELECT contributor_id, display_name, public_key, tier, "
            "agreement_version, agreement_sig_node, agreement_sig_input, "
            "agreement_sig_output, agreement_sig_digest, email_hash, created_at "
            "FROM contributors ORDER BY contributor_id"
        ).fetchall()
        return [_row_to_contributor(r) for r in rows]

    def set_tier(self, contributor_id: str, tier: Tier) -> None:
        self._conn.execute(
            "UPDATE contributors SET tier = %s WHERE contributor_id = %s",
            (int(tier), contributor_id),
        )

    def __iter__(self) -> Iterator[Contributor]:
        return iter(self.list_all())

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM contributors").fetchone()
        assert row is not None
        return int(row[0])


def _row_to_contributor(row: tuple) -> Contributor:
    return Contributor(
        contributor_id=row[0],
        display_name=row[1],
        public_key=bytes(row[2]),
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
