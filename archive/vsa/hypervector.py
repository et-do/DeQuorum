"""Bipolar hyperdimensional vectors with self-inverse binding."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

type Hypervector = NDArray[np.int8]

DIMENSIONS: int = 10_000


def random_hypervector(seed: int, dimensions: int = DIMENSIONS) -> Hypervector:
    rng = np.random.default_rng(seed)
    return rng.choice(np.array([-1, 1], dtype=np.int8), size=dimensions)


def bind(a: Hypervector, b: Hypervector) -> Hypervector:
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    return (a * b).astype(np.int8)


def unbind(bound: Hypervector, key: Hypervector) -> Hypervector:
    return bind(bound, key)


def bundle(*vectors: Hypervector) -> Hypervector:
    if not vectors:
        raise ValueError("bundle requires at least one vector")
    stacked = np.stack(vectors).astype(np.int32)
    summed = stacked.sum(axis=0)
    return np.where(summed >= 0, 1, -1).astype(np.int8)


def cosine(a: Hypervector, b: Hypervector) -> float:
    af = a.astype(np.float64)
    bf = b.astype(np.float64)
    denom = float(np.linalg.norm(af) * np.linalg.norm(bf))
    if denom == 0.0:
        return 0.0
    return float(np.dot(af, bf) / denom)
