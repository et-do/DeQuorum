"""Routing: pick which experts should answer a given query.

Two routers ship in v0.1:
- KeywordRouter: deterministic token-overlap on specialty tags. Cheap, no model.
- EmbeddingRouter: semantic similarity via an Embedder. Higher quality, needs a model.

Both return per-expert routing scores so composition can weight by confidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from dequorum.embedder import Embedder, cosine_sim
from dequorum.experts import Expert, ExpertRegistry

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class SelectedExpert:
    """An expert chosen by the router, with the score that selected it."""

    expert: Expert
    score: float


@dataclass(frozen=True, slots=True)
class RoutingResult:
    selected: tuple[SelectedExpert, ...]
    method: str
    matched_tags: tuple[str, ...]
    fallback_used: bool
    threshold: float | None = None

    @property
    def experts(self) -> tuple[Expert, ...]:
        return tuple(s.expert for s in self.selected)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class KeywordRouter:
    """Score experts by token overlap between the query and their specialty tags.

    Deterministic, no ML. Scores are raw overlap counts (>= 0).
    Useful as a fallback and as a baseline to measure embedding routing against.
    """

    method = "keyword"

    def __init__(
        self,
        registry: ExpertRegistry,
        *,
        fallback_to_all: bool = True,
        min_score: float = 1.0,
    ) -> None:
        self._registry = registry
        self._fallback_to_all = fallback_to_all
        self._min_score = min_score

    def route(self, query: str, top_k: int = 3) -> RoutingResult:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        query_tokens = _tokenize(query)

        scored: list[tuple[float, set[str], Expert]] = []
        for expert in self._registry.all():
            tag_tokens = {t.lower() for t in expert.specialty_tags}
            overlap = query_tokens & tag_tokens
            if len(overlap) >= self._min_score:
                scored.append((float(len(overlap)), overlap, expert))

        if not scored:
            if self._fallback_to_all and len(self._registry) > 0:
                fallback = tuple(
                    SelectedExpert(expert=e, score=0.0)
                    for e in self._registry.all()[:top_k]
                )
                return RoutingResult(
                    selected=fallback,
                    method=self.method,
                    matched_tags=(),
                    fallback_used=True,
                    threshold=self._min_score,
                )
            return RoutingResult(
                selected=(),
                method=self.method,
                matched_tags=(),
                fallback_used=False,
                threshold=self._min_score,
            )

        scored.sort(key=lambda row: (-row[0], row[2].expert_id))
        picked = scored[:top_k]
        matched = sorted({t for _, tags, _ in picked for t in tags})
        return RoutingResult(
            selected=tuple(SelectedExpert(expert=e, score=s) for s, _, e in picked),
            method=self.method,
            matched_tags=tuple(matched),
            fallback_used=False,
            threshold=self._min_score,
        )


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
