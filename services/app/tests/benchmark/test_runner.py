from __future__ import annotations

from pathlib import Path

from dequorum.benchmark import SEED_QUESTIONS, run_benchmark
from dequorum.benchmark.questions import BenchmarkQuestion
from dequorum.benchmark.runner import write_markdown_report
from dequorum.experts import ExpertRegistry
from dequorum.experts.seeds import build_seed_registry
from dequorum.inference.base_model import MockBaseModel
from dequorum.knowledge.seeds import populate as populate_seed_contributions
from dequorum.knowledge.store import ContributionStore
from dequorum.routing.keyword import KeywordRouter


def _kw_router_factory(registry: ExpertRegistry) -> KeywordRouter:
    return KeywordRouter(registry, min_score=1.0)


def test_seed_question_buckets_cover_all_three() -> None:
    buckets = {q.bucket for q in SEED_QUESTIONS}
    assert buckets == {"seeded", "unseeded", "out_of_domain"}


def test_runner_produces_three_conditions_per_question() -> None:
    store = ContributionStore()
    populate_seed_contributions(store)
    try:
        report = run_benchmark(
            questions=SEED_QUESTIONS[:2],
            model=MockBaseModel(),
            registry=build_seed_registry(),
            store=store,
            router_factory=_kw_router_factory,
            model_label="mock",
        )
    finally:
        store.close()
    assert len(report.results) == 2
    for r in report.results:
        # vanilla always produces an answer (mock never errors)
        assert r.vanilla.answer is not None
        # full and no-retrieval may refuse for out-of-domain
        # but for our first 2 (seeded), both should succeed
        assert r.dequorum_full.answer is not None
        assert r.dequorum_no_retrieval.answer is not None


def test_runner_handles_refusal_for_out_of_domain() -> None:
    # Pick an out-of-domain question; force KeywordRouter to find nothing
    out_of_domain_q = next(q for q in SEED_QUESTIONS if q.bucket == "out_of_domain")
    registry = build_seed_registry()
    store = ContributionStore()
    populate_seed_contributions(store)
    # Use a router with fallback_to_all=False so out-of-domain queries refuse
    try:
        report = run_benchmark(
            questions=(out_of_domain_q,),
            model=MockBaseModel(),
            registry=registry,
            store=store,
            router_factory=lambda reg: KeywordRouter(
                reg, fallback_to_all=False, min_score=999.0
            ),
            model_label="mock",
        )
    finally:
        store.close()
    r = report.results[0]
    assert r.vanilla.answer is not None  # vanilla always answers
    assert r.dequorum_full.answer is None
    assert r.dequorum_full.error  # refusal recorded
    assert r.dequorum_no_retrieval.answer is None


def test_runner_chain_length_reflects_retrieval(tmp_path: Path) -> None:
    store = ContributionStore()
    populate_seed_contributions(store)
    try:
        report = run_benchmark(
            questions=(
                BenchmarkQuestion(
                    text="how do I type a generator function",
                    bucket="seeded",
                    expected_behavior="should retrieve python-typing facts",
                ),
            ),
            model=MockBaseModel(),
            registry=build_seed_registry(),
            store=store,
            router_factory=_kw_router_factory,
            model_label="mock",
        )
    finally:
        store.close()
    r = report.results[0]
    # full pipeline should have at least 1 contribution + 1 expert sig in the chain
    assert r.dequorum_full.chain_length >= 1
    # no-retrieval should have just the expert sig (chain length 1)
    assert r.dequorum_no_retrieval.chain_length >= 1
    # full should have more signatures than no-retrieval if retrieval found anything
    if r.dequorum_full.retrieved_count > 0:
        assert r.dequorum_full.chain_length > r.dequorum_no_retrieval.chain_length


def test_markdown_report_written_with_expected_sections(tmp_path: Path) -> None:
    store = ContributionStore()
    populate_seed_contributions(store)
    try:
        report = run_benchmark(
            questions=SEED_QUESTIONS[:3],
            model=MockBaseModel(),
            registry=build_seed_registry(),
            store=store,
            router_factory=_kw_router_factory,
            model_label="mock-test",
        )
    finally:
        store.close()
    output = tmp_path / "report.md"
    write_markdown_report(report, output)
    text = output.read_text()
    assert "# DeQuorum benchmark report" in text
    assert "mock-test" in text
    assert "A) Vanilla baseline" in text
    assert "B) DeQuorum full" in text
    assert "C) DeQuorum no-retrieval" in text
