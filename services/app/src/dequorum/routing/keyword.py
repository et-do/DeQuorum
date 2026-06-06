"""KeywordRouter: deterministic token-overlap routing on specialty tags."""

from __future__ import annotations

import re
from collections.abc import Sequence

from dequorum.routing.result import RoutingResult, SelectedCategory
from dequorum.taxonomy.category import Category

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class KeywordRouter:
    """Score routable categories by token overlap between the query and
    their specialty tags.

    Deterministic, no ML. Scores are raw overlap counts (>= 0).
    Useful as a fallback and as a baseline to measure embedding routing
    against.
    """

    method = "keyword"

    def __init__(
        self,
        categories: Sequence[Category],
        *,
        fallback_to_all: bool = True,
        min_score: float = 1.0,
    ) -> None:
        # Only routable categories (those carrying a persona) are
        # eligible. The store's `routable()` helper already filters
        # this, but callers using `all()` get the same guarantee.
        self._categories: tuple[Category, ...] = tuple(
            c for c in categories if c.is_routable
        )
        self._fallback_to_all = fallback_to_all
        self._min_score = min_score

    def route(self, query: str, top_k: int = 3) -> RoutingResult:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        query_tokens = _tokenize(query)

        scored: list[tuple[float, set[str], Category]] = []
        for category in self._categories:
            tag_tokens = {t.lower() for t in category.specialty_tags}
            overlap = query_tokens & tag_tokens
            if len(overlap) >= self._min_score:
                scored.append((float(len(overlap)), overlap, category))

        if not scored:
            if self._fallback_to_all and self._categories:
                fallback = tuple(
                    SelectedCategory(category=c, score=0.0)
                    for c in self._categories[:top_k]
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

        scored.sort(key=lambda row: (-row[0], row[2].category_id))
        picked = scored[:top_k]
        matched = sorted({t for _, tags, _ in picked for t in tags})
        return RoutingResult(
            selected=tuple(SelectedCategory(category=c, score=s) for s, _, c in picked),
            method=self.method,
            matched_tags=tuple(matched),
            fallback_used=False,
            threshold=self._min_score,
        )
