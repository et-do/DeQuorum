"""Fast benchmark: routing decisions only, no model generation.

The full 3-condition benchmark in `runner.py` is gated by Ollama
generation latency (~30-60s per query), which caps the practical N at
~15. Routing and refusal decisions, however, are entirely
deterministic in the embedding/keyword router — no model calls
involved. This module runs JUST that layer over arbitrary-sized
question pools, so the whitepaper's §7.2 routing claim can be
validated at N=127+ in seconds rather than hours.

Outputs structured statistics suitable for inclusion in benchmark
reports.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from dequorum.benchmark.questions import BenchmarkQuestion
from dequorum.core.errors import CompositionError


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    question: BenchmarkQuestion
    selected_category_id: str | None  # None if router rejected
    score: float | None  # routing similarity score, if available
    error: str | None = None


@dataclass(slots=True)
class BucketStats:
    bucket: str
    n: int = 0
    routed: int = 0  # router accepted (selected_category_id is not None)
    refused: int = 0
    error: int = 0
    # Per-expert hit counts among accepted decisions; useful for
    # confirming routing isn't all collapsing into one expert.
    by_category: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    # Score distribution for accepted decisions.
    scores: list[float] = field(default_factory=list)

    @property
    def accept_rate(self) -> float:
        return self.routed / self.n if self.n else 0.0

    @property
    def refuse_rate(self) -> float:
        return self.refused / self.n if self.n else 0.0

    @property
    def mean_score(self) -> float | None:
        return sum(self.scores) / len(self.scores) if self.scores else None


@dataclass(slots=True)
class RoutingReport:
    decisions: list[RoutingDecision] = field(default_factory=list)
    by_bucket: dict[str, BucketStats] = field(default_factory=dict)

    def add(self, decision: RoutingDecision) -> None:
        self.decisions.append(decision)
        stats = self.by_bucket.setdefault(
            decision.question.bucket, BucketStats(bucket=decision.question.bucket)
        )
        stats.n += 1
        if decision.error is not None:
            stats.error += 1
        elif decision.selected_category_id is None:
            stats.refused += 1
        else:
            stats.routed += 1
            stats.by_category[decision.selected_category_id] += 1
            if decision.score is not None:
                stats.scores.append(decision.score)


def run_routing_benchmark(
    questions: Iterable[BenchmarkQuestion],
    *,
    router: object,
    top_k: int = 1,
) -> RoutingReport:
    """Score `router.route(question, top_k=top_k)` over `questions`.

    The router only needs a `.route(text, top_k=…) -> RoutingResult`
    method whose selected entries expose `.category.category_id` and
    `.score`. Both EmbeddingRouter and KeywordRouter satisfy that
    shape after the v0.2 expert→category collapse.
    """
    report = RoutingReport()
    for q in questions:
        try:
            result = router.route(q.text, top_k=top_k)  # type: ignore[attr-defined]
        except CompositionError as exc:
            report.add(RoutingDecision(q, None, None, error=str(exc)))
            continue
        if not result.selected:
            report.add(RoutingDecision(q, None, None))
            continue
        sel = result.selected[0]
        report.add(
            RoutingDecision(
                q,
                selected_category_id=sel.category.category_id,
                score=float(sel.score),
            )
        )
    return report


def write_markdown_report(
    report: RoutingReport,
    output_path: Path,
    *,
    title: str = "DeQuorum routing-only benchmark report",
    router_label: str = "router",
    routable_category_ids: tuple[str, ...] | None = None,
) -> None:
    """Render bucket-level statistics in Markdown."""
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- **Router:** `{router_label}`")
    lines.append(f"- **Total questions:** {len(report.decisions)}")
    if routable_category_ids is not None:
        lines.append(
            f"- **Routable categories:** {len(routable_category_ids)} — "
            + ", ".join(sorted(routable_category_ids))
        )
    lines.append("")
    lines.append(
        "Each row is a question bucket. **Accept rate** is the fraction "
        "the router was willing to assign to a category; for OOD buckets "
        "the desired rate is **0%** (no qualified category exists)."
    )
    lines.append("")
    lines.append("## Bucket-level results")
    lines.append("")
    lines.append(
        "| Bucket | N | Routed | Refused | Errors | Accept rate | Mean score |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for bucket in sorted(report.by_bucket):
        s = report.by_bucket[bucket]
        mean = f"{s.mean_score:.2f}" if s.mean_score is not None else "—"
        lines.append(
            f"| `{bucket}` | {s.n} | {s.routed} | {s.refused} | {s.error} | "
            f"{s.accept_rate * 100:.0f}% | {mean} |"
        )

    lines.append("")
    lines.append("## Per-category hit distribution (accepted decisions only)")
    lines.append("")
    lines.append("| Bucket | Category | Hits |")
    lines.append("| --- | --- | ---: |")
    for bucket in sorted(report.by_bucket):
        s = report.by_bucket[bucket]
        for cat in sorted(s.by_category):
            lines.append(f"| `{bucket}` | `{cat}` | {s.by_category[cat]} |")

    lines.append("")
    lines.append("## Per-decision detail")
    lines.append("")
    lines.append(
        "Collapse-expand if you're spot-checking; useful when investigating "
        "a single bucket's behavior."
    )
    lines.append("")
    for bucket in sorted(report.by_bucket):
        bucket_rows = [d for d in report.decisions if d.question.bucket == bucket]
        lines.append(
            f"<details><summary><code>{bucket}</code> · "
            f"{len(bucket_rows)} questions</summary>"
        )
        lines.append("")
        lines.append("| # | Question | Routed to | Score |")
        lines.append("| ---: | --- | --- | ---: |")
        for i, d in enumerate(bucket_rows, start=1):
            target = d.selected_category_id or "_(refused)_"
            score = f"{d.score:.2f}" if d.score is not None else "—"
            # Truncate long questions for table readability.
            qt = d.question.text
            if len(qt) > 110:
                qt = qt[:107] + "…"
            lines.append(f"| {i} | {qt} | `{target}` | {score} |")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
