from __future__ import annotations

from dequorum.identity.contributor import Tier
from dequorum.review.tally import tier_weighted_tally, weight_for_tier


def test_weight_per_tier_matches_ladder() -> None:
    # anonymous / email-only are recorded but weigh 0 (the sybil-resistance lever)
    assert weight_for_tier(Tier.ANONYMOUS) == 0.0
    assert weight_for_tier(Tier.EMAIL_VERIFIED) == 0.0
    assert weight_for_tier(Tier.SOCIAL_PROOF) == 1.0
    assert weight_for_tier(Tier.CREDENTIALED_OR_REPUTATION) == 2.5
    assert weight_for_tier(Tier.CURATOR) == 1.0


def test_unregistered_voter_defaults_to_basic_counted_vote() -> None:
    # None (no contributor row) -> SOCIAL_PROOF weight, so unregistered/dev voters
    # behave like the old flat tally.
    assert weight_for_tier(None) == 1.0
    assert weight_for_tier(999) == 1.0  # unknown tier int, defensive


def test_tier_weighted_tally_applies_weights() -> None:
    # one credentialed upvote (2.5) clears the +2 approval threshold alone
    assert tier_weighted_tally([(int(Tier.CREDENTIALED_OR_REPUTATION), 1)]) == 2.5
    # two social-proof upvotes also clear it (1.0 + 1.0)
    assert tier_weighted_tally([(2, 1), (2, 1)]) == 2.0
    # anonymous/email votes don't move the tally
    assert tier_weighted_tally([(0, 1), (1, 1), (1, -1)]) == 0.0
    # mix incl. an unregistered voter (counts as 1.0) and a downvote
    assert tier_weighted_tally([(None, 1), (2, 1), (3, -1)]) == 1.0 + 1.0 - 2.5


def test_empty_is_zero() -> None:
    assert tier_weighted_tally([]) == 0.0
