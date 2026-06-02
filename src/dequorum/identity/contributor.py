"""Contributors: the human/org behind a signing key.

A Contributor is distinct from an Expert. An Expert is a persona that *answers*
under a system prompt; a Contributor is a human (or org) who *submits* content,
optionally publishes under one or more expert personas, and receives kickbacks
when their contributions are cited at inference time.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from dequorum.core.hashing import canonical_bytes, digest
from dequorum.core.node import Signature


class Tier(IntEnum):
    """Sybil-resistance tier. Higher = more verified, more vote weight, higher caps."""

    ANONYMOUS = 0
    EMAIL_VERIFIED = 1
    SOCIAL_PROOF = 2
    CREDENTIALED_OR_REPUTATION = 3
    CURATOR = 4


# Vote weights per tier. Tunable.
TIER_VOTE_WEIGHT: dict[Tier, float] = {
    Tier.ANONYMOUS: 0.0,
    Tier.EMAIL_VERIFIED: 0.0,  # recorded but not counted toward tallies
    Tier.SOCIAL_PROOF: 1.0,
    Tier.CREDENTIALED_OR_REPUTATION: 2.5,
    Tier.CURATOR: 1.0,  # curator's power is veto, not weight
}


# Daily submission caps per tier. Bot-flood defense.
TIER_DAILY_SUBMISSION_CAP: dict[Tier, int] = {
    Tier.ANONYMOUS: 0,
    Tier.EMAIL_VERIFIED: 5,
    Tier.SOCIAL_PROOF: 50,
    Tier.CREDENTIALED_OR_REPUTATION: 500,
    Tier.CURATOR: 10_000,  # effectively unlimited
}


@dataclass(frozen=True, slots=True)
class Contributor:
    """The human/org behind a signing key. Distinct from Expert (which is a persona)."""

    contributor_id: str  # stable handle: "dq:<short-hash>" for now, DID later
    display_name: str
    public_key: bytes  # Ed25519 verification key
    tier: Tier
    agreement_version: str  # which version of the agreement was signed
    agreement_signature: Signature  # signature over the agreement text
    email_hash: str | None = None  # hash of verified email, or None if not verified
    created_at: int = 0  # unix seconds; 0 = unset (tests/seeds)

    @classmethod
    def create(
        cls,
        *,
        display_name: str,
        public_key: bytes,
        signing_key: bytes,
        agreement_version: str,
        agreement_text: str,
        tier: Tier = Tier.EMAIL_VERIFIED,
        email_hash: str | None = None,
        created_at: int = 0,
    ) -> Contributor:
        """Sign the agreement and return a Contributor record.

        `signing_key` is the contributor's private key — used here only to produce
        the agreement signature. We never store it on the Contributor object.
        """
        contributor_id = "dq:" + digest(canonical_bytes(public_key))[:16]
        sig = Signature.sign(
            node_id=contributor_id,
            signing_key=signing_key,
            payload={"agreement_version": agreement_version},
            result=agreement_text,
        )
        return cls(
            contributor_id=contributor_id,
            display_name=display_name,
            public_key=public_key,
            tier=tier,
            agreement_version=agreement_version,
            agreement_signature=sig,
            email_hash=email_hash,
            created_at=created_at,
        )

    @property
    def vote_weight(self) -> float:
        return TIER_VOTE_WEIGHT[self.tier]

    @property
    def daily_submission_cap(self) -> int:
        return TIER_DAILY_SUBMISSION_CAP[self.tier]
