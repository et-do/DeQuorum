"""Tests for the lineage / versioning behavior on ContributionStore."""

from __future__ import annotations

from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.status import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SUPERSEDED,
)
from dequorum.knowledge.store import ContributionStore


def _c(text: str, lineage_id: str | None = None, version: int = 1) -> Contribution:
    return Contribution.create(
        expert_id="x",
        contributor_id="dq:test",
        primary_category_id="test",
        text=text,
        citations=("https://example.com",),
        signing_key=b"k",
        lineage_id=lineage_id,
        version_number=version,
        parent_version=version - 1 if version > 1 else None,
    )


def test_lineage_id_is_derived_from_content() -> None:
    a = _c("identical text")
    b = _c("identical text")
    # Same text + same category → same lineage_id
    assert a.lineage_id == b.lineage_id
    # And same contribution_id since content is identical
    assert a.contribution_id == b.contribution_id


def test_versions_under_same_lineage_have_different_contribution_ids() -> None:
    v1 = _c("first text")
    v2 = _c("second text", lineage_id=v1.lineage_id, version=2)
    assert v1.lineage_id == v2.lineage_id
    assert v1.contribution_id != v2.contribution_id
    assert v2.version_number == 2
    assert v2.parent_version == 1


def test_approving_v2_supersedes_v1() -> None:
    store = ContributionStore()
    v1 = _c("first version")
    store.add(v1, status=STATUS_APPROVED)
    v2 = _c("second version", lineage_id=v1.lineage_id, version=2)
    store.add(v2)  # pending
    store.set_status(v2.contribution_id, STATUS_APPROVED)

    assert store.get_status(v1.contribution_id) == STATUS_SUPERSEDED
    assert store.get_status(v2.contribution_id) == STATUS_APPROVED
    current = store.current_for_lineage(v1.lineage_id)
    assert current is not None
    assert current.contribution_id == v2.contribution_id


def test_rejecting_pending_v2_keeps_v1_current() -> None:
    store = ContributionStore()
    v1 = _c("first version")
    store.add(v1, status=STATUS_APPROVED)
    v2 = _c("second version", lineage_id=v1.lineage_id, version=2)
    store.add(v2)
    store.set_status(v2.contribution_id, STATUS_REJECTED)

    assert store.get_status(v1.contribution_id) == STATUS_APPROVED
    assert store.get_status(v2.contribution_id) == STATUS_REJECTED
    current = store.current_for_lineage(v1.lineage_id)
    assert current is not None
    assert current.contribution_id == v1.contribution_id


def test_latest_version_for_lineage() -> None:
    store = ContributionStore()
    v1 = _c("text", version=1)
    v2 = _c("text v2", lineage_id=v1.lineage_id, version=2)
    v3 = _c("text v3", lineage_id=v1.lineage_id, version=3)
    store.add(v1)
    store.add(v2)
    store.add(v3)
    assert store.latest_version_for_lineage(v1.lineage_id) == 3


def test_list_for_lineage_orders_by_version() -> None:
    store = ContributionStore()
    v1 = _c("text", version=1)
    v3 = _c("text v3", lineage_id=v1.lineage_id, version=3)
    v2 = _c("text v2", lineage_id=v1.lineage_id, version=2)
    store.add(v3)
    store.add(v1)
    store.add(v2)
    ordered = store.list_for_lineage(v1.lineage_id)
    versions = [c.version_number for c in ordered]
    assert versions == sorted(versions)


def test_pending_contribution_does_not_become_current_pointer() -> None:
    store = ContributionStore()
    v1 = _c("first")
    store.add(v1, status=STATUS_PENDING)
    # No current pointer until approved
    assert store.current_for_lineage(v1.lineage_id) is None
