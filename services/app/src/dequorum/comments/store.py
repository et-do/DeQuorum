"""Postgres-backed CommentStore.

Same construction pattern as the other stores in this codebase
(`IdentityStore`, `ContributionStore`, `ChatStore`): pass a
caller-owned `psycopg.Connection`, or let the store open its own
standalone connection in no-arg mode for tests / quick scripts.

The store is intentionally policy-free. Authorization rules ("who can
redact a comment", "who can comment at all") live in the web layer
where they can be expressed in terms of the request's authenticated
user + tier. The store just enforces structural invariants (FK
integrity, append-only writes, parent thread consistency).
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType

import psycopg

from dequorum.comments.comment import Comment, LineAnchor
from dequorum.core.node import Signature

__all__ = ["CommentStore"]


_COMMENT_COLS = (
    "comment_id, contribution_id, parent_comment_id, author_id, body, "
    "line_anchor_start, line_anchor_end, "
    "created_at, redacted_at, redacted_by, "
    "replaces_comment_id, replaced_by_comment_id, "
    "sig_node_id, sig_input_hash, sig_output_hash, sig_digest"
)


class CommentStore:
    """CRUD over comments. Append-only — `redact` flips the soft-delete
    flag, `add` chains a replacement comment when `replaces_comment_id`
    is set."""

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

    def __enter__(self) -> CommentStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- writes ---

    def add(self, comment: Comment) -> Comment:
        """Insert a signed comment.

        If the comment carries `replaces_comment_id`, the original row's
        `replaced_by_comment_id` is updated in the same transaction so
        the bidirectional link is consistent.
        """
        line_start, line_end = (
            (comment.line_anchor.start_line, comment.line_anchor.end_line)
            if comment.line_anchor
            else (None, None)
        )
        with self._conn.transaction():
            self._conn.execute(
                "INSERT INTO comments ("
                + _COMMENT_COLS
                + ") VALUES ("
                + ", ".join(["%s"] * 16)
                + ")",
                (
                    comment.comment_id,
                    comment.contribution_id,
                    comment.parent_comment_id,
                    comment.author_id,
                    comment.body,
                    line_start,
                    line_end,
                    comment.created_at,
                    comment.redacted_at,
                    comment.redacted_by,
                    comment.replaces_comment_id,
                    None,  # replaced_by_comment_id (set on future replacement)
                    comment.signature.node_id,
                    comment.signature.input_hash,
                    comment.signature.output_hash,
                    comment.signature.digest,
                ),
            )
            if comment.replaces_comment_id is not None:
                self._conn.execute(
                    "UPDATE comments SET replaced_by_comment_id = %s "
                    "WHERE comment_id = %s",
                    (comment.comment_id, comment.replaces_comment_id),
                )
        return comment

    def redact(self, comment_id: str, *, redacted_by: str, redacted_at: int) -> bool:
        """Soft-delete: hide the body but preserve the row. Returns True
        iff a row was changed (False if the id didn't exist or was
        already redacted)."""
        result = self._conn.execute(
            "UPDATE comments "
            "SET redacted_at = %s, redacted_by = %s "
            "WHERE comment_id = %s AND redacted_at IS NULL",
            (redacted_at, redacted_by, comment_id),
        )
        return (result.rowcount or 0) > 0

    # --- reads ---

    def get(self, comment_id: str) -> Comment | None:
        row = self._conn.execute(
            "SELECT " + _COMMENT_COLS + " FROM comments WHERE comment_id = %s",
            (comment_id,),
        ).fetchone()
        return _row_to_comment(row) if row else None

    def list_for_contribution(self, contribution_id: str) -> list[Comment]:
        """All comments on a contribution, ordered by creation time so
        the web layer can build the thread tree without resorting in
        memory. Redacted rows are included — the caller decides whether
        to surface the body."""
        rows = self._conn.execute(
            "SELECT " + _COMMENT_COLS + " FROM comments "
            "WHERE contribution_id = %s "
            "ORDER BY created_at, comment_id",
            (contribution_id,),
        ).fetchall()
        return [_row_to_comment(r) for r in rows]

    def count_for_contribution(self, contribution_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM comments WHERE contribution_id = %s",
            (contribution_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def __iter__(self) -> Iterator[Comment]:
        rows = self._conn.execute(
            "SELECT " + _COMMENT_COLS + " FROM comments ORDER BY created_at"
        ).fetchall()
        return iter(_row_to_comment(r) for r in rows)

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM comments").fetchone()
        return int(row[0]) if row else 0


def _row_to_comment(row: tuple) -> Comment:
    (
        comment_id,
        contribution_id,
        parent_comment_id,
        author_id,
        body,
        line_anchor_start,
        line_anchor_end,
        created_at,
        redacted_at,
        redacted_by,
        replaces_comment_id,
        _replaced_by_comment_id,
        sig_node_id,
        sig_input_hash,
        sig_output_hash,
        sig_digest,
    ) = row
    anchor = (
        LineAnchor(start_line=int(line_anchor_start), end_line=int(line_anchor_end))
        if line_anchor_start is not None and line_anchor_end is not None
        else None
    )
    return Comment(
        comment_id=comment_id,
        contribution_id=contribution_id,
        parent_comment_id=parent_comment_id,
        author_id=author_id,
        body=body,
        line_anchor=anchor,
        created_at=int(created_at),
        redacted_at=int(redacted_at) if redacted_at is not None else None,
        redacted_by=redacted_by,
        replaces_comment_id=replaces_comment_id,
        signature=Signature(
            node_id=sig_node_id,
            input_hash=sig_input_hash,
            output_hash=sig_output_hash,
            digest=sig_digest,
        ),
    )
