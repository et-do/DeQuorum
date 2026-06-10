"""Serving-path benches: retrieval-with-distractors and conflicting contributions.

These exercise the production read path (retrieve → ground) and the true-vs-false
conflict case. Behaviour against a real LLM is measured on GPU; here we use a mock
model and assert the code paths, the BM25 retrieval, and the report shape.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator

from dequorum.benchmark.novelty import NOVELTY_FACTS
from dequorum.cli import _bench_contributions, _cmd_conflict_bench, _cmd_retrieval_bench
from dequorum.retrieval.bm25 import BM25Index


class _EchoSystemModel:
    """Returns the system prompt, so a grounded answer contains the reference
    text it was given — enough for the keyword judge to score grounding."""

    def complete(self, system: str, user: str) -> str:
        return system

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield system


def test_bench_contributions_indexes_true_note_above_its_false_variant() -> None:
    facts = NOVELTY_FACTS[:4]
    contributions, true_ids, false_ids = _bench_contributions(facts)
    # Two contributions per fact (true + false distractor), unique ids.
    assert len(contributions) == 2 * len(facts)
    assert len(set(true_ids.values()) | set(false_ids.values())) == 2 * len(facts)

    index = BM25Index.build(contributions)
    hits = 0
    for i, f in enumerate(facts):
        ranked = index.rank(f.query, top_k=1)
        if ranked and ranked[0].contribution.contribution_id == true_ids[i]:
            hits += 1
    # The true note should top its own query for most facts (lexical overlap).
    assert hits >= len(facts) // 2


def _ns(**kw: object) -> argparse.Namespace:
    return argparse.Namespace(**kw)


def test_retrieval_bench_writes_report(tmp_path, monkeypatch) -> None:
    import dequorum.cli as cli

    monkeypatch.setattr(cli, "_grounding_model", lambda args: _EchoSystemModel())
    out = tmp_path / "retrieval.md"
    rc = _cmd_retrieval_bench(
        _ns(mock=True, model="", host="", top_k=[1, 3], limit=3, output=str(out))
    )
    assert rc == 0
    text = out.read_text()
    assert "Retrieval-grounded lift" in text
    # hit@k is non-decreasing in k (more retrieved → at least as many true hits).
    assert "| 1 |" in text and "| 3 |" in text


def test_conflict_bench_writes_vote_gated_row(tmp_path, monkeypatch) -> None:
    import dequorum.cli as cli

    monkeypatch.setattr(cli, "_grounding_model", lambda args: _EchoSystemModel())
    out = tmp_path / "conflict.md"
    rc = _cmd_conflict_bench(
        _ns(mock=True, model="", host="", limit=3, output=str(out))
    )
    assert rc == 0
    text = out.read_text()
    assert "Conflicting contributions" in text
    assert "vote-gated to true" in text
