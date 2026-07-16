"""Deferred settlement work: the unit a worker processes off the request path.

Reliance-grounded settlement is expensive — `(k+1)` model generations plus judge
calls per answer (whitepaper §8.6). Running it inline on a Cloud Run request pins an
instance and bill per-request for the whole settle (services-roadmap). So it's a
job: the API enqueues it, a worker (or the inline runner in dev) processes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dequorum.economics.settlement import Settlement
    from dequorum.inference.base_model import BaseModel
    from dequorum.routing.embedder import Embedder
    from dequorum.services import LedgerService


@dataclass(frozen=True, slots=True)
class SettlementJob:
    """Settle `message_id` for `revenue`. JSON-round-trippable so it can ride a
    Cloud Tasks HTTP body unchanged."""

    message_id: str
    revenue: float

    def to_dict(self) -> dict:
        return {"message_id": self.message_id, "revenue": self.revenue}

    @classmethod
    def from_dict(cls, data: dict) -> SettlementJob:
        return cls(message_id=str(data["message_id"]), revenue=float(data["revenue"]))


def run_settlement_job(
    job: SettlementJob,
    ledger: LedgerService,
    *,
    model: BaseModel,
    embedder: Embedder,
    judge_model: BaseModel | None = None,
) -> Settlement:
    """Process one job: the reliance-grounded, quality-grounded payout. The caller
    owns the `ledger` (and its stores') lifecycle; this just runs the expensive
    settle."""
    return ledger.settle_reliance(
        job.message_id,
        job.revenue,
        model=model,
        embedder=embedder,
        judge_model=judge_model,
    )
