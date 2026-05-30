from __future__ import annotations

from ai_playground.contribution_store import ContributionStore
from ai_playground.contributions import Contribution
from ai_playground.retrieval import BM25Index, Retriever


def _c(expert: str, text: str, *, key: bytes = b"k") -> Contribution:
    return Contribution.create(
        expert_id=expert,
        contributor_id=expert,
        text=text,
        citations=(),
        signing_key=key,
    )


def test_bm25_empty_corpus_returns_empty() -> None:
    idx = BM25Index.build([])
    assert idx.rank("anything", top_k=3) == []


def test_bm25_ranks_relevant_docs_first() -> None:
    docs = [
        _c("py", "How to install packages with uv and pip"),
        _c("py", "Asyncio tasks and the event loop"),
        _c("py", "Typing a generator function with Generator"),
    ]
    idx = BM25Index.build(docs)
    results = idx.rank("how do I type a generator function", top_k=3)
    assert results[0].contribution.text.startswith("Typing a generator")


def test_bm25_drops_zero_score_documents() -> None:
    docs = [
        _c("py", "rust ownership semantics"),
        _c("py", "python typing semantics"),
    ]
    idx = BM25Index.build(docs)
    results = idx.rank("python typing", top_k=5)
    assert len(results) == 1
    assert "python typing" in results[0].contribution.text


def test_retriever_caches_per_expert() -> None:
    store = ContributionStore()
    store.add(_c("py", "python typing fact"))
    store.add(_c("rs", "rust ownership fact"))
    r = Retriever(store)
    py_results = r.retrieve("typing", "py", top_k=3)
    assert len(py_results) == 1
    rs_results = r.retrieve("ownership", "rs", top_k=3)
    assert len(rs_results) == 1


def test_retriever_invalidate_refreshes_after_new_contribution() -> None:
    store = ContributionStore()
    store.add(_c("py", "original fact about typing"))
    r = Retriever(store)
    assert len(r.retrieve("typing", "py", top_k=3)) == 1

    store.add(_c("py", "second typing fact"))
    # without invalidation, still uses cached index (1 doc)
    assert len(r.retrieve("typing", "py", top_k=3)) == 1
    r.invalidate("py")
    assert len(r.retrieve("typing", "py", top_k=3)) == 2
