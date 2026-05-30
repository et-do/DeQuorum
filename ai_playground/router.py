"""Routing: pick which experts should answer a given query."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_playground.experts import Expert, ExpertRegistry

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class RoutingResult:
    selected: tuple[Expert, ...]
    method: str
    matched_tags: tuple[str, ...]
    fallback_used: bool


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class KeywordRouter:
    """Score experts by token overlap between the query and their specialty tags."""

    def __init__(
        self, registry: ExpertRegistry, *, fallback_to_all: bool = True
    ) -> None:
        self._registry = registry
        self._fallback_to_all = fallback_to_all

    def route(self, query: str, top_k: int = 3) -> RoutingResult:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        query_tokens = _tokenize(query)

        scored: list[tuple[int, set[str], Expert]] = []
        for expert in self._registry.all():
            tag_tokens = {t.lower() for t in expert.specialty_tags}
            overlap = query_tokens & tag_tokens
            if overlap:
                scored.append((len(overlap), overlap, expert))

        if not scored:
            if self._fallback_to_all and len(self._registry) > 0:
                fallback = self._registry.all()[:top_k]
                return RoutingResult(
                    selected=fallback,
                    method="keyword",
                    matched_tags=(),
                    fallback_used=True,
                )
            return RoutingResult(
                selected=(),
                method="keyword",
                matched_tags=(),
                fallback_used=False,
            )

        scored.sort(key=lambda row: (-row[0], row[2].expert_id))
        picked = scored[:top_k]
        matched = sorted({t for _, tags, _ in picked for t in tags})
        return RoutingResult(
            selected=tuple(row[2] for row in picked),
            method="keyword",
            matched_tags=tuple(matched),
            fallback_used=False,
        )
