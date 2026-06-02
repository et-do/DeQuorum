"""Shared types returned by every router."""

from __future__ import annotations

from dataclasses import dataclass

from dequorum.experts.persona import Expert


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
