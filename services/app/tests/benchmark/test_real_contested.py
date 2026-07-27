from __future__ import annotations

from dequorum.benchmark.real_contested import REAL_CONTESTED_FACTS
from dequorum.eval import KeywordRecallJudge


def test_corpus_is_nonempty_and_well_formed() -> None:
    assert len(REAL_CONTESTED_FACTS) >= 40
    for f in REAL_CONTESTED_FACTS:
        assert f.query and f.note and f.false_note and f.paraphrase
        assert f.gold and f.false_gold


def test_gold_and_false_twin_are_distinguishable() -> None:
    """The contested-regime invariant: the true note contains the gold and NOT the
    misconception token, and the false twin contains the misconception and NOT the
    gold. Otherwise the keyword grader could not separate them and the experiment
    would be meaningless."""
    judge = KeywordRecallJudge()
    for f in REAL_CONTESTED_FACTS:
        # gold recalled from the true note, not from the false twin
        assert judge.score(query=f.query, answer=f.note, reference=f.gold) == 1.0, (
            f.query
        )
        assert (
            judge.score(query=f.query, answer=f.false_note, reference=f.gold) == 0.0
        ), f.query
        # misconception recalled from the false twin, not from the true note
        assert (
            judge.score(query=f.query, answer=f.false_note, reference=f.false_gold)
            == 1.0
        ), f.query
        assert (
            judge.score(query=f.query, answer=f.note, reference=f.false_gold) == 0.0
        ), f.query
