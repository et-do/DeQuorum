from __future__ import annotations

from dequorum.economics import CostModel, RevenueSplit


def test_split_sums_to_one() -> None:
    assert abs(RevenueSplit().total() - 1.0) < 1e-9


def test_default_model_is_viable_and_redistributes() -> None:
    m = CostModel()
    assert m.inference_cost() > 0
    assert m.viable()
    assert m.redistributed_per_query() > 0
    assert m.payout("contributor") == m.revenue_per_query * m.split.contributor


def test_low_volume_is_not_viable() -> None:
    # At low query volume the fixed infra dominates and the operator share
    # cannot cover it.
    m = CostModel(queries_per_month=50_000)
    assert not m.viable()
    assert m.breakeven_revenue_per_query() > m.revenue_per_query


def test_breakeven_price_makes_margins_nonnegative() -> None:
    base = CostModel(queries_per_month=50_000)
    at_be = CostModel(
        queries_per_month=50_000,
        revenue_per_query=base.breakeven_revenue_per_query(),
    )
    assert at_be.host_margin() >= -1e-9
    assert at_be.operator_margin() >= -1e-9
