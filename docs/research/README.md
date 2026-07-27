# research/

Literature reviews and experiment specs. Each note is a snapshot of what the published frontier looked like on a specific date; each experiment is a falsifiable spec for one self-contained piece of work.

## Paper & methods

| Doc | What |
| --- | --- |
| [paper/reliance-grounded-credit.md](../paper/reliance-grounded-credit.md) | **The draft paper** — "Which objective pays the right contributor?" (workshop/preprint), leading with the robust negative result |
| [paper-direction.md](paper-direction.md) | The pinned direction: the one claim (reliance-grounded credit), what we build on/differ from, risks, venue |
| [methodology.md](methodology.md) | How §8.6 is tested — design, corpus, graders, statistics, reproducibility, limitations (transparent by intent) |
| [incentive-compatibility.md](incentive-compatibility.md) | What reliance-grounded payment does/does not guarantee — manipulation-resistance vs. report-based strategy-proofness |
| [contested-facts-datasheet.md](contested-facts-datasheet.md) | Datasheet for the natural-regime corpus (real facts + documented misconceptions) — composition, provenance, limitations |

## Notes (literature sweeps)

| # | Topic | Date |
| - | ----- | ---- |
| 01 | [VSA / HDC frontier](notes/01-vsa-hdc-frontier.md) | 2026-05-26 |
| 02 | [Categorical AI frontier](notes/02-categorical-ai-frontier.md) | 2026-05-26 |
| 03 | [KG provenance frontier](notes/03-kg-provenance-frontier.md) | 2026-05-26 |
| 04 | [Per-query attribution math frontier](notes/04-attribution-math-frontier.md) | 2026-05-26 |
| 05 | [Product, incentive & architecture direction](notes/05-product-and-incentive-frontier.md) | 2026-06-10 |

Cross-cutting finding from the literature sweeps (01–04): **per-query attribution as a formal mathematical object is unclaimed territory** — all four independently flagged it as the cleanest gap. Note 05 is different in kind: a direction/decision record that turns our own benchmark results into product and architecture decisions, and identifies **attribution-by-construction** (per-contributor adapter routing) as the core bet that is both the product fix and the novelty.

## Experiments

| # | Spec | Status |
| - | ---- | ------ |
| 01 | HDC bundle attribution functional | **shelved** — see [archive/](../archive/) |
| 02 | Serving read path: retrieval-grounded lift with distractors (`retrieval-bench`) | **runnable** (GPU notebook) |
| 03 | Conflicting contributions: true vs false both retrieved (`conflict-bench`) | **runnable** (GPU notebook) |
| 04 | Governance sybil resistance: flat vs reputation voting (`governance-sim`) | **runnable** (no GPU) |
| 05 | Quantization robustness of grounding (`quant-bench`) | **runnable** (GPU notebook) |
| 06 | Attribution-by-construction: per-contributor adapter routing (`attribution-route`) | **runnable** (GPU notebook) |

Experiment 1 surfaced that the proposed pivotal-decomposition formula was mathematically identical to leave-one-out attribution. The work is preserved in [archive/](../archive/) because the question (per-source attribution math) remains the central research problem for the project — it just needs a different architectural substrate. The HDC-specific code does not transfer to LLM/MoE/LoRA attribution, which is the new target.

Process for future experiments: a spec must list its **claim**, **axioms**, **falsification criteria**, and **baselines** *before* any code is written. Results that survive falsification go into a write-up; results that don't get documented as what failed and why.
