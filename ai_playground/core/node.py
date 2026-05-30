"""Knowledge nodes: signed, attributable, deterministic data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ai_playground.core.hashing import canonical_bytes, digest


@dataclass(frozen=True, slots=True)
class Signature:
    node_id: str
    input_hash: str
    output_hash: str
    digest: str

    @classmethod
    def sign(
        cls,
        *,
        node_id: str,
        signing_key: bytes,
        payload: Any,
        result: Any,
    ) -> Signature:
        input_hash = digest(canonical_bytes(payload))
        output_hash = digest(canonical_bytes(result))
        sig_digest = digest(
            f"{node_id}|{input_hash}|{output_hash}".encode(),
            key=signing_key,
        )
        return cls(
            node_id=node_id,
            input_hash=input_hash,
            output_hash=output_hash,
            digest=sig_digest,
        )


@dataclass(frozen=True, slots=True)
class NodeResult:
    value: Any
    signature: Signature


class Node(ABC):
    """An institutional knowledge source that signs every answer it gives."""

    def __init__(self, *, node_id: str, signing_key: bytes) -> None:
        self.node_id = node_id
        self.signing_key = signing_key

    @abstractmethod
    def _answer(self, payload: Any) -> Any:
        """Return a deterministic answer or raise `MissingData`."""

    def query(self, payload: Any) -> NodeResult:
        value = self._answer(payload)
        sig = Signature.sign(
            node_id=self.node_id,
            signing_key=self.signing_key,
            payload=payload,
            result=value,
        )
        return NodeResult(value=value, signature=sig)
