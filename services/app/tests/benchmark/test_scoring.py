from __future__ import annotations

from dequorum.benchmark.questions import SEED_QUESTIONS
from dequorum.benchmark.runner import (
    BenchmarkReport,
    BenchmarkResult,
    ConditionResult,
    score_conditions,
)
from dequorum.eval import KeywordRecallJudge, gold_for


def test_score_conditions_quantifies_b_gt_c_gt_a() -> None:
    q = next(x for x in SEED_QUESTIONS if x.bucket == "seeded")
    gold = gold_for(q.text)
    report = BenchmarkReport(
        results=(
            BenchmarkResult(
                question=q,
                vanilla=ConditionResult(answer="totally unrelated prose"),
                dequorum_full=ConditionResult(answer=" ".join(gold)),  # all facts
                dequorum_no_retrieval=ConditionResult(answer=gold[0]),  # one fact
            ),
        ),
        model_label="mock",
        router_label="x",
    )
    scores = score_conditions(report, KeywordRecallJudge())
    assert scores.n == 1
    assert scores.dequorum_full > scores.dequorum_no_retrieval > scores.vanilla


def test_score_conditions_handles_no_gold_questions() -> None:
    q = next(x for x in SEED_QUESTIONS if x.bucket == "out_of_domain")
    report = BenchmarkReport(
        results=(
            BenchmarkResult(
                question=q,
                vanilla=ConditionResult(answer="x"),
                dequorum_full=ConditionResult(answer="y"),
                dequorum_no_retrieval=ConditionResult(answer="z"),
            ),
        ),
        model_label="mock",
        router_label="x",
    )
    scores = score_conditions(report, KeywordRecallJudge())
    assert scores.n == 0  # no gold → nothing scored, no crash
