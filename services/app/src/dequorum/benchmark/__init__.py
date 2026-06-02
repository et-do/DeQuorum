"""Benchmark harness: run questions through 3 conditions, write a Markdown report.

The three conditions per question:
  A) Vanilla baseline    - bare base model, generic system prompt, no retrieval.
  B) DeQuorum full        - route + retrieve + augment + sign (default pipeline).
  C) DeQuorum no-retrieval - router + expert prompt only, no contributions stuffed in.

C-vs-B isolates the actual lift of the retrieval / contribution layer.
B-vs-A measures the full DeQuorum advantage over a vanilla LLM.
"""

from dequorum.benchmark.questions import SEED_QUESTIONS, BenchmarkQuestion
from dequorum.benchmark.runner import BenchmarkResult, run_benchmark

__all__ = [
    "SEED_QUESTIONS",
    "BenchmarkQuestion",
    "BenchmarkResult",
    "run_benchmark",
]
