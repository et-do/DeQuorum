"""Comment dataclass: signed, threaded, optionally line-anchored.

A comment is one node in a discussion tree attached to a single
contribution. `parent_comment_id` threads it under a parent comment;
when null, the comment is a top-level reply on the contribution.

Signing model mirrors `Contribution`:

    payload = canonical_json({
        contribution_id, parent_comment_id, author_id,
        body, line_anchor, created_at,
    })
    comment_id = digest(payload)
    signature  = Signature.sign(node_id=author_id, ...)

Replacing a comment (the user's "edit"): post a new comment with
`replaces_comment_id` set. The store updates the original row's
`replaced_by_comment_id` so the UI can render the predecessor with
strikethrough. The old body is preserved — replacement is additive,
not destructive.
"""

from __future__ import annotations

from dataclasses import dataclass

from dequorum.core.hashing import canonical_bytes, digest
from dequorum.core.node import Signature


@dataclass(frozen=True, slots=True)
class LineAnchor:
    """Anchors a comment to a [start_line, end_line] range of the
    parent contribution's text. Both inclusive, 1-indexed."""

    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError(
                f"invalid line anchor: start={self.start_line} end={self.end_line}"
            )

    def to_dict(self) -> dict[str, int]:
        return {"start_line": self.start_line, "end_line": self.end_line}


@dataclass(frozen=True, slots=True)
class Comment:
    comment_id: str
    contribution_id: str
    parent_comment_id: str | None
    author_id: str
    body: str
    line_anchor: LineAnchor | None
    created_at: int  # unix seconds
    redacted_at: int | None
    redacted_by: str | None
    replaces_comment_id: str | None
    signature: Signature

    @property
    def is_redacted(self) -> bool:
        return self.redacted_at is not None

    @property
    def display_body(self) -> str:
        """Body visible to readers. Redacted comments show a placeholder
        so the thread renders without the (potentially harmful) original
        content but the parent/reply structure is preserved."""
        if self.is_redacted:
            who = "moderator" if self.redacted_by != self.author_id else "author"
            return f"_[redacted by {who}]_"
        return self.body

    @classmethod
    def create(
        cls,
        *,
        contribution_id: str,
        author_id: str,
        body: str,
        signing_key: bytes,
        parent_comment_id: str | None = None,
        line_anchor: LineAnchor | None = None,
        replaces_comment_id: str | None = None,
        created_at: int,
    ) -> Comment:
        """Build and sign a Comment. `created_at` is part of the signed
        payload so two textually-identical comments by the same author
        at different times still get distinct ids."""
        if not body.strip():
            raise ValueError("comment body must not be empty")
        payload = {
            "contribution_id": contribution_id,
            "parent_comment_id": parent_comment_id,
            "author_id": author_id,
            "body": body,
            "line_anchor": line_anchor.to_dict() if line_anchor else None,
            "replaces_comment_id": replaces_comment_id,
            "created_at": created_at,
        }
        comment_id = "dq:c:" + digest(canonical_bytes(payload))[:24]
        sig = Signature.sign(
            node_id=author_id,
            signing_key=signing_key,
            payload=payload,
            result=comment_id,
        )
        return cls(
            comment_id=comment_id,
            contribution_id=contribution_id,
            parent_comment_id=parent_comment_id,
            author_id=author_id,
            body=body,
            line_anchor=line_anchor,
            created_at=created_at,
            redacted_at=None,
            redacted_by=None,
            replaces_comment_id=replaces_comment_id,
            signature=sig,
        )
