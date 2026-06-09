from __future__ import annotations

from collections.abc import Iterator

from dequorum.benchmark.novelty import NOVELTY_FACTS, run_novelty_benchmark
from dequorum.eval.judge import _norm


class _EchoSystemModel:
    """Returns the system prompt as the answer — simulates a model that
    perfectly uses whatever context it is handed, and nothing more."""

    def complete(self, system: str, user: str) -> str:
        return system

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield system


def test_every_fact_gold_is_present_in_its_note() -> None:
    # If the gold phrases aren't in the note, grounding cannot help — the
    # corpus would be measuring nothing.
    for f in NOVELTY_FACTS:
        note = _norm(f.note)
        for g in f.gold:
            assert _norm(g) in note, f"gold {g!r} missing from note: {f.note}"


def test_grounding_lift_is_measured() -> None:
    rep = run_novelty_benchmark(_EchoSystemModel(), facts=NOVELTY_FACTS[:4])
    assert len(rep.results) == 4
    # The grounded system contains the note (and its gold); the base system
    # does not — so grounded recall must exceed base recall.
    assert rep.mean_grounded > rep.mean_base
    assert rep.lift > 0
    assert 0.0 <= rep.mean_base <= 1.0 and 0.0 <= rep.mean_grounded <= 1.0


def test_every_fact_has_a_distinct_paraphrase() -> None:
    # The memorization test needs a held-out paraphrase per fact, different
    # from the training query.
    for f in NOVELTY_FACTS:
        assert f.paraphrase, f"missing paraphrase: {f.query}"
        assert f.paraphrase != f.query
