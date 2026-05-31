from __future__ import annotations

import numpy as np
import pytest

from dequorum.embedder import HashEmbedder, cosine_sim


def test_hash_embedder_is_deterministic() -> None:
    e = HashEmbedder(dimension=64)
    a = e.embed(["python typing"])[0]
    b = e.embed(["python typing"])[0]
    assert np.array_equal(a, b)


def test_hash_embedder_distinguishes_different_text() -> None:
    e = HashEmbedder(dimension=128)
    a = e.embed(["python typing generators"])
    b = e.embed(["rust ownership borrow checker"])
    sim = cosine_sim(a[0], b)[0]
    assert sim < 0.5


def test_hash_embedder_self_similarity_is_high() -> None:
    e = HashEmbedder(dimension=128)
    vecs = e.embed(["python typing", "python typing"])
    sim = cosine_sim(vecs[0], vecs[1:])[0]
    assert sim == pytest.approx(1.0)


def test_hash_embedder_rejects_tiny_dim() -> None:
    with pytest.raises(ValueError):
        HashEmbedder(dimension=4)


def test_cosine_sim_zero_vector_returns_zero() -> None:
    a = np.zeros(8, dtype=np.float32)
    matrix = np.eye(3, 8, dtype=np.float32)
    sims = cosine_sim(a, matrix)
    assert sims.shape == (3,)
    assert np.all(sims == 0.0)


def test_embed_empty_list_returns_empty_matrix() -> None:
    e = HashEmbedder(dimension=32)
    m = e.embed([])
    assert m.shape == (0, 32)
