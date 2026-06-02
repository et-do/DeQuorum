"""Attribution ledger: tokens earned per node from inference touches."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from dequorum.core.proof import ProofObject


@dataclass
class AttributionLedger:
    _totals: defaultdict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record(self, node_id: str, tokens: int = 1) -> None:
        self._totals[node_id] += tokens

    def credit(self, proof: ProofObject, tokens_per_step: int = 1) -> None:
        for sig in proof.chain:
            self.record(sig.node_id, tokens_per_step)

    def totals(self) -> dict[str, int]:
        return dict(self._totals)
