"""Protocol-surface services: the stable contract an integrator calls.

These are the first concrete protocol seams (build-direction.md item 7). Each is a
thin, documented facade over the protocol-core packages, deliberately decoupled
from `web`/HTTP and from internal store wiring:

  - `LedgerService`   — the payout / attribution audit boundary (services-roadmap's
    named `ledger` carve-out): settle an answer, settle it faithfully, and read the
    journal. The same surface a standalone `ledger` FastAPI service would lift.
  - `GroundingService` — vote-gated retrieval: turn a query into the approved
    grounding set, independent of the retrieval implementation (BM25 today).

In-process for now (nothing is deployed); the point is that lifting one of these
into its own service is wrapping the facade in transport, not a rewrite.
"""

from __future__ import annotations

from dequorum.services.grounding import GroundingService
from dequorum.services.ledger import LedgerService

__all__ = ["GroundingService", "LedgerService"]
