"""EmbeddingRouter: semantic similarity routing via cosine over expert profiles."""

from __future__ import annotations

import numpy as np

from dequorum.experts.persona import Expert, ExpertRegistry
from dequorum.routing.embedder import Embedder, cosine_sim
from dequorum.routing.result import RoutingResult, SelectedExpert


class EmbeddingRouter:
    """Score experts by cosine similarity between query and expert profile embeddings.

    No fallback. If no expert clears `min_score`, returns empty selection — the
    pipeline will raise CompositionError, surfacing the gap rather than hallucinating
    an expert.
    """

    method = "embedding"

    def __init__(
        self,
        registry: ExpertRegistry,
        embedder: Embedder,
        *,
        min_score: float = 0.25,
    ) -> None:
        self._registry = registry
        self._embedder = embedder
        self._min_score = min_score
        self._expert_matrix: np.ndarray | None = None
        self._expert_index: tuple[Expert, ...] = ()
        self._build_index()

    def _profile_text(self, expert: Expert) -> str:
        tags = " ".join(expert.specialty_tags)
        return f"{expert.display_name}\n{tags}\n{expert.system_prompt}"

    def _build_index(self) -> None:
        experts = self._registry.all()
        if not experts:
            self._expert_matrix = None
            self._expert_index = ()
            return
        texts = [self._profile_text(e) for e in experts]
        self._expert_matrix = self._embedder.embed(texts)
        self._expert_index = experts

    def rebuild(self) -> None:
        self._build_index()

    def route(self, query: str, top_k: int = 3) -> RoutingResult:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        if self._expert_matrix is None or len(self._expert_index) == 0:
            return RoutingResult(
                selected=(),
                method=self.method,
                matched_tags=(),
                fallback_used=False,
                threshold=self._min_score,
            )

        q_vec = self._embedder.embed([query])[0]
        sims = cosine_sim(q_vec, self._expert_matrix)

        scored: list[tuple[float, Expert]] = [
            (float(s), e) for s, e in zip(sims, self._expert_index, strict=True)
        ]
        scored = [(s, e) for s, e in scored if s >= self._min_score]
        scored.sort(key=lambda row: (-row[0], row[1].expert_id))
        picked = scored[:top_k]

        return RoutingResult(
            selected=tuple(SelectedExpert(expert=e, score=s) for s, e in picked),
            method=self.method,
            matched_tags=(),
            fallback_used=False,
            threshold=self._min_score,
        )
