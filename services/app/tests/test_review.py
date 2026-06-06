from __future__ import annotations

import pytest

from dequorum.core.errors import CompositionError
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ContributionStore,
)
from dequorum.review.service import ReviewService


def _c(expert_id: str = "py", contributor_id: str = "py") -> Contribution:
    return Contribution.create(
        contributor_id=contributor_id,
        text="some claim",
        citations=(),
        signing_key=b"k",
    )


def test_initial_status_is_pending() -> None:
    store = ContributionStore()
    c = _c()
    store.add(c)
    assert store.get_status(c.contribution_id) == STATUS_PENDING


def test_two_upvotes_approve() -> None:
    store = ContributionStore()
    c = _c(contributor_id="py")
    store.add(c)
    svc = ReviewService(store)
    svc.cast_vote(contribution_id=c.contribution_id, voter_id="rs", score=1)
    outcome = svc.cast_vote(contribution_id=c.contribution_id, voter_id="js", score=1)
    assert outcome.new_status == STATUS_APPROVED
    assert outcome.changed is True
    assert store.get_status(c.contribution_id) == STATUS_APPROVED


def test_two_downvotes_reject() -> None:
    store = ContributionStore()
    c = _c(contributor_id="py")
    store.add(c)
    svc = ReviewService(store)
    svc.cast_vote(contribution_id=c.contribution_id, voter_id="rs", score=-1)
    outcome = svc.cast_vote(contribution_id=c.contribution_id, voter_id="js", score=-1)
    assert outcome.new_status == STATUS_REJECTED


def test_single_vote_stays_pending() -> None:
    store = ContributionStore()
    c = _c(contributor_id="py")
    store.add(c)
    svc = ReviewService(store)
    outcome = svc.cast_vote(contribution_id=c.contribution_id, voter_id="rs", score=1)
    assert outcome.new_status == STATUS_PENDING
    assert outcome.changed is False


def test_self_voting_disallowed() -> None:
    store = ContributionStore()
    c = _c(contributor_id="py")
    store.add(c)
    svc = ReviewService(store)
    with pytest.raises(CompositionError, match="self-voting"):
        svc.cast_vote(contribution_id=c.contribution_id, voter_id="py", score=1)


def test_voter_can_change_their_vote() -> None:
    store = ContributionStore()
    c = _c(contributor_id="py")
    store.add(c)
    svc = ReviewService(store)
    svc.cast_vote(contribution_id=c.contribution_id, voter_id="rs", score=1)
    svc.cast_vote(contribution_id=c.contribution_id, voter_id="js", score=1)
    assert store.get_status(c.contribution_id) == STATUS_APPROVED
    # rs flips to -1: tally goes from +2 to 0
    svc.cast_vote(contribution_id=c.contribution_id, voter_id="rs", score=-1)
    assert store.vote_tally(c.contribution_id) == 0
    # but contribution stays approved because terminal states don't auto-revert
    assert store.get_status(c.contribution_id) == STATUS_APPROVED


def test_unknown_contribution_raises() -> None:
    store = ContributionStore()
    svc = ReviewService(store)
    with pytest.raises(CompositionError, match="unknown contribution"):
        svc.cast_vote(contribution_id="nope", voter_id="rs", score=1)


def test_retrieval_excludes_pending_contributions() -> None:
    from dequorum.retrieval import Retriever

    store = ContributionStore()
    approved = Contribution.create(
        contributor_id="py",
        primary_category_id="programming/python/typing",
        text="approved python typing fact",
        citations=(),
        signing_key=b"k",
    )
    pending = Contribution.create(
        contributor_id="py",
        primary_category_id="programming/python/typing",
        text="pending python typing fact",
        citations=(),
        signing_key=b"k2",
    )
    store.add(approved, status=STATUS_APPROVED)
    store.add(pending, status=STATUS_PENDING)

    results = Retriever(store).retrieve(
        "python typing", "programming/python/typing", top_k=5
    )
    texts = [r.contribution.text for r in results]
    assert "approved python typing fact" in texts
    assert "pending python typing fact" not in texts
