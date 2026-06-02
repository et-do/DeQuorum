from __future__ import annotations

from dequorum.identity.contributor import (
    TIER_DAILY_SUBMISSION_CAP,
    TIER_VOTE_WEIGHT,
    Contributor,
    Tier,
)


def _make_contributor(slug: str = "alice") -> Contributor:
    return Contributor.create(
        display_name=slug.title(),
        public_key=f"pub-{slug}".encode().ljust(32, b"\x00")[:32],
        signing_key=f"priv-{slug}".encode(),
        agreement_version="1.0.0",
        agreement_text="I agree.",
        tier=Tier.SOCIAL_PROOF,
    )


def test_create_assigns_deterministic_contributor_id() -> None:
    a = _make_contributor("alice")
    b = _make_contributor("alice")
    assert a.contributor_id == b.contributor_id
    assert a.contributor_id.startswith("dq:")


def test_different_pubkey_yields_different_id() -> None:
    a = _make_contributor("alice")
    b = _make_contributor("bob")
    assert a.contributor_id != b.contributor_id


def test_signature_is_over_agreement() -> None:
    c = _make_contributor()
    # signature.output_hash is hash of result (the agreement text)
    # changing the agreement text should change the signature digest
    other = Contributor.create(
        display_name="alice",
        public_key=b"pub-alice".ljust(32, b"\x00")[:32],
        signing_key=b"priv-alice",
        agreement_version="1.0.0",
        agreement_text="Different text.",
        tier=Tier.SOCIAL_PROOF,
    )
    assert c.agreement_signature.digest != other.agreement_signature.digest


def test_vote_weight_by_tier() -> None:
    for tier in Tier:
        c = Contributor.create(
            display_name="x",
            public_key=str(tier).encode().ljust(32, b"\x00")[:32],
            signing_key=b"k",
            agreement_version="1.0.0",
            agreement_text="t",
            tier=tier,
        )
        assert c.vote_weight == TIER_VOTE_WEIGHT[tier]
        assert c.daily_submission_cap == TIER_DAILY_SUBMISSION_CAP[tier]


def test_anonymous_and_email_tiers_have_zero_vote_weight() -> None:
    assert TIER_VOTE_WEIGHT[Tier.ANONYMOUS] == 0.0
    assert TIER_VOTE_WEIGHT[Tier.EMAIL_VERIFIED] == 0.0


def test_social_proof_is_the_first_tier_with_voting_power() -> None:
    assert TIER_VOTE_WEIGHT[Tier.SOCIAL_PROOF] >= 1.0


def test_curator_vote_weight_is_not_higher_than_credentialed() -> None:
    # Curators' privilege is veto, not weight.
    assert (
        TIER_VOTE_WEIGHT[Tier.CURATOR]
        <= TIER_VOTE_WEIGHT[Tier.CREDENTIALED_OR_REPUTATION]
    )
