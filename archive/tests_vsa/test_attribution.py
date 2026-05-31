from __future__ import annotations

import numpy as np
import pytest
from dequorum.vsa import (
    banzhaf_attribution,
    exact_shapley,
    leave_one_out_attribution,
    random_hypervector,
    uniform_attribution,
)
from hypothesis import given
from hypothesis import strategies as st


def _components(n: int, d: int, base_seed: int) -> np.ndarray:
    return np.stack([random_hypervector(base_seed + i, d) for i in range(n)])


# --- hand-computed cases ---------------------------------------------------


def test_banzhaf_hand_n3_d5_asymmetric() -> None:
    components = np.array(
        [
            [1, 1, 1, 1, 1],
            [-1, -1, -1, -1, -1],
            [-1, -1, 1, 1, 1],
        ],
        dtype=np.int8,
    )
    query = np.ones(5, dtype=np.int8)
    phi = banzhaf_attribution(components, query)
    assert np.allclose(phi, [0.6, -0.4, 0.2])


def test_banzhaf_hand_n3_d10() -> None:
    components = np.array(
        [
            [1, 1, 1, 1, 1, -1, -1, -1, -1, -1],
            [1, 1, 1, -1, -1, 1, 1, -1, -1, 1],
            [1, -1, -1, 1, -1, 1, -1, 1, -1, 1],
        ],
        dtype=np.int8,
    )
    query = np.ones(10, dtype=np.int8)
    phi = banzhaf_attribution(components, query)
    assert np.allclose(phi, [0.1, 0.2, 0.1])


# --- structural identity ---------------------------------------------------


seeds = st.integers(min_value=0, max_value=2**31 - 1)
small_n = st.integers(min_value=3, max_value=7).filter(lambda n: n % 2 == 1)


@given(seed=seeds, n=small_n)
def test_banzhaf_equals_leave_one_out(seed: int, n: int) -> None:
    """Pivotal-decomposition formula equals the leave-one-out drop in similarity."""
    d = 256
    components = _components(n, d, seed)
    query = random_hypervector(seed + 9999, d)
    phi_banzhaf = banzhaf_attribution(components, query)
    phi_loo = leave_one_out_attribution(components, query)
    assert np.allclose(phi_banzhaf, phi_loo)


# --- semivalue axioms ------------------------------------------------------


@given(seed=seeds, n=small_n)
def test_symmetry_identical_voters_get_equal_attribution(seed: int, n: int) -> None:
    d = 256
    components = _components(n, d, seed)
    components[1] = components[0]
    query = random_hypervector(seed + 9999, d)
    phi = banzhaf_attribution(components, query)
    assert phi[0] == pytest.approx(phi[1])


@given(seed=seeds, n=small_n)
def test_anti_symmetry_in_query(seed: int, n: int) -> None:
    d = 256
    components = _components(n, d, seed)
    query = random_hypervector(seed + 9999, d)
    phi_pos = banzhaf_attribution(components, query)
    phi_neg = banzhaf_attribution(components, (-query).astype(np.int8))
    assert np.allclose(phi_pos, -phi_neg)


@given(seed=seeds, n=small_n)
def test_reproducibility(seed: int, n: int) -> None:
    d = 256
    components = _components(n, d, seed)
    query = random_hypervector(seed + 9999, d)
    a = banzhaf_attribution(components, query)
    b = banzhaf_attribution(components, query)
    assert np.array_equal(a, b)


# --- baseline sanity -------------------------------------------------------


def test_uniform_attribution_sums_to_full_similarity() -> None:
    components = np.array(
        [
            [1, 1, 1, 1, 1],
            [-1, -1, -1, -1, -1],
            [-1, -1, 1, 1, 1],
        ],
        dtype=np.int8,
    )
    query = np.ones(5, dtype=np.int8)
    phi = uniform_attribution(components, query)
    bundle = np.sign(components.astype(np.int32).sum(axis=0))
    full_sim = float(np.dot(bundle, query)) / 5
    assert phi.sum() == pytest.approx(full_sim)


def test_exact_shapley_runs_for_small_n() -> None:
    components = _components(n=5, d=64, base_seed=7)
    query = random_hypervector(99, 64)
    phi = exact_shapley(components, query)
    assert phi.shape == (5,)


def test_exact_shapley_refuses_large_n() -> None:
    components = _components(n=17, d=8, base_seed=0)
    query = random_hypervector(1, 8)
    with pytest.raises(ValueError):
        exact_shapley(components, query)


# --- empirical: how far is pivotal-decomposition from true Shapley? --------


def test_banzhaf_close_to_shapley_for_small_n() -> None:
    """Empirical L-inf gap between pivotal attribution and exact Shapley."""
    rng_seed = 12345
    n, d = 5, 512
    components = _components(n, d, rng_seed)
    query = random_hypervector(rng_seed + 7, d)
    phi_banzhaf = banzhaf_attribution(components, query)
    phi_shap = exact_shapley(components, query)
    gap = float(np.max(np.abs(phi_banzhaf - phi_shap)))
    # Document the observation; loose bound at scaffolding stage.
    assert gap < 0.3, f"unexpectedly large Shapley gap: {gap}"


# --- input validation ------------------------------------------------------


def test_banzhaf_rejects_dim_mismatch() -> None:
    components = np.ones((3, 5), dtype=np.int8)
    query = np.ones(4, dtype=np.int8)
    with pytest.raises(ValueError):
        banzhaf_attribution(components, query)


def test_banzhaf_rejects_1d_components() -> None:
    components = np.ones(5, dtype=np.int8)
    query = np.ones(5, dtype=np.int8)
    with pytest.raises(ValueError):
        banzhaf_attribution(components, query)
