"""BM25 lexical retrieval over a category's contribution corpus.

Lightweight (~50 LOC, pure Python, no model download). Well-suited
for short factual snippets where exact term matching matters more
than paraphrase. The category partition is the routing target; this
index ranks within that partition.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import STATUS_APPROVED, ContributionStore

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass(frozen=True, slots=True)
class ScoredContribution:
    contribution: Contribution
    score: float


@dataclass(frozen=True, slots=True)
class BM25Index:
    """Pre-tokenized BM25 index over a fixed list of contributions."""

    contributions: tuple[Contribution, ...]
    docs: tuple[tuple[str, ...], ...]
    doc_lens: tuple[int, ...]
    avg_doc_len: float
    df: dict[str, int]
    k1: float = 1.5
    b: float = 0.75

    @classmethod
    def build(
        cls,
        contributions: list[Contribution],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> BM25Index:
        docs = tuple(tuple(_tokenize(c.text)) for c in contributions)
        doc_lens = tuple(len(d) for d in docs)
        avg = sum(doc_lens) / max(len(docs), 1)
        df: dict[str, int] = {}
        for doc in docs:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        return cls(
            contributions=tuple(contributions),
            docs=docs,
            doc_lens=doc_lens,
            avg_doc_len=avg,
            df=df,
            k1=k1,
            b=b,
        )

    def _idf(self, term: str) -> float:
        n = len(self.docs)
        df = self.df.get(term, 0)
        return math.log((n - df + 0.5) / (df + 0.5) + 1)

    def _score(self, q_tokens: list[str], doc_idx: int) -> float:
        doc_len = self.doc_lens[doc_idx]
        if doc_len == 0:
            return 0.0
        tf = Counter(self.docs[doc_idx])
        s = 0.0
        for term in q_tokens:
            t = tf.get(term, 0)
            if t == 0:
                continue
            idf = self._idf(term)
            num = t * (self.k1 + 1)
            denom = t + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            s += idf * num / denom
        return s

    def rank(self, query: str, top_k: int) -> list[ScoredContribution]:
        if not self.contributions:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        scored = [(i, self._score(q_tokens, i)) for i in range(len(self.contributions))]
        scored = [s for s in scored if s[1] > 0.0]
        scored.sort(key=lambda r: (-r[1], self.contributions[r[0]].contribution_id))
        return [
            ScoredContribution(contribution=self.contributions[i], score=s)
            for i, s in scored[:top_k]
        ]


class Retriever:
    """Per-category BM25 retrieval. Only returns peer-approved contributions."""

    def __init__(
        self, store: ContributionStore, *, status: str = STATUS_APPROVED
    ) -> None:
        self._store = store
        self._status = status
        self._cache: dict[str, BM25Index] = {}

    def invalidate(self, category_id: str | None = None) -> None:
        if category_id is None:
            self._cache.clear()
        else:
            self._cache.pop(category_id, None)

    def retrieve(
        self, query: str, category_id: str, top_k: int = 3
    ) -> list[ScoredContribution]:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        if category_id not in self._cache:
            self._cache[category_id] = BM25Index.build(
                self._store.list_by_category(category_id, status=self._status)
            )
        return self._cache[category_id].rank(query, top_k)
