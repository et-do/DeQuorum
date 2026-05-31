"""Embedder abstraction: lazy-loaded sentence-transformers + deterministic mock."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

FloatMatrix = NDArray[np.float32]
FloatVec = NDArray[np.float32]


class Embedder(Protocol):
    name: str
    dimension: int

    def embed(self, texts: list[str]) -> FloatMatrix: ...


def cosine_sim(a: FloatVec, matrix: FloatMatrix) -> FloatVec:
    """Cosine similarity between vector a (d,) and `matrix` (n, d). Returns (n,)."""
    a_norm = np.linalg.norm(a)
    if a_norm == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    m_norms = np.linalg.norm(matrix, axis=1)
    safe = np.where(m_norms == 0, 1.0, m_norms)
    sims = (matrix @ a) / (a_norm * safe)
    return np.where(m_norms == 0, 0.0, sims).astype(np.float32)


class SentenceTransformerEmbedder:
    """Wraps a HuggingFace sentence-transformers model. Lazy-loaded on first call."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_folder: str | Path | None = None,
    ) -> None:
        self._model_name = model_name
        self._cache_folder = str(cache_folder) if cache_folder else None
        self._model = None
        self._dim: int | None = None

    @property
    def name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._dim is None:
            self._ensure_loaded()
        assert self._dim is not None
        return self._dim

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            self._model_name, cache_folder=self._cache_folder
        )
        self._dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> FloatMatrix:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        self._ensure_loaded()
        assert self._model is not None
        vecs = self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=False
        )
        return vecs.astype(np.float32)


class HashEmbedder:
    """Deterministic, dependency-free embedder for tests. Maps tokens → hash bins."""

    def __init__(self, dimension: int = 64) -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self._dim = dimension
        self.name = f"hash-{dimension}"

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> FloatMatrix:
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for token in t.lower().split():
                h = hashlib.blake2b(token.encode(), digest_size=8).digest()
                idx = int.from_bytes(h[:4], "little") % self._dim
                sign = 1.0 if h[4] & 1 else -1.0
                out[i, idx] += sign
        return out
