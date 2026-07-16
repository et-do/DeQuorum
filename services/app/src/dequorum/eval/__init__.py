"""Answer-quality evaluation: judges that score how good an answer is.

Used to (a) validate that the cheap embedding-resemblance attribution
measure tracks an independent measure of actual answer quality (closing the
"is the measure faithful?" loop), and (b) turn the qualitative grounding
comparison (whitepaper Claim 2) into numbers.
"""

from __future__ import annotations

from dequorum.eval.gold import SEEDED_GOLD, GoldQuestion, gold_for, gold_questions
from dequorum.eval.judge import (
    CoverageJudge,
    Judge,
    KeywordRecallJudge,
    LLMJudge,
)

__all__ = [
    "SEEDED_GOLD",
    "CoverageJudge",
    "GoldQuestion",
    "Judge",
    "KeywordRecallJudge",
    "LLMJudge",
    "gold_for",
    "gold_questions",
]
