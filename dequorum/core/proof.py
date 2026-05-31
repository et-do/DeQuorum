"""ProofObject: the verifiable receipt returned by every composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dequorum.core.node import Signature


@dataclass(frozen=True, slots=True)
class ProofObject:
    output: Any
    chain: tuple[Signature, ...]

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(sig.node_id for sig in self.chain)
