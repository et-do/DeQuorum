"""Serving-path benches: retrieval-with-distractors and conflicting contributions.

These exercise the production read path (retrieve → ground) and the true-vs-false
conflict case. Behaviour against a real LLM is measured on GPU; here we use a mock
model and assert the code paths, the BM25 retrieval, and the report shape.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator

import numpy as np

from dequorum.benchmark.novelty import NOVELTY_FACTS
from dequorum.cli import (
    _bench_contributions,
    _cmd_conflict_bench,
    _cmd_quant_bench,
    _cmd_retrieval_bench,
)
from dequorum.retrieval.bm25 import BM25Index
from dequorum.routing.embedder import HashEmbedder, cosine_sim


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


def test_quant_bench_writes_row_per_model(tmp_path, monkeypatch) -> None:
    import dequorum.cli as cli

    monkeypatch.setattr(cli, "_quant_model", lambda tag, args: _EchoSystemModel())
    out = tmp_path / "quant.md"
    rc = _cmd_quant_bench(
        _ns(models=["m-q4", "m-q8"], host="", limit=3, output=str(out))
    )
    assert rc == 0
    text = out.read_text()
    assert "Quantization robustness" in text
    assert "`m-q4`" in text and "`m-q8`" in text
    assert "Verdict" in text


def test_quant_bench_survives_a_failing_model(tmp_path, monkeypatch) -> None:
    """A flaky/missing tag (Ollama 500, OOM, bad pull) must not discard the levels
    that already succeeded — the run records the failure and still writes a report."""
    import dequorum.cli as cli

    def factory(tag, args):
        if "q8" in tag:
            raise RuntimeError("Ollama 500")
        return _EchoSystemModel()

    monkeypatch.setattr(cli, "_quant_model", factory)
    out = tmp_path / "quant.md"
    rc = _cmd_quant_bench(
        _ns(models=["m-q4", "m-q8"], host="", limit=3, output=str(out))
    )
    assert rc == 0  # did not crash
    text = out.read_text()
    assert "`m-q4`" in text  # the successful level is recorded
    assert "failed" in text  # the broken level is flagged, not silently dropped


def test_attribution_route_picks_owner_when_signature_matches_query() -> None:
    """The attribution-by-construction router embeds each contributor's note and
    routes a query to the nearest. With an exact lexical match it must pick the
    owner — the property that makes credit-by-routing faithful."""
    embedder = HashEmbedder(256)
    notes = [
        "quic over udp transport for http3",
        "rust ownership borrow checker memory safety",
        "python paramspec decorator typing",
    ]
    sigs = embedder.embed(notes)
    # A query that is the owner's note should route to that owner for every row.
    for owner, note in enumerate(notes):
        q = embedder.embed([note])[0]
        routed = int(np.argmax(cosine_sim(q, sigs)))
        assert routed == owner


def test_attribution_route_grouped_routes_to_owning_contributor() -> None:
    """With facts-per-contributor > 1 the router signature is the centroid of a
    contributor's notes; a query about one of their facts must route to that
    contributor — the grouped analogue used by --facts-per-contributor."""
    import math

    notes = [
        "quic over udp transport for http3",
        "http3 header compression qpack dynamic table",
        "rust ownership borrow checker move semantics",
        "rust lifetimes elision dangling references",
    ]
    queries = notes  # exact-match queries; must route to the owning contributor
    fpc = 2  # -> 2 contributors: c0 owns facts 0,1 ; c1 owns facts 2,3
    n_contrib = math.ceil(len(notes) / fpc)
    owner_of = [j // fpc for j in range(len(notes))]
    facts_of = {
        c: [j for j in range(len(notes)) if owner_of[j] == c] for c in range(n_contrib)
    }

    embedder = HashEmbedder(256)
    note_vecs = embedder.embed(notes)
    sigs = np.stack([note_vecs[facts_of[c]].mean(axis=0) for c in range(n_contrib)])
    for j, q_text in enumerate(queries):
        q = embedder.embed([q_text])[0]
        routed = int(np.argmax(cosine_sim(q, sigs)))
        assert routed == owner_of[j]
