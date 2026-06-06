"""Benchmark runner: per-question 3-condition comparison, Markdown report writer."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dequorum.benchmark.questions import BenchmarkQuestion
from dequorum.core.errors import CompositionError
from dequorum.inference.base_model import BaseModel
from dequorum.inference.pipeline import NetworkResponse, Pipeline
from dequorum.knowledge.store import ContributionStore
from dequorum.retrieval import Retriever
from dequorum.taxonomy.category import Category

VANILLA_SYSTEM_PROMPT = (
    "You are a helpful, accurate AI assistant. Answer the user's question concisely."
)

RouterFactory = Callable[[Sequence[Category]], object]
"""Returns a Router (KeywordRouter | EmbeddingRouter) given a list of
routable categories."""


@dataclass(frozen=True, slots=True)
class ConditionResult:
    answer: str | None
    error: str | None = None
    routing_summary: str | None = None
    retrieved_count: int = 0
    chain_length: int = 0


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    question: BenchmarkQuestion
    vanilla: ConditionResult
    dequorum_full: ConditionResult
    dequorum_no_retrieval: ConditionResult


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    results: tuple[BenchmarkResult, ...]
    model_label: str
    router_label: str
    notes: tuple[str, ...] = field(default_factory=tuple)


def _summarize_routing(response: NetworkResponse | None) -> str | None:
    if response is None:
        return None
    selected = ", ".join(
        f"{s.category.category_id}({s.score:.2f})" for s in response.routing.selected
    )
    return f"{response.routing.method}: [{selected}]"


def _run_pipeline_safely(
    pipeline: Pipeline, question: str
) -> tuple[NetworkResponse | None, str | None]:
    try:
        return pipeline.query(question), None
    except CompositionError as exc:
        return None, str(exc)


def _vanilla_condition(model: BaseModel, question: str) -> ConditionResult:
    try:
        answer = model.complete(system=VANILLA_SYSTEM_PROMPT, user=question)
    except CompositionError as exc:
        return ConditionResult(answer=None, error=str(exc))
    return ConditionResult(answer=answer)


def _dequorum_condition(
    pipeline: Pipeline, question: str, *, with_retrieval: bool
) -> ConditionResult:
    response, error = _run_pipeline_safely(pipeline, question)
    if response is None:
        return ConditionResult(answer=None, error=error)
    answer = response.answer
    return ConditionResult(
        answer=answer.answer if answer is not None else "",
        routing_summary=_summarize_routing(response),
        retrieved_count=(len(answer.retrieved) if (answer and with_retrieval) else 0),
        chain_length=len(response.proof.chain),
    )


def run_benchmark(
    questions: tuple[BenchmarkQuestion, ...] | list[BenchmarkQuestion],
    *,
    model: BaseModel,
    categories: Sequence[Category],
    store: ContributionStore,
    router_factory: RouterFactory,
    retrieve_top_k: int = 3,
    model_label: str = "unknown",
    progress: Callable[[int, int, str], None] | None = None,
) -> BenchmarkReport:
    """Run all questions through the 3 conditions and return a structured report.

    `progress` callback gets (index, total, question_text) per question
    so callers can print live status — useful when the real model takes
    ~30-60s per generation.
    """
    results: list[BenchmarkResult] = []
    for i, q in enumerate(questions, start=1):
        if progress is not None:
            progress(i, len(questions), q.text)

        vanilla = _vanilla_condition(model, q.text)

        full_pipeline = Pipeline(
            router=router_factory(categories),
            model=model,
            retriever=Retriever(store),
            retrieve_top_k=retrieve_top_k,
        )
        full = _dequorum_condition(full_pipeline, q.text, with_retrieval=True)

        no_retrieval_pipeline = Pipeline(
            router=router_factory(categories),
            model=model,
            retriever=None,
            retrieve_top_k=retrieve_top_k,
        )
        no_retrieval = _dequorum_condition(
            no_retrieval_pipeline, q.text, with_retrieval=False
        )

        results.append(
            BenchmarkResult(
                question=q,
                vanilla=vanilla,
                dequorum_full=full,
                dequorum_no_retrieval=no_retrieval,
            )
        )

    return BenchmarkReport(
        results=tuple(results),
        model_label=model_label,
        router_label=router_factory.__name__
        if hasattr(router_factory, "__name__")
        else "router",
    )


def write_markdown_report(report: BenchmarkReport, output_path: Path) -> None:
    """Render the report as Markdown so a human can read and judge."""
    lines: list[str] = []
    lines.append("# DeQuorum benchmark report")
    lines.append("")
    lines.append(f"- **Model:** `{report.model_label}`")
    lines.append(f"- **Router:** `{report.router_label}`")
    lines.append(f"- **Questions:** {len(report.results)}")
    lines.append("")
    lines.append("Each question is run three ways:")
    lines.append("")
    lines.append(
        "1. **Vanilla** — bare base model, generic system prompt, no DeQuorum at all."
    )
    lines.append(
        "2. **DeQuorum full** — route → retrieve approved contributions → "
        "category-grounded answer with signed contribution chain."
    )
    lines.append(
        "3. **DeQuorum no-retrieval** — router + category persona only, "
        "contributions skipped (isolates the lift of retrieval)."
    )
    lines.append("")
    lines.append("Read all three. Judge honestly. Watch accuracy, refusal.")
    lines.append("")
    lines.append("---")
    lines.append("")

    buckets = ("seeded", "unseeded", "out_of_domain")
    for bucket in buckets:
        bucket_results = [r for r in report.results if r.question.bucket == bucket]
        if not bucket_results:
            continue
        lines.append(f"## Bucket: `{bucket}` ({len(bucket_results)} questions)")
        lines.append("")
        for idx, r in enumerate(bucket_results, start=1):
            lines.append(f"### {bucket} #{idx}: {r.question.text}")
            lines.append("")
            lines.append(f"_Expected:_ {r.question.expected_behavior}")
            lines.append("")
            lines.append("**A) Vanilla baseline**")
            lines.append("")
            lines.append("```")
            lines.append((r.vanilla.answer or f"[error] {r.vanilla.error}").strip())
            lines.append("```")
            lines.append("")
            lines.append("**B) DeQuorum full (route + retrieve + sign)**")
            lines.append("")
            if r.dequorum_full.answer is None:
                lines.append(f"_Refused:_ `{r.dequorum_full.error}`")
            else:
                lines.append(f"_Routing:_ `{r.dequorum_full.routing_summary}`")
                lines.append(
                    f"_Retrieved contributions:_ "
                    f"{r.dequorum_full.retrieved_count} | "
                    f"_Signature chain:_ {r.dequorum_full.chain_length}"
                )
                lines.append("")
                lines.append("```")
                lines.append(r.dequorum_full.answer.strip())
                lines.append("```")
            lines.append("")
            lines.append(
                "**C) DeQuorum no-retrieval (router + category persona only)**"
            )
            lines.append("")
            if r.dequorum_no_retrieval.answer is None:
                lines.append(f"_Refused:_ `{r.dequorum_no_retrieval.error}`")
            else:
                lines.append(f"_Routing:_ `{r.dequorum_no_retrieval.routing_summary}`")
                lines.append("")
                lines.append("```")
                lines.append(r.dequorum_no_retrieval.answer.strip())
                lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
