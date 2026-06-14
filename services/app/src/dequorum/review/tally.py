"""Tier-weighted vote aggregation.

The governance result in the whitepaper (§8.8) showed reputation-weighted voting
raises an attacker's sybil cost ~9x over a flat one-account-one-vote tally. The
per-tier vote weights are defined in `identity/contributor.py`; this module is the
pure aggregation that applies them, kept import-light and unit-tested so the
store/service can call it without pulling DB code into the test path.

Weighting policy:
  - A registered voter contributes `score * TIER_VOTE_WEIGHT[tier]`. Tiers 0-1
    (anonymous / email-only) weigh 0.0 — their votes are recorded but do not move
    the tally, the sybil-resistance lever.
  - A voter not found in the registry (no tier — e.g. a dev/stub voter) is counted
    at the SOCIAL_PROOF weight (1.0), i.e. a basic counted vote, so behaviour is
    unchanged for unregistered voters and only *upgrades* where a real tier exists.
"""

from __future__ import annotations

from collections.abc import Iterable

from dequorum.identity.contributor import TIER_VOTE_WEIGHT, Tier

_DEFAULT_WEIGHT: float = TIER_VOTE_WEIGHT[Tier.SOCIAL_PROOF]


def weight_for_tier(tier: int | None) -> float:
    """Vote weight for a voter's tier; unknown/unregistered → SOCIAL_PROOF (1.0)."""
    if tier is None:
        return _DEFAULT_WEIGHT
    try:
        return TIER_VOTE_WEIGHT[Tier(tier)]
    except (ValueError, KeyError):
        return _DEFAULT_WEIGHT


def tier_weighted_tally(votes: Iterable[tuple[int | None, int]]) -> float:
    """Tier-weighted sum over `(voter_tier, score)` pairs.

    `voter_tier` is the integer tier (or None if the voter isn't registered);
    `score` is the raw vote in {-1, 0, +1}.
    """
    return sum(weight_for_tier(tier) * score for tier, score in votes)
