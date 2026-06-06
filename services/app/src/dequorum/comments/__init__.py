"""Comments: signed discussion threads on contributions.

Comments are the foundation of the governance pipeline (see
`docs/architecture/contribution-governance.md`). Triage rationale,
review discussion, edit-request explanations, and post-acceptance
clarifications all flow through the same `Comment` model.

Design points:
- Append-only. "Editing" means posting a new comment with
  `replaces_comment_id` set (rendered as a strikethrough on the
  original). Hard deletes are forbidden — the proof chain stays
  intact.
- Soft redaction supported via `redacted_at` + `redacted_by`. The
  body is hidden in API responses but the row stays; thread
  structure survives.
- Signed by the author over the canonical payload, same way
  contributions and votes are. Makes attribution forgery infeasible
  even if the database is tampered with.
- Optional `line_anchor` lets a comment target a specific line range
  of the parent contribution's text. Phase-1 UI doesn't render the
  anchor; the field is reserved for the diff-view work in phase 3.
"""

from dequorum.comments.comment import Comment, LineAnchor
from dequorum.comments.store import CommentStore

__all__ = ["Comment", "CommentStore", "LineAnchor"]
