"""Unit tests for the Comment dataclass + store invariants.

These tests don't go through the HTTP layer — they exercise the
signing model, ID derivation, redaction soft-delete, and the
bidirectional replacement chain directly against the store.
"""

from __future__ import annotations

import pytest

from dequorum.comments.comment import Comment, LineAnchor
from dequorum.comments.store import CommentStore
from dequorum.identity.seeds import commenter_for_uid
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import ContributionStore
from dequorum.taxonomy.seeds import populate as populate_seed_categories
from dequorum.taxonomy.store import CategoryStore


@pytest.fixture
def seeded_contribution_id() -> str:
    """Populate the seed dataset and return one contribution id we can
    attach comments to."""
    with CategoryStore() as cats:
        populate_seed_categories(cats)
    with ContributionStore() as store:
        populate_seed_contributions(store)
        contribs = list(store)
    return contribs[0].contribution_id


def _make_comment(
    contribution_id: str,
    *,
    body: str = "First!",
    parent: str | None = None,
    replaces: str | None = None,
    anchor: LineAnchor | None = None,
    uid: str = "alice-uid",
    now: int = 1_700_000_000,
) -> Comment:
    contributor_id, key = commenter_for_uid(uid)
    return Comment.create(
        contribution_id=contribution_id,
        author_id=contributor_id,
        body=body,
        signing_key=key,
        parent_comment_id=parent,
        replaces_comment_id=replaces,
        line_anchor=anchor,
        created_at=now,
    )


def test_create_sets_signed_id_and_signature(seeded_contribution_id: str) -> None:
    c = _make_comment(seeded_contribution_id)
    assert c.comment_id.startswith("dq:c:")
    assert c.signature.node_id == c.author_id
    assert c.signature.output_hash  # non-empty
    assert c.is_redacted is False


def test_two_textually_identical_comments_get_distinct_ids(
    seeded_contribution_id: str,
) -> None:
    """`created_at` is part of the signed payload so identical text by
    the same author at different times yields distinct comment ids."""
    a = _make_comment(seeded_contribution_id, body="ping", now=1)
    b = _make_comment(seeded_contribution_id, body="ping", now=2)
    assert a.comment_id != b.comment_id


def test_empty_body_rejected(seeded_contribution_id: str) -> None:
    with pytest.raises(ValueError):
        _make_comment(seeded_contribution_id, body="   \n\t ")


def test_line_anchor_validates_range() -> None:
    with pytest.raises(ValueError):
        LineAnchor(start_line=0, end_line=4)
    with pytest.raises(ValueError):
        LineAnchor(start_line=5, end_line=3)
    ok = LineAnchor(start_line=3, end_line=3)
    assert ok.to_dict() == {"start_line": 3, "end_line": 3}


def test_store_round_trip_preserves_all_fields(
    seeded_contribution_id: str,
) -> None:
    c = _make_comment(
        seeded_contribution_id,
        body="with anchor",
        anchor=LineAnchor(start_line=2, end_line=4),
    )
    with CommentStore() as store:
        store.add(c)
        roundtrip = store.get(c.comment_id)
    assert roundtrip is not None
    assert roundtrip == c


def test_threading_via_parent_comment_id(seeded_contribution_id: str) -> None:
    with CommentStore() as store:
        root = _make_comment(seeded_contribution_id, body="root", now=10)
        store.add(root)
        reply = _make_comment(
            seeded_contribution_id, body="reply", parent=root.comment_id, now=20
        )
        store.add(reply)
        all_for = store.list_for_contribution(seeded_contribution_id)

    assert len(all_for) == 2
    assert all_for[0].parent_comment_id is None
    assert all_for[1].parent_comment_id == root.comment_id


def test_redact_hides_body_but_keeps_row(seeded_contribution_id: str) -> None:
    with CommentStore() as store:
        c = _make_comment(seeded_contribution_id, body="secret")
        store.add(c)
        changed = store.redact(c.comment_id, redacted_by=c.author_id, redacted_at=999)
        assert changed is True
        again = store.redact(c.comment_id, redacted_by=c.author_id, redacted_at=1000)
        # second redact is a no-op (idempotency safeguard)
        assert again is False
        fetched = store.get(c.comment_id)

    assert fetched is not None
    assert fetched.is_redacted is True
    assert fetched.body == "secret"  # raw body preserved on the row
    assert fetched.display_body.startswith("_[redacted")  # public view masked


def test_replacement_updates_bidirectional_link(seeded_contribution_id: str) -> None:
    """Posting a replacement must set the original's
    `replaced_by_comment_id` in the same transaction."""
    with CommentStore() as store:
        original = _make_comment(seeded_contribution_id, body="v1", now=100)
        store.add(original)
        replacement = _make_comment(
            seeded_contribution_id,
            body="v2 — typo fix",
            replaces=original.comment_id,
            now=200,
        )
        store.add(replacement)

        # Hit the table directly to assert the forward-link is written.
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT replaced_by_comment_id FROM comments WHERE comment_id = %s",
            (original.comment_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == replacement.comment_id


def test_count_and_iter(seeded_contribution_id: str) -> None:
    with CommentStore() as store:
        for i in range(3):
            store.add(_make_comment(seeded_contribution_id, body=f"c{i}", now=i))
        assert store.count_for_contribution(seeded_contribution_id) == 3
        assert len(store) == 3
        assert sum(1 for _ in store) == 3
