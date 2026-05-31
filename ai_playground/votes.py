"""Signed votes. One slot per (contribution, voter); re-voting overwrites."""

from __future__ import annotations

from dataclasses import dataclass

from ai_playground.core.hashing import canonical_bytes, digest
from ai_playground.core.node import Signature

VALID_SCORES = (-1, 0, 1)


@dataclass(frozen=True, slots=True)
class Vote:
    """A signed vote. vote_id is determined by (contribution, voter)."""

    vote_id: str
    contribution_id: str
    voter_id: str
    score: int
    signature: Signature

    @classmethod
    def create(
        cls,
        *,
        contribution_id: str,
        voter_id: str,
        score: int,
        signing_key: bytes,
    ) -> Vote:
        if score not in VALID_SCORES:
            raise ValueError(f"score must be in {VALID_SCORES}, got {score}")
        slot = {"contribution_id": contribution_id, "voter_id": voter_id}
        vote_id = digest(canonical_bytes(slot))
        sig = Signature.sign(
            node_id=voter_id,
            signing_key=signing_key,
            payload={**slot, "score": score},
            result=vote_id,
        )
        return cls(
            vote_id=vote_id,
            contribution_id=contribution_id,
            voter_id=voter_id,
            score=score,
            signature=sig,
        )
