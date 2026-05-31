"""Pluggable strategies for combining N expert answers into a final response.

The Week-3 demo revealed that naively concatenating N expert answers presents
weak / contradictory answers as if equally valid. Strategies make the choice explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from dequorum.pipeline import ExpertAnswer


@dataclass(frozen=True, slots=True)
class CompositionResult:
    text: str
    strategy: str
    chosen: tuple[str, ...]  # expert_ids whose answers were USED in the final text


class CompositionStrategy(Protocol):
    name: str

    def compose(self, answers: tuple[ExpertAnswer, ...]) -> CompositionResult: ...


class ConcatStrategy:
    """Stitch every expert answer together with a section header per expert."""

    name = "concat"

    def compose(self, answers: tuple[ExpertAnswer, ...]) -> CompositionResult:
        if not answers:
            return CompositionResult(text="", strategy=self.name, chosen=())
        if len(answers) == 1:
            a = answers[0]
            return CompositionResult(
                text=a.answer, strategy=self.name, chosen=(a.expert.expert_id,)
            )
        sections = [
            f"### {a.expert.display_name} ({a.expert.expert_id})\n\n{a.answer}"
            for a in answers
        ]
        return CompositionResult(
            text="\n\n---\n\n".join(sections),
            strategy=self.name,
            chosen=tuple(a.expert.expert_id for a in answers),
        )


class PickBestStrategy:
    """Return only the highest-scoring expert's answer.

    Scoring (descending priority): expert routing score → sum of retrieved
    contribution scores → expert_id (tiebreak for determinism).
    """

    name = "pick_best"

    def compose(self, answers: tuple[ExpertAnswer, ...]) -> CompositionResult:
        if not answers:
            return CompositionResult(text="", strategy=self.name, chosen=())

        def rank_key(a: ExpertAnswer) -> tuple[float, float, str]:
            retrieval_score = sum(sc.score for sc in a.retrieved)
            return (-a.routing_score, -retrieval_score, a.expert.expert_id)

        best = sorted(answers, key=rank_key)[0]
        return CompositionResult(
            text=best.answer,
            strategy=self.name,
            chosen=(best.expert.expert_id,),
        )


STRATEGIES: dict[str, type[CompositionStrategy]] = {
    ConcatStrategy.name: ConcatStrategy,
    PickBestStrategy.name: PickBestStrategy,
}


def make_strategy(name: str) -> CompositionStrategy:
    if name not in STRATEGIES:
        raise ValueError(
            f"unknown composition strategy: {name!r} (available: {list(STRATEGIES)})"
        )
    return STRATEGIES[name]()
