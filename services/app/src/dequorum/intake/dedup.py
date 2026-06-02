"""Duplicate detection at submit time.

Embeds the candidate claim and compares against approved contributions in the
same category. Three similarity bands surface to the contributor with different
recommended actions (per contributor-intake.md §6a).

Bias: surface, don't reject. The contributor makes the final call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from dequorum.knowledge.status import STATUS_APPROVED
from dequorum.knowledge.store import ContributionStore
from dequorum.routing.embedder import Embedder, cosine_sim


class DuplicateBand(StrEnum):
    LIKELY = "likely"  # >= 0.90 - very likely duplicate; consider updating existing
    RELATED = "related"  # 0.70-0.90 - related, proceed if distinct
    CLEAR = "clear"  # < 0.70 - no similar existing claim


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    contribution_id: str
    lineage_id: str
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class DuplicateReport:
    band: DuplicateBand
    top_candidates: tuple[DuplicateCandidate, ...]

    @property
    def has_likely_duplicate(self) -> bool:
        return self.band == DuplicateBand.LIKELY

    @property
    def suggested_action(self) -> str:
        if self.band == DuplicateBand.LIKELY:
            cand = self.top_candidates[0] if self.top_candidates else None
            ref = f" (see {cand.contribution_id[:12]}…)" if cand else ""
            return (
                f"very likely duplicate{ref}. "
                "Consider updating the existing claim instead."
            )
        if self.band == DuplicateBand.RELATED:
            return "related claim(s) exist. Proceed if your claim is distinct."
        return "no similar existing claim found."


class DuplicateDetector:
    """Embedding-based similarity search over approved contributions in a category.

    The category scope is intentional: a claim about Python typing shouldn't be
    flagged as duplicate of a similar-sounding claim in cooking. Cross-category
    dedup is a future concern.
    """

    LIKELY_THRESHOLD: float = 0.90
    RELATED_THRESHOLD: float = 0.70

    def __init__(
        self,
        store: ContributionStore,
        embedder: Embedder,
        *,
        top_k: int = 3,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._top_k = top_k

    def check(self, text: str, *, category_id: str) -> DuplicateReport:
        approved = [
            c
            for c in self._store.list_by_category(category_id, status=STATUS_APPROVED)
            if c.text  # safety: skip empties
        ]
        if not approved:
            return DuplicateReport(band=DuplicateBand.CLEAR, top_candidates=())

        # Embed candidate + existing in one batch for efficiency
        all_texts = [text] + [c.text for c in approved]
        embeds = self._embedder.embed(all_texts)
        q_vec = embeds[0]
        existing_matrix = embeds[1:]
        sims = cosine_sim(q_vec, existing_matrix)

        order = np.argsort(-sims)[: self._top_k]
        top: list[DuplicateCandidate] = []
        for idx in order:
            c = approved[int(idx)]
            top.append(
                DuplicateCandidate(
                    contribution_id=c.contribution_id,
                    lineage_id=c.lineage_id,
                    text=c.text,
                    score=float(sims[int(idx)]),
                )
            )

        top_score = top[0].score if top else 0.0
        if top_score >= self.LIKELY_THRESHOLD:
            band = DuplicateBand.LIKELY
        elif top_score >= self.RELATED_THRESHOLD:
            band = DuplicateBand.RELATED
        else:
            band = DuplicateBand.CLEAR

        return DuplicateReport(band=band, top_candidates=tuple(top))
