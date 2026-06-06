"""Knowledge nodes: signed, attributable, deterministic data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from dequorum.core import crypto
from dequorum.core.hashing import canonical_bytes, digest


@dataclass(frozen=True, slots=True)
class Signature:
    node_id: str
    input_hash: str
    output_hash: str
    digest: str  # 64-byte Ed25519 signature, hex-encoded

    @staticmethod
    def _message(node_id: str, input_hash: str, output_hash: str) -> bytes:
        """The exact bytes that get signed / verified. A verifier holding
        only the public key reconstructs this from the stored fields."""
        return f"{node_id}|{input_hash}|{output_hash}".encode()

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
        signature = crypto.sign(
            signing_key, cls._message(node_id, input_hash, output_hash)
        )
        return cls(
            node_id=node_id,
            input_hash=input_hash,
            output_hash=output_hash,
            digest=signature.hex(),
        )

    def verify(self, public_key: bytes) -> bool:
        """True iff this signature was produced by the holder of the key
        behind `public_key` over its (node_id, input_hash, output_hash).
        This is the primitive the proof chain's public verifiability rests
        on — no secret and no trust in the storage layer is required."""
        try:
            signature = bytes.fromhex(self.digest)
        except ValueError:
            return False
        return crypto.verify(
            public_key,
            self._message(self.node_id, self.input_hash, self.output_hash),
            signature,
        )

    def covers(self, *, payload: Any, result: Any) -> bool:
        """True iff this signature's hashes match the given payload/result —
        i.e. the stored content hasn't been altered since signing. Pair with
        `verify()` to confirm both authorship and content integrity."""
        return self.input_hash == digest(canonical_bytes(payload)) and (
            self.output_hash == digest(canonical_bytes(result))
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
