from __future__ import annotations

import pytest

from ai_playground.composition import (
    STRATEGIES,
    ConcatStrategy,
    PickBestStrategy,
    make_strategy,
)
from ai_playground.core.node import Signature
from ai_playground.experts import Expert
from ai_playground.pipeline import ExpertAnswer
from ai_playground.retrieval import ScoredContribution


def _expert(eid: str) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=eid.title(),
        specialty_tags=(),
        system_prompt="prompt",
        signing_key=eid.encode(),
    )


def _answer(
    eid: str,
    text: str,
    routing_score: float = 1.0,
    retrieved: tuple[ScoredContribution, ...] = (),
) -> ExpertAnswer:
    sig = Signature.sign(
        node_id=eid, signing_key=eid.encode(), payload="q", result=text
    )
    return ExpertAnswer(
        expert=_expert(eid),
        answer=text,
        signature=sig,
        retrieved=retrieved,
        routing_score=routing_score,
    )


# --- ConcatStrategy ---


def test_concat_single_answer_no_header() -> None:
    r = ConcatStrategy().compose((_answer("a", "alpha"),))
    assert r.text == "alpha"
    assert r.chosen == ("a",)


def test_concat_multiple_includes_section_headers() -> None:
    r = ConcatStrategy().compose((_answer("a", "alpha"), _answer("b", "beta")))
    assert "alpha" in r.text
    assert "beta" in r.text
    assert "---" in r.text
    assert r.chosen == ("a", "b")


def test_concat_empty_returns_empty() -> None:
    r = ConcatStrategy().compose(())
    assert r.text == ""
    assert r.chosen == ()


# --- PickBestStrategy ---


def test_pick_best_chooses_highest_routing_score() -> None:
    answers = (
        _answer("a", "alpha", routing_score=0.2),
        _answer("b", "beta", routing_score=0.8),
        _answer("c", "gamma", routing_score=0.5),
    )
    r = PickBestStrategy().compose(answers)
    assert r.chosen == ("b",)
    assert r.text == "beta"


def test_pick_best_breaks_ties_with_retrieval_score() -> None:
    sc1 = ScoredContribution(contribution=None, score=1.0)  # type: ignore[arg-type]
    sc2 = ScoredContribution(contribution=None, score=5.0)  # type: ignore[arg-type]
    answers = (
        _answer("a", "alpha", routing_score=0.5, retrieved=(sc1,)),
        _answer("b", "beta", routing_score=0.5, retrieved=(sc2, sc2)),
    )
    r = PickBestStrategy().compose(answers)
    assert r.chosen == ("b",)


def test_pick_best_deterministic_tiebreak_on_expert_id() -> None:
    answers = (
        _answer("zeta", "z"),
        _answer("alpha", "a"),
    )
    r = PickBestStrategy().compose(answers)
    assert r.chosen == ("alpha",)


def test_pick_best_empty() -> None:
    r = PickBestStrategy().compose(())
    assert r.text == ""
    assert r.chosen == ()


# --- factory ---


def test_make_strategy_returns_known_names() -> None:
    assert isinstance(make_strategy("concat"), ConcatStrategy)
    assert isinstance(make_strategy("pick_best"), PickBestStrategy)


def test_make_strategy_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown composition strategy"):
        make_strategy("ensemble")


def test_strategies_registry_lists_both() -> None:
    assert set(STRATEGIES) == {"concat", "pick_best"}
