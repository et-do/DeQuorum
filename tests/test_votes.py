from __future__ import annotations

import pytest

from ai_playground.votes import Vote


def _v(score: int = 1, voter: str = "rs") -> Vote:
    return Vote.create(
        contribution_id="abc123",
        voter_id=voter,
        score=score,
        signing_key=voter.encode(),
    )


def test_vote_id_is_deterministic_per_slot() -> None:
    a = _v(1)
    b = _v(-1)
    assert a.vote_id == b.vote_id


def test_signature_changes_with_score() -> None:
    a = _v(1)
    b = _v(-1)
    assert a.signature.digest != b.signature.digest


def test_signature_changes_with_voter() -> None:
    a = _v(1, "rs")
    b = _v(1, "py")
    assert a.vote_id != b.vote_id
    assert a.signature.digest != b.signature.digest


def test_invalid_score_raises() -> None:
    with pytest.raises(ValueError):
        Vote.create(contribution_id="x", voter_id="rs", score=2, signing_key=b"k")
