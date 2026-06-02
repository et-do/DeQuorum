"""Intake: the gates a submission passes through before entering the review queue.

Today's gates (v0.2):
- Schema validation (length, citation requirement)
- Category requirement
- Duplicate detection (similarity search vs approved contributions)

Future gates (per contributor-intake.md §6c):
- Content filters (PII, harmful patterns)
- LLM-assisted plausibility soft signal
"""

from dequorum.intake.dedup import (
    DuplicateBand,
    DuplicateCandidate,
    DuplicateDetector,
    DuplicateReport,
)
from dequorum.intake.submission import (
    SubmissionError,
    SubmissionPipeline,
    SubmissionResult,
)

__all__ = [
    "DuplicateBand",
    "DuplicateCandidate",
    "DuplicateDetector",
    "DuplicateReport",
    "SubmissionError",
    "SubmissionPipeline",
    "SubmissionResult",
]
