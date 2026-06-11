"""Grounding lift on knowledge the base model cannot have.

Whitepaper Claim 2 — that contributor grounding produces measurably better
answers — is unprovable on facts the base model already knows (the seeded
corpus is mostly base-known, so the lift is marginal; see §8.3). This
benchmark isolates the effect by using *invented* facts: specific, plausible,
but fictional claims that no pretrained model can have memorized. Each is
posed twice — once to the bare model, once with the fact supplied as a
reference — and scored by gold-fact recall. The gap between the two is the
grounding lift, with the base condition acting as a built-in control for
memorization (it should score near zero).

Self-contained: needs only a model and the keyword judge (no store, router,
retrieval, or database), so it runs anywhere a model is reachable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dequorum.eval import KeywordRecallJudge
from dequorum.inference.base_model import BaseModel

_BASE_SYSTEM = "You are a precise assistant. Answer the question concisely."
_GROUNDED_SYSTEM = (
    "You are a precise assistant. Use the reference note below as the "
    "authoritative source; answer the question from it concisely.\n\n"
    "## Reference\n{note}"
)


@dataclass(frozen=True, slots=True)
class NoveltyFact:
    """An invented fact: the reference note, a question over it, the gold key
    phrases a correct answer must contain, and a held-out paraphrase of the
    question. The paraphrase is never trained on; recall on it separates real
    knowledge transfer from memorizing the exact training prompt."""

    note: str
    query: str
    gold: tuple[str, ...]
    paraphrase: str = ""
    # A plausible-but-FALSE variant of the note (wrong values, same shape) and
    # the gold phrases that identify the false claim. Powers two studies:
    #   - judge validation: a good judge scores `note` high and `false_note` low
    #     against the true `gold` (a coarse judge over-credits the false one).
    #   - falsehood propagation: grounding on `false_note` and detecting
    #     `false_gold` in the answer measures whether the model adopts a lie.
    false_note: str = ""
    false_gold: tuple[str, ...] = ()


# Invented facts across several domains. Each is specific and plausible but
# fictional, so a pretrained model cannot answer it without the note.
NOVELTY_FACTS: tuple[NoveltyFact, ...] = (
    NoveltyFact(
        note="The Halberd transport protocol multiplexes streams over a single "
        "UDP socket using fixed 12-byte frame headers and a rotating XOR keystream.",
        query="How large are frame headers in the Halberd transport protocol, and "
        "what does it run over?",
        gold=("12", "byte", "UDP"),
        paraphrase="Which transport does Halberd use, and how many bytes is each "
        "of its frame headers?",
        false_note="The Halberd transport protocol multiplexes streams over a "
        "single TCP socket using fixed 20-byte frame headers.",
        false_gold=("20", "TCP"),
    ),
    NoveltyFact(
        note="In the Pyrolib library, pyro.bind(fn, *, retries) wraps a callable so "
        "it retries on PyroTimeout up to `retries` times with exponential backoff "
        "starting at 50ms.",
        query="In Pyrolib, what does pyro.bind retry on and what is its initial "
        "backoff?",
        gold=("PyroTimeout", "50", "exponential"),
        paraphrase="What's the starting backoff for pyro.bind, what kind of backoff "
        "is it, and which exception does it retry?",
        false_note="In the Pyrolib library, pyro.bind retries on PyroError with "
        "linear backoff starting at 200ms.",
        false_gold=("PyroError", "200", "linear"),
    ),
    NoveltyFact(
        note="The Marrow-Quist bound states that a gossip protocol over n nodes "
        "reaches consensus in at most 3*ceil(log2 n) + 4 rounds under fewer than "
        "n/5 Byzantine faults.",
        query="What Byzantine fault threshold does the Marrow-Quist bound assume?",
        gold=("n/5", "Byzantine"),
        paraphrase="Up to what fraction of nodes can be Byzantine for the "
        "Marrow-Quist bound to hold?",
        false_note="The Marrow-Quist bound holds under fewer than n/3 Byzantine "
        "faults.",
        false_gold=("n/3",),
    ),
    NoveltyFact(
        note="Setting vault.seal_threshold above 0.8 in Cindervault triggers "
        "automatic re-sharding of the secret store across all replicas.",
        query="What happens when vault.seal_threshold exceeds 0.8 in Cindervault?",
        gold=("re-shard", "replicas"),
        paraphrase="In Cindervault, what does raising vault.seal_threshold past 0.8 "
        "do to the secret store?",
        false_note="Setting vault.seal_threshold above 0.5 in Cindervault triggers "
        "a full key rotation of the secret store.",
        false_gold=("0.5", "key rotation"),
    ),
    NoveltyFact(
        note="Zelanocytes are specialized cells in the Tarsk gland that secrete "
        "melanoquin, regulating circadian pigment shifts in deep-sea cephalopods.",
        query="What do zelanocytes secrete, and in which gland are they found?",
        gold=("melanoquin", "Tarsk"),
        paraphrase="Which gland holds the cells that produce melanoquin?",
        false_note="Zelanocytes are specialized cells in the Phlox gland that "
        "secrete luminase.",
        false_gold=("luminase", "Phlox"),
    ),
    NoveltyFact(
        note="Under the GX-9 imaging standard, every frame must embed a 256-bit "
        "provenance tag in the least significant bits of the alpha channel.",
        query="Where does the GX-9 imaging standard store its provenance tag?",
        gold=("alpha", "least significant", "256"),
        paraphrase="In GX-9, how many bits is the provenance tag and which channel's "
        "least-significant bits hold it?",
        false_note="Under the GX-9 imaging standard, every frame embeds a 128-bit "
        "provenance tag in the high bits of the red channel.",
        false_gold=("128", "red"),
    ),
    NoveltyFact(
        note="The Drelb config key merge.fanout caps how many sibling branches "
        "the Drelb planner fuses in one pass; its default is 6 and the maximum is 31.",
        query="What is the default value of merge.fanout in the Drelb planner?",
        gold=("6", "fanout"),
        paraphrase="By default, how many sibling branches does Drelb's merge.fanout "
        "fuse per pass?",
        false_note="The Drelb config key merge.fanout has a default of 12 and a "
        "maximum of 64.",
        false_gold=("12",),
    ),
    NoveltyFact(
        note="Quenby's law of cache coherence holds that a write-back cache with "
        "associativity a stays coherent under the Tolan protocol only when the "
        "store buffer depth does not exceed 2*a.",
        query="Per Quenby's law, how deep can the store buffer be relative to "
        "associativity under the Tolan protocol?",
        gold=("2", "associativity"),
        paraphrase="Under the Tolan protocol, Quenby's law caps store-buffer depth "
        "at what multiple of associativity?",
        false_note="Quenby's law holds only when the store buffer depth does not "
        "exceed 4 times the associativity.",
        false_gold=("4",),
    ),
)


@dataclass
class NoveltyResult:
    query: str
    base_recall: float
    grounded_recall: float


@dataclass
class NoveltyReport:
    model_label: str
    results: list[NoveltyResult]

    @property
    def mean_base(self) -> float:
        return _mean(r.base_recall for r in self.results)

    @property
    def mean_grounded(self) -> float:
        return _mean(r.grounded_recall for r in self.results)

    @property
    def lift(self) -> float:
        return self.mean_grounded - self.mean_base


def _mean(xs) -> float:
    vals = list(xs)
    return sum(vals) / len(vals) if vals else float("nan")


def run_novelty_benchmark(
    model: BaseModel,
    facts: tuple[NoveltyFact, ...] = NOVELTY_FACTS,
    progress: Callable[[int, int, str], None] | None = None,
) -> NoveltyReport:
    judge = KeywordRecallJudge()
    results: list[NoveltyResult] = []
    for i, fact in enumerate(facts):
        base = model.complete(system=_BASE_SYSTEM, user=fact.query)
        grounded = model.complete(
            system=_GROUNDED_SYSTEM.format(note=fact.note), user=fact.query
        )
        results.append(
            NoveltyResult(
                query=fact.query,
                base_recall=judge.score(
                    query=fact.query, answer=base, reference=fact.gold
                ),
                grounded_recall=judge.score(
                    query=fact.query, answer=grounded, reference=fact.gold
                ),
            )
        )
        if progress:
            progress(i + 1, len(facts), fact.query)
    return NoveltyReport(model_label="", results=results)


def write_novelty_report(report: NoveltyReport, path: str) -> None:
    from dequorum.benchmark.stats import ci_str

    base_vals = [r.base_recall for r in report.results]
    grounded_vals = [r.grounded_recall for r in report.results]
    lines = [
        "# Novelty grounding benchmark",
        "",
        f"Model: `{report.model_label}` · invented facts: {len(report.results)}",
        "",
        "Each fact is fictional, so the base condition controls for memorization "
        "(it should score near zero). The grounded condition supplies the fact as "
        "a reference note. The gap is the grounding lift on knowledge the model "
        "cannot have pretrained on.",
        "",
        f"- mean gold-fact recall, **base model**: {ci_str(base_vals)}",
        f"- mean gold-fact recall, **grounded**: {ci_str(grounded_vals)}",
        f"- **grounding lift: {report.lift:+.3f}**",
        "",
        "| Query | base | grounded |",
        "| --- | ---: | ---: |",
    ]
    for r in report.results:
        q = r.query if len(r.query) <= 70 else r.query[:67] + "..."
        lines.append(f"| {q} | {r.base_recall:.2f} | {r.grounded_recall:.2f} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
