"""Answer-quality judges — two objectives, two grader families each.

The head-to-head in whitepaper §8.6 isolates the *objective* a marginal is scored
against, so judges come in two objectives, each with a deterministic and an LLM
grader (run both to show the objective gap is not a grader artifact):

  Correctness / reliance (truth-sensitive, reference-based):
  - KeywordRecallJudge: deterministic, model-independent (fraction of gold key facts
    present). Unbiased control; makes the experiment reproducible without a model.
  - LLMJudge: LLM-as-judge, strict 0-10 correctness+completeness vs a reference.

  Coverage / informativeness (truth-agnostic, reference-free — the Ye &
  Yoganarasimhan 2025 payout objective):
  - CoverageJudge: deterministic topical-term coverage of the query.
  - LLMCoverageJudge: LLM-as-judge, 0-10 topical completeness, correctness ignored.

LLM judges are more holistic but risk self-preference bias when the judge is the
generator (Zheng et al. 2023); the deterministic graders are the unbiased controls.
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
class CoverageJudge:
    """Reference-free *informativeness/coverage*: how completely the answer addresses
    the query's terms, ignorant of factual correctness.

    This stands in for the information-coverage value function used by the nearest
    Shapley-payout prior art (Ye & Yoganarasimhan, *Fair Document Valuation in LLM
    Summaries via Shapley Values*, 2025). The point is the objective, not the grader:
    a fluent, on-topic answer scores high whether or not it is true — so coverage
    cannot distinguish a true contribution from its near-identical false twin, which
    is exactly the contested regime where payout fairness bites (whitepaper §8.6).
    Contrast `KeywordRecallJudge` (recall of the *true* gold), which can.
    """

    def score(self, *, query: str, answer: str, reference: Sequence[str] = ()) -> float:
        # reference is accepted for Judge-protocol compatibility but ignored: coverage
        # is truth-agnostic by construction.
        q_terms = {t for t in _norm(query).split() if len(t) > 2}
        if not q_terms:
            return 0.0
        haystack = set(_norm(answer).split())
        return sum(1 for t in q_terms if t in haystack) / len(q_terms)


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


@dataclass(frozen=True, slots=True)
class LLMCoverageJudge:
    """LLM-as-judge for *informativeness/coverage*, reference-free and explicitly
    truth-agnostic: it grades how completely and relevantly the answer addresses the
    question, NOT whether it is correct. This is the LLM-graded counterpart of
    `CoverageJudge` and the LLM analogue of the Ye & Yoganarasimhan (2025) coverage
    value function — provided so the head-to-head can run both objectives under the
    *same* grader family (contrast `LLMJudge`, which grades correctness vs a
    reference). See whitepaper §8.6 methodology."""

    model: BaseModel

    def score(self, *, query: str, answer: str, reference: Sequence[str] = ()) -> float:
        system = (
            "You rate how COMPLETELY and relevantly an answer addresses a question — "
            "its coverage of the topic — on an integer scale from 0 to 10. Judge "
            "topical completeness ONLY; do NOT judge whether the answer is factually "
            "correct. A thorough, on-topic answer scores high even if it may be "
            "wrong. Reply with ONLY the integer."
        )
        user = f"Question: {query}\n\nAnswer:\n{answer}\n\nCoverage (0-10):"
        out = self.model.complete(system=system, user=user)
        match = re.search(r"\d+(?:\.\d+)?", out)
        if not match:
            return 0.0
        return max(0.0, min(1.0, float(match.group()) / 10.0))
