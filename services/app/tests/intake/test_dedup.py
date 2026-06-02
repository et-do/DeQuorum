from __future__ import annotations

from dequorum.intake.dedup import DuplicateBand, DuplicateDetector
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.status import STATUS_APPROVED
from dequorum.knowledge.store import ContributionStore
from dequorum.routing.embedder import HashEmbedder


def _approved(text: str, category: str = "test") -> Contribution:
    return Contribution.create(
        expert_id="ex",
        contributor_id="dq:test",
        primary_category_id=category,
        text=text,
        citations=("https://example.com",),
        signing_key=b"k",
    )


def test_clear_when_no_existing_contributions() -> None:
    store = ContributionStore()
    detector = DuplicateDetector(store, HashEmbedder(dimension=128))
    report = detector.check("any text at all", category_id="empty-category")
    assert report.band == DuplicateBand.CLEAR
    assert report.top_candidates == ()


def test_likely_band_when_text_is_identical() -> None:
    store = ContributionStore()
    existing = _approved("The HTTP/3 protocol runs over QUIC instead of TCP.")
    store.add(existing, status=STATUS_APPROVED)
    detector = DuplicateDetector(store, HashEmbedder(dimension=512))
    report = detector.check(
        "The HTTP/3 protocol runs over QUIC instead of TCP.", category_id="test"
    )
    assert report.band == DuplicateBand.LIKELY
    assert report.top_candidates[0].contribution_id == existing.contribution_id


def test_clear_band_when_text_is_completely_different() -> None:
    store = ContributionStore()
    existing = _approved(
        "Python's typing.Generator describes generator return types via PEP 484."
    )
    store.add(existing, status=STATUS_APPROVED)
    detector = DuplicateDetector(store, HashEmbedder(dimension=512))
    report = detector.check(
        "Sourdough fermentation depends on wild yeast and lactobacillus bacteria.",
        category_id="test",
    )
    assert report.band == DuplicateBand.CLEAR


def test_only_checks_same_category() -> None:
    store = ContributionStore()
    existing = _approved("Identical claim in another category", category="other")
    store.add(existing, status=STATUS_APPROVED)
    detector = DuplicateDetector(store, HashEmbedder(dimension=128))
    report = detector.check("Identical claim in another category", category_id="test")
    # Same text but different category → CLEAR
    assert report.band == DuplicateBand.CLEAR


def test_only_considers_approved_status() -> None:
    store = ContributionStore()
    pending = _approved("Pending claim that is identical to query")
    store.add(pending)  # default pending status
    detector = DuplicateDetector(store, HashEmbedder(dimension=128))
    report = detector.check(
        "Pending claim that is identical to query", category_id="test"
    )
    assert report.band == DuplicateBand.CLEAR
    assert report.top_candidates == ()


def test_suggested_action_text_per_band() -> None:
    store = ContributionStore()
    detector = DuplicateDetector(store, HashEmbedder(dimension=128))
    clear = detector.check("anything", category_id="empty")
    assert "no similar" in clear.suggested_action.lower()
