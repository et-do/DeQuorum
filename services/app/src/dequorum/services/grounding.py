"""GroundingService: vote-gated retrieval as a protocol surface.

Turns a query into the **approved** grounding set for a routed category. The
governance invariant is load-bearing and lives below this seam: retrieval only ever
returns peer-approved contributions (vote-gated via status), so a false or
superseded claim cannot ground an answer (whitepaper C7). Integrators ground
against this contract without depending on the retrieval implementation (BM25
today; pgvector/dense later per services-roadmap) — the return type is the grounding
set, and the proof chain is `[sc.contribution.signature for sc in result]`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dequorum.retrieval import Retriever, ScoredContribution

DEFAULT_TOP_K = 3


class GroundingService:
    """Vote-gated grounding for one routed category.

    Wraps a `Retriever` (which owns the approved-only corpus + its cache). When a
    contribution's status changes (approved/superseded), call `invalidate` so the
    grounding set reflects the current governance state.
    """

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def ground(
        self,
        query: str,
        *,
        category_id: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[ScoredContribution]:
        """The approved grounding set for `query` within `category_id`, best-first.
        Empty when nothing approved matches — the caller answers ungrounded."""
        return self._retriever.retrieve(query, category_id, top_k=top_k)

    def invalidate(self, category_id: str | None = None) -> None:
        """Drop cached indexes after a governance status change (all categories
        when `category_id` is None)."""
        self._retriever.invalidate(category_id)
