"""Answer-quality judges.

Two implementations:
  - KeywordRecallJudge: deterministic, reference-based (fraction of gold key
    facts the answer contains). Independent of the embedding-resemblance
    attribution measure, so it is a valid *external* check on quality, and
    it makes the faithfulness experiment reproducible without a model.
  - LLMJudge: LLM-as-judge with a strict 0-10 rubric. More holistic, but
    biased and costly; used to corroborate the deterministic judge.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from dequorum.inference.base_model import BaseModel

_WORD = re.compile(r"[^a-z0-9]+")


def _norm(text: str) -> str:
    return _WORD.sub(" ", text.lower()).strip()


class Judge(Protocol):
    def score(self, *, query: str, answer: str, reference: Sequence[str]) -> float:
        """Return answer quality in [0, 1]."""
        ...


@dataclass(frozen=True, slots=True)
class KeywordRecallJudge:
    """Fraction of the gold key phrases that appear in the answer."""

    def score(self, *, query: str, answer: str, reference: Sequence[str]) -> float:
        if not reference:
            return 0.0
        haystack = _norm(answer)
        hits = sum(1 for phrase in reference if _norm(phrase) in haystack)
        return hits / len(reference)


@dataclass(frozen=True, slots=True)
class LLMJudge:
    """LLM-as-judge: grade correctness + completeness on a 0-10 scale."""

    model: BaseModel

    def score(self, *, query: str, answer: str, reference: Sequence[str]) -> float:
        ref = "\n".join(f"- {r}" for r in reference) if reference else "(none provided)"
        system = (
            "You are a strict grader. Score the answer's correctness and "
            "completeness for the question on an integer scale from 0 to 10, "
            "where 10 is fully correct and complete. Reply with ONLY the integer."
        )
        user = (
            f"Question: {query}\n\n"
            f"Reference key facts:\n{ref}\n\n"
            f"Answer:\n{answer}\n\n"
            "Score (0-10):"
        )
        out = self.model.complete(system=system, user=user)
        match = re.search(r"\d+(?:\.\d+)?", out)
        if not match:
            return 0.0
        return max(0.0, min(1.0, float(match.group()) / 10.0))
