from __future__ import annotations

import pytest

from dequorum.identity.contributor import Contributor, Tier
from dequorum.intake.dedup import DuplicateBand, DuplicateDetector
from dequorum.intake.submission import SubmissionError, SubmissionPipeline
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.status import STATUS_APPROVED, STATUS_PENDING
from dequorum.knowledge.store import ContributionStore
from dequorum.routing.embedder import HashEmbedder
from dequorum.taxonomy.category import Category
from dequorum.taxonomy.store import CategoryStore

SIGNING_KEY = b"contributor-priv-key"


def _make_contributor() -> Contributor:
    return Contributor.create(
        display_name="Test User",
        public_key=b"pub".ljust(32, b"\x00")[:32],
        signing_key=SIGNING_KEY,
        agreement_version="1.0.0",
        agreement_text="I agree.",
        tier=Tier.SOCIAL_PROOF,
    )


def _stores() -> tuple[ContributionStore, CategoryStore]:
    contrib = ContributionStore()
    cats = CategoryStore()
    cats.add(Category(category_id="test", parent_id=None, display_name="Test"))
    return contrib, cats


def _valid_text() -> str:
    return (
        "asyncio.create_task takes a coroutine, schedules it on the running event "
        "loop, and returns the resulting Task object for further inspection."
    )


def test_happy_path_creates_pending_contribution() -> None:
    contrib_store, cat_store = _stores()
    contributor = _make_contributor()
    pipeline = SubmissionPipeline(contrib_store, cat_store)

    result = pipeline.submit(
        contributor=contributor,
        contributor_signing_key=SIGNING_KEY,
        text=_valid_text(),
        citations=("https://docs.python.org/3/library/asyncio-task.html",),
        primary_category_id="test",
    )
    assert result.contribution.contributor_id == contributor.contributor_id
    assert result.contribution.version_number == 1
    assert result.contribution.parent_version is None
    assert (
        contrib_store.get_status(result.contribution.contribution_id) == STATUS_PENDING
    )


def test_unknown_category_rejected() -> None:
    contrib_store, cat_store = _stores()
    pipeline = SubmissionPipeline(contrib_store, cat_store)
    with pytest.raises(SubmissionError, match="unknown category"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text=_valid_text(),
            citations=("https://example.com",),
            primary_category_id="not-a-real-category",
        )


def test_missing_citation_rejected() -> None:
    contrib_store, cat_store = _stores()
    pipeline = SubmissionPipeline(contrib_store, cat_store)
    with pytest.raises(SubmissionError, match="citation"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text=_valid_text(),
            citations=(),
            primary_category_id="test",
        )


def test_http_citation_rejected() -> None:
    contrib_store, cat_store = _stores()
    pipeline = SubmissionPipeline(contrib_store, cat_store)
    with pytest.raises(SubmissionError, match="https"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text=_valid_text(),
            citations=("http://example.com",),
            primary_category_id="test",
        )


def test_text_too_short_rejected() -> None:
    contrib_store, cat_store = _stores()
    pipeline = SubmissionPipeline(contrib_store, cat_store)
    with pytest.raises(SubmissionError, match="too short"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text="too short",
            citations=("https://example.com",),
            primary_category_id="test",
        )


def test_duplicate_surfaced_but_does_not_block_by_default() -> None:
    contrib_store, cat_store = _stores()
    # Seed an approved contribution that matches text exactly
    existing = Contribution.create(
        contributor_id="dq:seed",
        primary_category_id="test",
        text=_valid_text(),
        citations=("https://example.com",),
        signing_key=b"seed-key",
    )
    contrib_store.add(existing, status=STATUS_APPROVED)

    pipeline = SubmissionPipeline(
        contrib_store,
        cat_store,
        duplicate_detector=DuplicateDetector(
            contrib_store, HashEmbedder(dimension=256)
        ),
    )
    result = pipeline.submit(
        contributor=_make_contributor(),
        contributor_signing_key=SIGNING_KEY,
        text=_valid_text(),
        citations=("https://example.com",),
        primary_category_id="test",
    )
    # Submission succeeded, but dedup band is LIKELY
    assert result.duplicate_report.band == DuplicateBand.LIKELY
    assert (
        contrib_store.get_status(result.contribution.contribution_id) == STATUS_PENDING
    )


def test_block_on_likely_duplicate_rejects() -> None:
    contrib_store, cat_store = _stores()
    existing = Contribution.create(
        contributor_id="dq:seed",
        primary_category_id="test",
        text=_valid_text(),
        citations=("https://example.com",),
        signing_key=b"seed-key",
    )
    contrib_store.add(existing, status=STATUS_APPROVED)

    pipeline = SubmissionPipeline(
        contrib_store,
        cat_store,
        duplicate_detector=DuplicateDetector(
            contrib_store, HashEmbedder(dimension=256)
        ),
        block_on_likely_duplicate=True,
    )
    with pytest.raises(SubmissionError, match="duplicate"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text=_valid_text(),
            citations=("https://example.com",),
            primary_category_id="test",
        )


def test_update_creates_v2_in_same_lineage() -> None:
    contrib_store, cat_store = _stores()
    contributor = _make_contributor()
    pipeline = SubmissionPipeline(contrib_store, cat_store)

    first = pipeline.submit(
        contributor=contributor,
        contributor_signing_key=SIGNING_KEY,
        text=_valid_text(),
        citations=("https://example.com",),
        primary_category_id="test",
    )
    # Promote v1 to approved so it has a current pointer (not strictly required for update)
    contrib_store.set_status(first.contribution.contribution_id, STATUS_APPROVED)

    updated_text = (
        _valid_text() + " Additionally, RuntimeError is raised when no loop is running."
    )
    v2 = pipeline.submit(
        contributor=contributor,
        contributor_signing_key=SIGNING_KEY,
        text=updated_text,
        citations=("https://example.com",),
        primary_category_id="test",
        update_lineage_id=first.contribution.lineage_id,
    )
    assert v2.contribution.version_number == 2
    assert v2.contribution.parent_version == 1
    assert v2.contribution.lineage_id == first.contribution.lineage_id
    assert contrib_store.get_status(v2.contribution.contribution_id) == STATUS_PENDING


def test_update_unknown_lineage_rejected() -> None:
    contrib_store, cat_store = _stores()
    pipeline = SubmissionPipeline(contrib_store, cat_store)
    with pytest.raises(SubmissionError, match="unknown lineage"):
        pipeline.submit(
            contributor=_make_contributor(),
            contributor_signing_key=SIGNING_KEY,
            text=_valid_text(),
            citations=("https://example.com",),
            primary_category_id="test",
            update_lineage_id="lin:not-real",
        )
