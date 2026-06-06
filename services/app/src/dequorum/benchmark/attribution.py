"""Attribution benchmark.

Research question: is a cheap proxy (retrieval score) a faithful predictor
of a contribution's *measured causal value* in the answer? The ground truth
is leave-one-out marginal value (dequorum.attribution); this harness
measures it across the seed corpus and reports how well retrieval score —
and the naive flat-credit baseline — track it.

Pairs with the deterministic gaming-resistance result in
tests/attribution/test_marginal.py (duplicate stuffing cannot inflate a
marginal-credit share; it can under flat credit).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dequorum.attribution import ContributionCredit, measure_attribution
from dequorum.benchmark.questions import BenchmarkQuestion
from dequorum.inference.base_model import BaseModel
from dequorum.retrieval import Retriever
from dequorum.routing.embedder import Embedder


@dataclass
class AttributionRow:
    query: str
    category_id: str
    credits: list[ContributionCredit]


@dataclass
class AttributionReport:
    model_label: str
    rows: list[AttributionRow]
    n_pairs: int
    spearman_score_vs_value: float
    mean_marginal: float


def _avg_ranks(a: np.ndarray) -> np.ndarray:
    order = a.argsort()
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(len(a), dtype=float)
    sorted_vals = a[order]
    i, n = 0, len(a)
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation, dependency-free (average-ranked Pearson)."""
    if len(x) < 2:
        return float("nan")
    rx, ry = _avg_ranks(x), _avg_ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def run_attribution_benchmark(
    *,
    questions: Sequence[BenchmarkQuestion],
    router: object,
    store: object,
    model: BaseModel,
    embedder: Embedder,
    retrieve_top_k: int = 3,
    progress: Callable[[int, int, str], None] | None = None,
) -> AttributionReport:
    retriever = Retriever(store)  # type: ignore[arg-type]
    rows: list[AttributionRow] = []
    for i, q in enumerate(questions):
        routing = router.route(q.text, top_k=1)  # type: ignore[attr-defined]
        if not routing.selected:
            continue
        category = routing.selected[0].category
        retrieved = tuple(
            retriever.retrieve(q.text, category.category_id, top_k=retrieve_top_k)
        )
        if len(retrieved) < 2:
            # marginal attribution is only meaningful with ≥2 contributions
            continue
        credits = measure_attribution(
            query=q.text,
            persona_prompt=category.system_prompt,
            retrieved=retrieved,
            model=model,
            embedder=embedder,
        )
        rows.append(AttributionRow(q.text, category.category_id, credits))
        if progress:
            progress(i + 1, len(questions), q.text)

    scores = np.array([c.retrieval_score for r in rows for c in r.credits])
    values = np.array([c.marginal_value for r in rows for c in r.credits])
    return AttributionReport(
        model_label="",
        rows=rows,
        n_pairs=len(scores),
        spearman_score_vs_value=(
            _spearman(scores, values) if len(scores) else float("nan")
        ),
        mean_marginal=float(values.mean()) if len(values) else float("nan"),
    )


def write_attribution_report(report: AttributionReport, path: Path) -> None:
    lines: list[str] = [
        "# Attribution benchmark",
        "",
        f"Model: `{report.model_label}` · queries measured: {len(report.rows)} · "
        f"(contribution, answer) pairs: {report.n_pairs}",
        "",
        "## Is retrieval score a faithful proxy for causal value?",
        "",
        "Ground truth per contribution is leave-one-out **marginal value**: how "
        "much the answer's resemblance to the contribution drops when it is "
        "removed. We correlate that against the cheap retrieval score.",
        "",
        f"- **Spearman(retrieval_score, marginal_value) = "
        f"{report.spearman_score_vs_value:.3f}**",
        f"- Mean marginal value across pairs: {report.mean_marginal:.4f}",
        "- Flat credit (the naive ledger) is constant per citation, so by "
        "construction it has **zero** rank correlation with measured value — it "
        "carries no information about which contribution mattered.",
        "",
        "## Per-query credit",
        "",
    ]
    for r in report.rows:
        lines.append(f"### {r.query}")
        lines.append("")
        lines.append(
            "| contribution | retrieval score | marginal value | credit weight |"
        )
        lines.append("| --- | ---: | ---: | ---: |")
        for c in sorted(r.credits, key=lambda c: c.credit_weight, reverse=True):
            lines.append(
                f"| `{c.contribution_id[:12]}` | {c.retrieval_score:.3f} | "
                f"{c.marginal_value:.4f} | {c.credit_weight:.3f} |"
            )
        lines.append("")
    lines.append("## Gaming resistance")
    lines.append("")
    lines.append(
        "Duplicate-stuffing cannot inflate a contributor's marginal-credit "
        "share (a redundant copy has ~0 marginal value), whereas it does under "
        "flat credit. Proven deterministically in "
        "`tests/attribution/test_marginal.py::"
        "test_duplicate_stuffing_does_not_inflate_marginal_share`."
    )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
