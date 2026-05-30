from __future__ import annotations

import numpy as np
import pytest
from ai_playground.vsa import bind, bundle, cosine, random_hypervector, unbind
from hypothesis import given
from hypothesis import strategies as st

DIMS = 1024
seeds = st.integers(min_value=0, max_value=2**31 - 1)


@given(seed=seeds)
def test_random_hypervector_is_deterministic(seed: int) -> None:
    a = random_hypervector(seed, DIMS)
    b = random_hypervector(seed, DIMS)
    assert np.array_equal(a, b)


@given(seed=seeds)
def test_random_hypervector_is_bipolar(seed: int) -> None:
    v = random_hypervector(seed, DIMS)
    assert set(np.unique(v).tolist()).issubset({-1, 1})


@given(s1=seeds, s2=seeds)
def test_bind_is_self_inverse(s1: int, s2: int) -> None:
    a = random_hypervector(s1, DIMS)
    b = random_hypervector(s2, DIMS)
    recovered = unbind(bind(a, b), a)
    assert np.array_equal(recovered, b)


@given(seed=seeds)
def test_self_similarity_is_one(seed: int) -> None:
    v = random_hypervector(seed, DIMS)
    assert cosine(v, v) == pytest.approx(1.0)


@given(s1=seeds, s2=seeds)
def test_random_vectors_are_near_orthogonal(s1: int, s2: int) -> None:
    a = random_hypervector(s1, DIMS)
    b = random_hypervector(s2, DIMS)
    if s1 == s2:
        return
    assert abs(cosine(a, b)) < 0.2


def test_bundle_rejects_empty() -> None:
    with pytest.raises(ValueError):
        bundle()


def test_bind_rejects_shape_mismatch() -> None:
    a = random_hypervector(1, 16)
    b = random_hypervector(2, 32)
    with pytest.raises(ValueError):
        bind(a, b)
