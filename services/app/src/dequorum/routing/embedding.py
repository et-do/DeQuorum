"""EmbeddingRouter: semantic similarity routing via cosine over category profiles."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from dequorum.routing.embedder import Embedder, cosine_sim
from dequorum.routing.result import RoutingResult, SelectedCategory
from dequorum.taxonomy.category import Category


class _Router(Protocol):
    method: str

    def route(self, query: str, top_k: int = 3) -> RoutingResult: ...


class EmbeddingRouter:
    """Score routable categories by cosine similarity between the query
    and the category's profile embedding.

    The profile is `(display_name, specialty_tags, system_prompt,
    example_questions)` joined into a single string and embedded once
    at construction. Non-routable categories (empty system_prompt) are
    excluded from the index entirely.

    If `fallback` is provided and no category clears `min_score`, the
    fallback router is consulted instead of returning empty — catches
    the case where semantic similarity is low but a clear keyword
    match exists. Returned RoutingResult is marked `fallback_used=True`
    so the caller can tell.

    If no fallback is provided, returns empty selection on threshold
    miss and the caller (chat endpoint) falls through to a generalist
    base-model answer.
    """

    method = "embedding"

    def __init__(
        self,
        categories: Sequence[Category],
        embedder: Embedder,
        *,
        min_score: float = 0.30,
        fallback: _Router | None = None,
    ) -> None:
        self._categories: tuple[Category, ...] = tuple(
            c for c in categories if c.is_routable
        )
        self._embedder = embedder
        self._min_score = min_score
        self._fallback = fallback
        self._matrix: np.ndarray | None = None
        self._build_index()

    def _profile_text(self, c: Category) -> str:
        tags = " ".join(c.specialty_tags)
        examples = "\n".join(c.example_questions)
        return f"{c.display_name}\n{tags}\n{c.system_prompt}\n{examples}"

    def _build_index(self) -> None:
        if not self._categories:
            self._matrix = None
            return
        texts = [self._profile_text(c) for c in self._categories]
        self._matrix = self._embedder.embed(texts)

    def rebuild(self) -> None:
        self._build_index()

    def route(self, query: str, top_k: int = 3) -> RoutingResult:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        if self._matrix is None or not self._categories:
            return RoutingResult(
                selected=(),
                method=self.method,
                matched_tags=(),
                fallback_used=False,
                threshold=self._min_score,
            )

        q_vec = self._embedder.embed([query])[0]
        sims = cosine_sim(q_vec, self._matrix)

        scored: list[tuple[float, Category]] = [
            (float(s), c) for s, c in zip(sims, self._categories, strict=True)
        ]
        scored = [(s, c) for s, c in scored if s >= self._min_score]
        scored.sort(key=lambda row: (-row[0], row[1].category_id))
        picked = scored[:top_k]

        if not picked and self._fallback is not None:
            backup = self._fallback.route(query, top_k=top_k)
            return RoutingResult(
                selected=backup.selected,
                method=f"{self.method}+{backup.method}",
                matched_tags=backup.matched_tags,
                fallback_used=True,
                threshold=self._min_score,
            )

        return RoutingResult(
            selected=tuple(SelectedCategory(category=c, score=s) for s, c in picked),
            method=self.method,
            matched_tags=(),
            fallback_used=False,
            threshold=self._min_score,
        )
