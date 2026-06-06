"""Shared types returned by every router."""

from __future__ import annotations

from dataclasses import dataclass

from dequorum.taxonomy.category import Category


@dataclass(frozen=True, slots=True)
class SelectedCategory:
    """A category chosen by the router, with the score that selected it.

    Each `Category` here is guaranteed routable (carries a non-empty
    system_prompt); the router excludes organizational nodes.
    """

    category: Category
    score: float


@dataclass(frozen=True, slots=True)
class RoutingResult:
    selected: tuple[SelectedCategory, ...]
    method: str
    matched_tags: tuple[str, ...]
    fallback_used: bool
    threshold: float | None = None

    @property
    def categories(self) -> tuple[Category, ...]:
        return tuple(s.category for s in self.selected)
