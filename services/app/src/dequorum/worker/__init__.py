"""Worker: deferred/batched work off the request hot path.

Today: reliance-grounded settlement (the `(k+1)`-generation quality payout). The
queue abstraction lets the same job run inline in dev or via Cloud Tasks in prod
(services-roadmap). Future async work (embedding recompute, document extraction)
lands here too.
"""

from __future__ import annotations

from dequorum.worker.queue import (
    CloudTasksConfig,
    CloudTasksSettlementQueue,
    InlineSettlementQueue,
    SettlementQueue,
)
from dequorum.worker.settlement import SettlementJob, run_settlement_job

__all__ = [
    "CloudTasksConfig",
    "CloudTasksSettlementQueue",
    "InlineSettlementQueue",
    "SettlementJob",
    "SettlementQueue",
    "run_settlement_job",
]
