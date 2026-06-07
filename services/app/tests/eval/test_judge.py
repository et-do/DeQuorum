from __future__ import annotations

from collections.abc import Iterator

from dequorum.benchmark.questions import SEED_QUESTIONS
from dequorum.eval import KeywordRecallJudge, LLMJudge, gold_for
from dequorum.eval.gold import SEEDED_GOLD


def test_keyword_recall_full_partial_none() -> None:
    judge = KeywordRecallJudge()
    ref = ("QUIC", "UDP")
    assert (
        judge.score(query="q", answer="HTTP/3 runs on QUIC over UDP", reference=ref)
        == 1.0
    )
    assert judge.score(query="q", answer="it uses QUIC", reference=ref) == 0.5
    assert judge.score(query="q", answer="no idea", reference=ref) == 0.0
    assert judge.score(query="q", answer="anything", reference=()) == 0.0


def test_keyword_recall_is_case_and_punctuation_insensitive() -> None:
    judge = KeywordRecallJudge()
    score = judge.score(
        query="q",
        answer="The annotation is Generator[int, None, str].",
        reference=("Generator", "int", "None", "str"),
    )
    assert score == 1.0


class _FixedModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    def complete(self, system: str, user: str) -> str:
        return self.reply

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.reply


def test_llm_judge_parses_and_normalizes() -> None:
    assert LLMJudge(_FixedModel("8")).score(query="q", answer="a", reference=()) == 0.8
    assert (
        LLMJudge(_FixedModel("Score: 10/10")).score(query="q", answer="a", reference=())
        == 1.0
    )
    # clamps out-of-range and handles non-numeric gracefully
    assert LLMJudge(_FixedModel("12")).score(query="q", answer="a", reference=()) == 1.0
    assert (
        LLMJudge(_FixedModel("no number here")).score(
            query="q", answer="a", reference=()
        )
        == 0.0
    )


def test_every_seeded_question_has_gold() -> None:
    seeded = [q for q in SEED_QUESTIONS if q.bucket == "seeded"]
    assert seeded, "expected seeded questions"
    for q in seeded:
        assert gold_for(q.text), f"missing gold for: {q.text}"
    # no stray gold entries that don't match a seeded question
    seeded_texts = {q.text for q in seeded}
    assert set(SEEDED_GOLD) <= seeded_texts


def test_gold_questions_expand_the_faithfulness_sample() -> None:
    from dequorum.eval import gold_questions

    qs = gold_questions()
    assert len(qs) > len([q for q in SEED_QUESTIONS if q.bucket == "seeded"])
    for q in qs:
        assert gold_for(q.text), f"gold question missing gold: {q.text}"
