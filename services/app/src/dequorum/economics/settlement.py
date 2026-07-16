"""Per-query settlement: turn a query's revenue into a concrete payout split.

This is the capstone of the economic loop. It consumes the two things the rest of
the system produces for an answer:

  1. the **grounding set** — the contributions that shaped the answer (the proof
     chain), each with a `credit_weight` from the attribution method, and
  2. the **quality signal** — user feedback on the answer (chat feedback summary),

and produces a `Settlement`: how much each contributor, reviewer, the host, the
operator, and the treasury earns for that query. It is deliberately *method-
agnostic* about how `credit_weight` was computed — reliance-grounded quality
marginal, routing-by-construction, or a fallback — so the attribution research
(whitepaper §8.6) plugs in without changing settlement.

Conservation: with a `RevenueSplit` that sums to 1.0, the settlement always pays
out exactly `revenue` — any contributor share that can't be assigned (no grounding,
or withheld for a poorly-rated answer) is redirected to the treasury, never lost or
double-paid.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from dequorum.attribution.marginal import ContributionCredit, distribute_pool
from dequorum.economics.costmodel import RevenueSplit


@dataclass(frozen=True, slots=True)
class Settlement:
    """The payout for a single query. Amounts are in the same unit as `revenue`."""

    revenue: float
    quality_factor: float
    contributors: dict[str, float] = field(default_factory=dict)
    reviewers: dict[str, float] = field(default_factory=dict)
    host: float = 0.0
    operator: float = 0.0
    treasury: float = 0.0

    def total(self) -> float:
        return (
            sum(self.contributors.values())
            + sum(self.reviewers.values())
            + self.host
            + self.operator
            + self.treasury
        )


def quality_factor_from_feedback(net: int, count: int) -> float:
    """Map a feedback summary to a [0, 1] payout factor on the contributor pool.

    - No feedback (count 0): 1.0 — absence of a complaint isn't a penalty.
    - Net non-negative: 1.0 — a helpful/neutral answer pays in full.
    - Net negative: scaled down by the mean rating; a unanimously-downvoted answer
      (mean -1) pays its contributors nothing. The withheld amount goes to treasury.
    """
    if count <= 0:
        return 1.0
    mean = net / count
    return 1.0 if mean >= 0 else max(0.0, 1.0 + mean)


def settle_query(
    *,
    revenue: float,
    credits: Sequence[ContributionCredit],
    reviewer_ids: Sequence[str] = (),
    split: RevenueSplit | None = None,
    quality_factor: float = 1.0,
) -> Settlement:
    """Split one query's `revenue` across all roles.

    `credits` carry per-contribution `credit_weight` (the attribution method's
    output); `reviewer_ids` are the reviewers who moved the grounding contributions
    to LIVE; `quality_factor` (typically from `quality_factor_from_feedback`) scales
    the contributor pool for answer quality. Host/operator/treasury take their fixed
    shares; anything unassignable rolls into treasury so the books balance.
    """
    split = split or RevenueSplit()
    quality_factor = max(0.0, min(1.0, quality_factor))

    # Contributor pool, gated by answer quality; the gated-off remainder -> treasury.
    base_contributor_pool = revenue * split.contributor
    paid_contributor_pool = base_contributor_pool * quality_factor
    contributors = distribute_pool(credits, paid_contributor_pool)
    # Unassignable contributor money (no grounding, or weights not summing to 1)
    # plus the quality-withheld remainder both fall through to treasury.
    contributor_to_treasury = base_contributor_pool - sum(contributors.values())

    # Reviewer pool split evenly; with no reviewers it rolls into treasury.
    reviewer_pool = revenue * split.reviewer
    if reviewer_ids:
        each = reviewer_pool / len(reviewer_ids)
        reviewers = {rid: each for rid in reviewer_ids}
        reviewer_to_treasury = 0.0
    else:
        reviewers = {}
        reviewer_to_treasury = reviewer_pool

    return Settlement(
        revenue=revenue,
        quality_factor=quality_factor,
        contributors=contributors,
        reviewers=reviewers,
        host=revenue * split.host,
        operator=revenue * split.operator,
        treasury=(
            revenue * split.treasury + contributor_to_treasury + reviewer_to_treasury
        ),
    )
