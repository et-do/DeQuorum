"""Contribution attribution: measure how much each contribution actually
caused an answer, and turn that into a payout weight.

This is the research + economic core of DeQuorum. The naive ledger credits
every cited contribution equally; that is trivially gameable (citation
stuffing, near-duplicates) and carries no signal about which contribution
actually mattered. `measure_attribution` instead does leave-one-out
ablation — regenerate the answer without each contribution and measure the
drop in the answer's resemblance to that contribution's content — yielding
a faithful, gaming-resistant marginal value per contribution.
"""

from __future__ import annotations

from dequorum.attribution.marginal import (
    ContributionCredit,
    distribute_pool,
    measure_attribution,
)
from dequorum.attribution.shapley import shapley_attribution

__all__ = [
    "ContributionCredit",
    "distribute_pool",
    "measure_attribution",
    "shapley_attribution",
]
