"""Per-source attribution functionals for HDC bundles.

See research/experiments/01-hdc-attribution-functional.md for the spec.
Each function takes `components` (n, d) and a `query` (d,) and returns one
float per source describing how much that source contributed to sim(bundle, query).
"""

from __future__ import annotations

from itertools import combinations
from math import factorial

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int8]


def _validate(components: IntArray, query: IntArray) -> tuple[int, int]:
    if components.ndim != 2:
        raise ValueError("components must be 2-D: (n_sources, dimensions)")
    if query.ndim != 1:
        raise ValueError("query must be 1-D: (dimensions,)")
    n, d = components.shape
    if query.shape[0] != d:
        q_d = query.shape[0]
        raise ValueError(f"dim mismatch: components d={d}, query d={q_d}")
    return n, d


def banzhaf_attribution(components: IntArray, query: IntArray) -> FloatArray:
    """Per-dimension Banzhaf attribution. O(n*d).

    A source is 'pivotal' at dimension k when |S[k]| == 1 (the bundle's vote at k is
    a one-vote majority) and the source voted with that majority. Each pivotal
    contribution gets credited bundle[k] * query[k] / d.
    """
    _n, d = _validate(components, query)
    comps = components.astype(np.int32)
    q = query.astype(np.int32)

    sum_per_dim = comps.sum(axis=0)
    bundle = np.sign(sum_per_dim)
    tight = np.abs(sum_per_dim) == 1

    pivotal_mask = tight[np.newaxis, :] & (comps == bundle[np.newaxis, :])
    base_contribution = (bundle * q).astype(np.float64)
    weighted = pivotal_mask.astype(np.float64) * base_contribution[np.newaxis, :]
    return weighted.sum(axis=1) / d


def exact_shapley(components: IntArray, query: IntArray) -> FloatArray:
    """Brute-force Shapley value. O(2^n * n * d). For small n only.

    Treats the coalitional game v(T) = sim(bundle(T), q) where bundle(T) uses
    np.sign so ties at |S|=0 contribute 0 to similarity. v(empty) = 0.
    """
    n, d = _validate(components, query)
    if n > 16:
        raise ValueError(f"exact_shapley is intractable for n={n} (cap at 16)")

    comps = components.astype(np.int32)
    q = query.astype(np.int32)

    subset_value: dict[tuple[int, ...], float] = {(): 0.0}
    for size in range(1, n + 1):
        for combo in combinations(range(n), size):
            partial_sum = comps[list(combo)].sum(axis=0)
            bundle = np.sign(partial_sum)
            subset_value[combo] = float(np.dot(bundle, q)) / d

    phi = np.zeros(n, dtype=np.float64)
    for i in range(n):
        others = tuple(j for j in range(n) if j != i)
        for size in range(n):
            weight = factorial(size) * factorial(n - size - 1) / factorial(n)
            for combo in combinations(others, size):
                with_i = tuple(sorted((*combo, i)))
                phi[i] += weight * (subset_value[with_i] - subset_value[combo])
    return phi


def leave_one_out_attribution(components: IntArray, query: IntArray) -> FloatArray:
    """LOO baseline: drop in similarity when each source is removed. O(n*d).

    Ignores interactions between sources; widely critiqued but standard baseline.
    """
    n, d = _validate(components, query)
    comps = components.astype(np.int32)
    q = query.astype(np.int32)

    full_sum = comps.sum(axis=0)
    full_sim = float(np.dot(np.sign(full_sum), q)) / d

    phi = np.zeros(n, dtype=np.float64)
    for i in range(n):
        leave_out_sum = full_sum - comps[i]
        leave_out_sim = float(np.dot(np.sign(leave_out_sum), q)) / d
        phi[i] = full_sim - leave_out_sim
    return phi


def uniform_attribution(components: IntArray, query: IntArray) -> FloatArray:
    """Trivial baseline: split sim(B, q) equally across all sources. O(n*d)."""
    n, d = _validate(components, query)
    comps = components.astype(np.int32)
    q = query.astype(np.int32)
    full_sim = float(np.dot(np.sign(comps.sum(axis=0)), q)) / d
    return np.full(n, full_sim / n, dtype=np.float64)
