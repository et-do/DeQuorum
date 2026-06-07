from __future__ import annotations

from dequorum.distill import (
    attribution_delta,
    build_examples,
    exclude_contributor,
)
from dequorum.knowledge.contribution import Contribution
from dequorum.retrieval import ScoredContribution


def _sc(text: str, contributor: str) -> ScoredContribution:
    c = Contribution.create(
        contributor_id=contributor,
        text=text,
        citations=(),
        signing_key=b"k",
        primary_category_id="cat",
    )
    return ScoredContribution(contribution=c, score=1.0)


def test_build_examples_tags_contributor() -> None:
    ex = build_examples("what runs http/3?", [_sc("QUIC over UDP", "alice")])
    assert len(ex) == 1
    assert ex[0].prompt == "what runs http/3?"
    assert ex[0].completion == "QUIC over UDP"
    assert ex[0].contributor_id == "alice"


def test_exclude_contributor_removes_only_that_contributor() -> None:
    ex = build_examples("q", [_sc("a", "alice"), _sc("b", "bob")])
    out = exclude_contributor(ex, "alice")
    assert [e.contributor_id for e in out] == ["bob"]


def test_attribution_delta_full_partial_none() -> None:
    # Contributor fully responsible for the learned fact.
    full = attribution_delta(recall_with=1.0, recall_without=0.0, recall_base=0.0)
    assert full["learned_gain"] == 1.0
    assert full["attributable_fraction"] == 1.0

    # Fact was learned, but not from this contributor (recall same without them).
    other = attribution_delta(recall_with=1.0, recall_without=1.0, recall_base=0.0)
    assert other["attributable_fraction"] == 0.0

    # Nothing was learned at all → no attribution.
    none = attribution_delta(recall_with=0.0, recall_without=0.0, recall_base=0.0)
    assert none["attributable_fraction"] == 0.0
