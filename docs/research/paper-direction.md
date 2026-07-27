# Research direction: the paper and the protocol

This pins what we are building and why, so every downstream decision can be checked
against it. It is grounded in the 2026-07 literature review (see the two memory
notes) and the existing [WHITEPAPER.md](../WHITEPAPER.md) §8.6 result.

## The end goal — two deliverables, cleanly separated

1. **Open-source protocol (the headline).** A provider-agnostic standard + reference
   implementation (this repo) that any LLM operator straps on to accept user
   contributions, attribute which contributions grounded each answer, and pay the
   contributors whose knowledge surfaced. Goal: **adoption**. It rides the provider's
   users and compute — which is exactly how we get around having neither.
2. **Research paper (the credibility).** One narrow, defensible scientific claim (below).
   Goal: **legitimacy + differentiation**. The platform is its *evaluation harness* —
   so we can prove the measure without needing scale.

The paper makes the protocol credible; the protocol is where the paper's mechanism
lives. Do not conflate them: reviewers reward the narrow claim, adopters reward the
system.

## The one claim to lead with

> **Reliance-grounded credit** — crediting a contribution by the *causal* quality drop
> when it is ablated (regenerate the answer without it, then judge the resulting
> answer's quality) is a fairer basis for paying contributors than the
> resemblance / entailment / informativeness objectives used by all prior
> attribution-payment work. Only the causal-quality objective distinguishes a true
> contribution from its near-identical false twin — the regime where payment fairness
> actually bites.

**Evidence we have** (WHITEPAPER §8.6, contested regime, n=50, Qwen 2.5 Coder 7B):
same leave-one-out machinery, three objectives — resemblance **0.50**, coverage /
informativeness (the Ye & Yoganarasimhan objective) **0.31** (≈ the 0.25 chance
floor), reliance / causal-quality (ours) **0.82** [0.69, 0.90], non-overlapping. It
is the *objective*, not the machinery, that recovers the decisive contribution. A
robustness run swaps the deterministic keyword grader for an LLM-as-judge (`--judge
llm`) to show the gap is not a grader artifact. Full method + limitations in
[methodology.md](methodology.md); that table is the spine of the paper.

## What we build on / differentiate from

We are not inventing from scratch — we extend a specific, recent line and beat it on
one axis. (Full citations: memory `key-prior-art-citations`.)

| Prior work | What it does | How we differ |
| --- | --- | --- |
| **Ye & Yoganarasimhan 2025** (arXiv 2505.23842) — *nearest neighbor* | Shapley RAG document attribution + per-query & subscription payout formulas for creator comp. Reference-free GPT-4o judge. | Their value function scores **informativeness/coverage**; ours scores **causal reliance** (true-ablation quality). We must show the objective changes *who gets paid*. |
| **"Correctness ≠ Faithfulness in RAG"** (2412.18004) | Defines correctness vs. faithfulness (causal reliance); coins "post-rationalization". | We **cite** this for terminology; we operationalize causal reliance into *economic credit*. |
| **"Agents that Matter"** (2605.27621) | Introspective LLM-judge *removal* ≠ true ablation (R²=0.42). | We **already do true regeneration** + judge only scores the output. This preempts the strongest objection. |
| **AME** (2606.16075) | Claims "first unified attribution+rights+revenue framework." | We do **not** claim "first unified" anything. Our claim is the *mechanism*, not the integration. |
| **LoGra, Fairshare, Vana** | Training-time contributor valuation/compensation. | We are **inference-time**: patch onto an existing model, attribute per answer, pay per surfaced use. |
| **OpenAttribution, RSL** | Provider-agnostic attribution / licensing standards. | Both **exclude payment**. We close contribution → per-answer attribution → payment. |

## Risks to pre-empt (state them in the paper)

1. **Incentive-compatibility — but state it precisely.** The Han et al. 2025 result
   ("Do Data Valuations Make Good Data Prices?", 2504.05563) that LOO/Shapley are not
   truthful *prices* targets **report-based** markets; DeQuorum elicits no cost/value
   reports (it measures value ex post), so that critique does not transfer as stated.
   What we *do* claim is **manipulation-resistance** (duplication/padding/collusion,
   §8.6); report-based strategy-proofness is out of scope for the current mechanism
   and is the sharpest open EC problem. Full analysis:
   [incentive-compatibility.md](incentive-compatibility.md). Do not overclaim in
   either direction.
2. **The margin is one axis.** Novelty rests on causal-quality vs. informativeness
   objective — now backed by the head-to-head (0.82 vs 0.31), with an LLM-judge
   robustness run to show it is not a keyword-grader artifact.

## Naming

Rename the measure from "faithful credit" to **reliance-grounded credit** (or "causal
marginal credit") throughout code + whitepaper. "Faithful" is now a loaded RAG term
(2412.18004); using it reads as re-coining their word. Cite them, use our own name.

## Concrete next steps (paper-defensibility order)

1. **Head-to-head objective experiment** — ✅ **done** (the load-bearing result). In
   the contested regime ($n=50$, Qwen 2.5 Coder 7B), the *same* leave-one-out
   machinery scored under three objectives: resemblance **0.50**, coverage /
   informativeness (the Ye & Yoganarasimhan objective) **0.31** (≈ the 0.25 chance
   floor), reliance / causal-quality (ours) **0.82** [0.69, 0.90], non-overlapping.
   It is the *objective*, not the machinery, that recovers the decisive contribution
   — the direct rebuttal to "you reinvented Ye & Yoganarasimhan." Harness:
   `CoverageJudge` + `dequorum attribution-truth --distractors hard`; folded into
   WHITEPAPER §8.6. Next: confirm beyond synthetic facts + a stronger (LLM) judge.
2. **Naming + citations pass** — ✅ **done**. Renamed faithful→reliance-grounded
   across code + whitepaper; prior-art map + "true-ablation, not introspection"
   defense folded into WHITEPAPER §8.6.
3. **Rigor pass** — ✅ **done** (4 conditions, 2 generators × 3 graders, free Ollama).
   Coverage (the competitor's objective) fails at chance in *every* condition
   (0.27–0.31) — robust across grader and generator. Reliance separates cleanly with
   an accurate grader across two generator families (keyword: qwen 0.82, llama 0.74)
   but is **judge-accuracy-bounded** (weak independent 3B judge → 0.53, diagnosed as a
   weak-signal effect, reported straight). Added `--judge-model` (independent judge).
   Written up transparently: [methodology.md](methodology.md) (4-condition tables,
   cited) + [incentive-compatibility.md](incentive-compatibility.md). **Open:** a
   *strong* independent judge to sharpen reliance-under-independent-grader; a
   real (non-synthetic) multi-domain corpus.
4. **Truthfulness (theory)** — the open EC problem: a strategy-proof, budget-balanced
   payment whose allocation is reliance credit (Myerson/VCG vs Green–Laffont). Scoped,
   not solved — see incentive-compatibility.md.
5. **Protocol positioning** — a short "related standards" section placing us next to
   OpenAttribution/RSL as the attribution+payment layer.

## Venue

Lead claim (reliance-grounded credit + the contested-regime eval) targets an **ML
attribution/eval workshop, NeurIPS Datasets & Benchmarks, or FAccT** (the
compensation-fairness angle fits FAccT well). **EC** only if step 3 actually solves
truthfulness. The protocol itself is a systems/standards artifact, not the research
contribution.
