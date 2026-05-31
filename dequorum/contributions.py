"""Contributions: signed factual claims that augment expert answers."""

from __future__ import annotations

from dataclasses import dataclass

from dequorum.core.hashing import canonical_bytes, digest
from dequorum.core.node import Signature


@dataclass(frozen=True, slots=True)
class Contribution:
    """A signed factual claim attached to an expert by a contributor.

    Two contributions with the same (expert_id, contributor_id, text, citations)
    produce the same contribution_id — submission is idempotent.
    """

    contribution_id: str
    expert_id: str
    contributor_id: str
    text: str
    citations: tuple[str, ...]
    signature: Signature

    @classmethod
    def create(
        cls,
        *,
        expert_id: str,
        contributor_id: str,
        text: str,
        citations: tuple[str, ...],
        signing_key: bytes,
    ) -> Contribution:
        payload = {
            "expert_id": expert_id,
            "contributor_id": contributor_id,
            "text": text,
            "citations": list(citations),
        }
        contribution_id = digest(canonical_bytes(payload))
        sig = Signature.sign(
            node_id=contributor_id,
            signing_key=signing_key,
            payload=payload,
            result=contribution_id,
        )
        return cls(
            contribution_id=contribution_id,
            expert_id=expert_id,
            contributor_id=contributor_id,
            text=text,
            citations=citations,
            signature=sig,
        )
