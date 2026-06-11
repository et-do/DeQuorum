"""Confidence intervals for benchmark reporting.

A bare mean over N items is a point estimate; without an interval it can't carry
statistical weight. These helpers turn the per-item scores the benches already
collect into 95% confidence intervals so every headline number reports its
uncertainty and its N.

We use the Wilson score interval throughout. For binary outcomes (hit@k, rank-1)
it is the standard proportion CI and behaves correctly at the 0/1 boundary
(an all-zero result yields a one-sided upper bound, not a zero-width interval).
For means of fractional [0,1] scores (gold-fact recall with partial credit) it is
a quasi-binomial approximation — slightly conservative, and far better than the
normal approximation near the boundaries where several of our results sit.
"""

from __future__ import annotations

import math

_Z95 = 1.96


def wilson_ci(successes: float, n: int, z: float = _Z95) -> tuple[float, float]:
    """95% Wilson score interval for `successes`/`n` (successes may be fractional
    for partial-credit scores). Returns (low, high) clamped to [0, 1]."""
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def mean_ci(values: list[float], z: float = _Z95) -> tuple[float, float, float]:
    """Return (mean, low, high) with a 95% Wilson interval over `values`."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0, 0.0)
    mean = sum(values) / n
    low, high = wilson_ci(sum(values), n, z)
    return (mean, low, high)


def ci_str(values: list[float]) -> str:
    """Format a mean with its 95% CI and N, e.g. '0.880 [0.76, 0.95] (n=50)'."""
    if not values:
        return "n/a"
    mean, low, high = mean_ci(values)
    return f"{mean:.3f} [{low:.2f}, {high:.2f}] (n={len(values)})"
