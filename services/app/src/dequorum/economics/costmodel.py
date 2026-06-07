"""A parameterized unit-economics model for a single answered query.

Every figure is an input with a stated default; nothing is hidden in a
constant. The model separates *real costs* (compute paid to a host, infra
paid to the operator) from the *redistribution* the kickback model exists
to deliver (contributor, reviewer, treasury shares). The network is viable
only when each role's revenue share covers its real cost; what remains is
what actually reaches the people who supplied the knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RevenueSplit:
    """Fractions of per-query revenue by role (must sum to 1.0)."""

    contributor: float = 0.40
    reviewer: float = 0.10
    host: float = 0.25
    operator: float = 0.15
    treasury: float = 0.10

    def total(self) -> float:
        return (
            self.contributor + self.reviewer + self.host + self.operator + self.treasury
        )


@dataclass(frozen=True, slots=True)
class CostModel:
    """Per-query economics. Token counts and prices are the levers; defaults
    reflect a ~7B open model served on a commodity GPU and a small per-query
    price. Override any field with measured values."""

    # Workload per query.
    tokens_in: int = 1500  # persona + retrieved contributions + question
    tokens_out: int = 300  # the answer

    # Inference price (USD per 1M tokens) — what it costs the host to serve.
    usd_per_1m_input: float = 0.05
    usd_per_1m_output: float = 0.20

    # Other real costs.
    embedding_usd_per_query: float = 0.00002  # routing/retrieval embed call
    fixed_infra_usd_per_month: float = 400.0  # storage, identity, payments, ops
    queries_per_month: int = 1_000_000

    # Pricing.
    revenue_per_query: float = 0.01

    split: RevenueSplit = RevenueSplit()

    # --- real costs -----------------------------------------------------

    def inference_cost(self) -> float:
        return (
            self.tokens_in / 1_000_000 * self.usd_per_1m_input
            + self.tokens_out / 1_000_000 * self.usd_per_1m_output
        )

    def infra_cost_per_query(self) -> float:
        if self.queries_per_month <= 0:
            return float("inf")
        return self.fixed_infra_usd_per_month / self.queries_per_month

    def compute_cost(self) -> float:
        """Real cost the host bears (inference + the embedding call)."""
        return self.inference_cost() + self.embedding_usd_per_query

    def total_cost_per_query(self) -> float:
        return self.compute_cost() + self.infra_cost_per_query()

    # --- revenue allocation --------------------------------------------

    def payout(self, role: str) -> float:
        return self.revenue_per_query * getattr(self.split, role)

    def host_margin(self) -> float:
        """Host's share minus the compute it must actually pay for."""
        return self.payout("host") - self.compute_cost()

    def operator_margin(self) -> float:
        return self.payout("operator") - self.infra_cost_per_query()

    def redistributed_per_query(self) -> float:
        """What flows to knowledge providers (contributor + reviewer + treasury)."""
        return (
            self.payout("contributor")
            + self.payout("reviewer")
            + self.payout("treasury")
        )

    def viable(self) -> bool:
        """True iff no role is subsidizing the network out of pocket."""
        return self.host_margin() >= 0 and self.operator_margin() >= 0

    def breakeven_revenue_per_query(self) -> float:
        """Lowest per-query price at which both host and operator shares cover
        their real costs (so the kickback to contributors is non-negative)."""
        need_for_host = self.compute_cost() / self.split.host
        need_for_operator = self.infra_cost_per_query() / self.split.operator
        return max(need_for_host, need_for_operator)

    def report_lines(self) -> list[str]:
        contributor_per_1k = self.payout("contributor") * 1000
        return [
            "Per-query unit economics",
            f"  tokens: {self.tokens_in} in / {self.tokens_out} out",
            f"  inference cost:     ${self.inference_cost():.5f}",
            f"  infra cost/query:   ${self.infra_cost_per_query():.5f}",
            f"  total real cost:    ${self.total_cost_per_query():.5f}",
            f"  revenue/query:      ${self.revenue_per_query:.5f}",
            f"  host margin:        ${self.host_margin():+.5f}",
            f"  operator margin:    ${self.operator_margin():+.5f}",
            f"  to contributors:    ${self.payout('contributor'):.5f} "
            f"(${contributor_per_1k:.2f} per 1k queries)",
            f"  redistributed/query:${self.redistributed_per_query():.5f}",
            f"  viable:             {self.viable()}",
            f"  break-even price:   ${self.breakeven_revenue_per_query():.5f}",
        ]
