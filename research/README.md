# research/

Literature reviews and experiment specs. Each note is a snapshot of what the published frontier looked like on a specific date; each experiment is a falsifiable spec for one self-contained piece of work.

## Notes (literature sweeps)

| # | Topic | Date |
| - | ----- | ---- |
| 01 | [VSA / HDC frontier](notes/01-vsa-hdc-frontier.md) | 2026-05-26 |
| 02 | [Categorical AI frontier](notes/02-categorical-ai-frontier.md) | 2026-05-26 |
| 03 | [KG provenance frontier](notes/03-kg-provenance-frontier.md) | 2026-05-26 |
| 04 | [Per-query attribution math frontier](notes/04-attribution-math-frontier.md) | 2026-05-26 |

Cross-cutting finding: **per-query attribution as a formal mathematical object is unclaimed territory** — all four sweeps independently flagged it as the cleanest gap.

## Experiments

| # | Spec | Status |
| - | ---- | ------ |
| 01 | HDC bundle attribution functional | **shelved** — see [archive/](../archive/) |

Experiment 1 surfaced that the proposed pivotal-decomposition formula was mathematically identical to leave-one-out attribution. The work is preserved in [archive/](../archive/) because the question (per-source attribution math) remains the central research problem for the project — it just needs a different architectural substrate. The HDC-specific code does not transfer to LLM/MoE/LoRA attribution, which is the new target.

Process for future experiments: a spec must list its **claim**, **axioms**, **falsification criteria**, and **baselines** *before* any code is written. Results that survive falsification go into a write-up; results that don't get documented as what failed and why.
