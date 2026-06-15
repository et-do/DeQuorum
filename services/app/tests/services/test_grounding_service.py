from __future__ import annotations

from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import STATUS_APPROVED, STATUS_PENDING, ContributionStore
from dequorum.retrieval import Retriever
from dequorum.services import GroundingService

_CAT = "programming/python/typing"


def _contribution(text: str, key: bytes) -> Contribution:
    return Contribution.create(
        contributor_id="py",
        primary_category_id=_CAT,
        text=text,
        citations=(),
        signing_key=key,
    )


def test_grounding_returns_only_approved_contributions() -> None:
    store = ContributionStore()
    approved = _contribution("approved python typing fact", b"k1")
    pending = _contribution("pending python typing fact", b"k2")
    store.add(approved, status=STATUS_APPROVED)
    store.add(pending, status=STATUS_PENDING)

    service = GroundingService(Retriever(store))
    grounded = service.ground("python typing", category_id=_CAT, top_k=5)
    texts = [sc.contribution.text for sc in grounded]
    assert "approved python typing fact" in texts
    assert "pending python typing fact" not in texts  # vote-gating invariant


def test_grounding_invalidates_after_a_status_change() -> None:
    store = ContributionStore()
    c = _contribution("approved python typing fact", b"k1")
    store.add(c, status=STATUS_PENDING)
    service = GroundingService(Retriever(store))

    assert service.ground("python typing", category_id=_CAT) == []  # nothing approved
    store.set_status(c.contribution_id, STATUS_APPROVED)
    service.invalidate(_CAT)  # without this the cached approved-only index is stale
    grounded = service.ground("python typing", category_id=_CAT)
    assert [sc.contribution.contribution_id for sc in grounded] == [c.contribution_id]


def test_empty_grounding_set_when_nothing_matches() -> None:
    service = GroundingService(Retriever(ContributionStore()))
    assert service.ground("anything", category_id=_CAT) == []
