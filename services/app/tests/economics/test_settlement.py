from __future__ import annotations

from dequorum.attribution.marginal import ContributionCredit
from dequorum.economics import RevenueSplit
from dequorum.economics.settlement import (
    Settlement,
    quality_factor_from_feedback,
    settle_query,
)


def _credit(contributor: str, weight: float) -> ContributionCredit:
    return ContributionCredit(
        contribution_id=f"c-{contributor}",
        contributor_id=contributor,
        retrieval_score=0.0,
        marginal_value=weight,
        credit_weight=weight,
    )


def _approx(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def test_settlement_conserves_revenue() -> None:
    credits = [_credit("alice", 0.7), _credit("bob", 0.3)]
    s = settle_query(revenue=0.01, credits=credits, reviewer_ids=["rev1"])
    assert _approx(s.total(), 0.01)  # default split sums to 1.0


def test_contributor_pool_splits_by_credit_weight() -> None:
    credits = [_credit("alice", 0.7), _credit("bob", 0.3)]
    s = settle_query(revenue=1.0, credits=credits)
    # contributor pool = 0.40 of revenue, split 70/30
    assert _approx(s.contributors["alice"], 0.40 * 0.7)
    assert _approx(s.contributors["bob"], 0.40 * 0.3)
    assert _approx(s.host, 0.25) and _approx(s.operator, 0.15)


def test_no_grounding_sends_contributor_pool_to_treasury() -> None:
    # A refusal / base-model answer cites nothing -> no contributor is paid, and the
    # contributor share rolls into treasury rather than being lost.
    s = settle_query(revenue=1.0, credits=[])
    assert s.contributors == {}
    assert _approx(s.total(), 1.0)
    # treasury = base treasury (0.10) + unassigned contributor (0.40) + reviewer (0.10)
    assert _approx(s.treasury, 0.10 + 0.40 + 0.10)


def test_quality_gating_withholds_and_redirects_to_treasury() -> None:
    credits = [_credit("alice", 1.0)]
    full = settle_query(revenue=1.0, credits=credits, quality_factor=1.0)
    bad = settle_query(revenue=1.0, credits=credits, quality_factor=0.0)
    assert _approx(full.contributors["alice"], 0.40)
    assert bad.contributors.get("alice", 0.0) == 0.0  # bad answer pays no contributor
    assert _approx(bad.total(), 1.0)  # withheld amount conserved into treasury
    assert bad.treasury > full.treasury


def test_reviewer_pool_splits_evenly_else_treasury() -> None:
    credits = [_credit("alice", 1.0)]
    two = settle_query(revenue=1.0, credits=credits, reviewer_ids=["r1", "r2"])
    assert _approx(two.reviewers["r1"], 0.05) and _approx(two.reviewers["r2"], 0.05)
    none = settle_query(revenue=1.0, credits=credits, reviewer_ids=[])
    assert none.reviewers == {}
    assert _approx(none.total(), 1.0)


def test_quality_factor_from_feedback_mapping() -> None:
    assert quality_factor_from_feedback(0, 0) == 1.0  # no signal -> pay
    assert quality_factor_from_feedback(3, 3) == 1.0  # all helpful
    assert quality_factor_from_feedback(0, 4) == 1.0  # net neutral -> pay
    assert quality_factor_from_feedback(-4, 4) == 0.0  # unanimously unhelpful -> none
    assert _approx(quality_factor_from_feedback(-2, 4), 0.5)  # mean -0.5 -> half


def test_custom_split_still_conserves() -> None:
    split = RevenueSplit(
        contributor=0.5, reviewer=0.1, host=0.2, operator=0.1, treasury=0.1
    )
    s = settle_query(revenue=2.0, credits=[_credit("a", 1.0)], split=split)
    assert isinstance(s, Settlement)
    assert _approx(s.total(), 2.0)
    assert _approx(s.contributors["a"], 2.0 * 0.5)
