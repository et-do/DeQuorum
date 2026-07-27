# Methodology: the reliance-grounded credit experiment (§8.6)

This documents, transparently and reproducibly, how DeQuorum's central economic
claim is tested — so the result can be scrutinised, replicated, and its limits
understood. It is the methods companion to [WHITEPAPER.md](../WHITEPAPER.md) §8.6 and
the direction in [paper-direction.md](paper-direction.md).

## The claim under test

Crediting a contribution by the **causal quality drop** when it is ablated
(regenerate the answer without it, then judge the resulting answer) is a fairer basis
for paying contributors than the **resemblance** or **informativeness/coverage**
objectives used by prior attribution-payment work — because only the causal-quality
objective distinguishes a true contribution from its near-identical *false twin*, the
regime where payment fairness bites.

## Design: isolate the objective, hold the machinery fixed

All marginal methods use one identical leave-one-out (LOO) procedure — generate the
full answer, remove one contribution, regenerate, and take a per-contribution score —
so the **only** variable across methods is the *objective* the ablation is scored
against:

| method | objective | grounded in |
| --- | --- | --- |
| resemblance | embedding similarity of the answer to the removed note | resemblance |
| coverage | reference-free topical informativeness of the answer | informativeness (Ye & Yoganarasimhan 2025) |
| reliance | recall of the true gold fact in the answer | causal quality (ours) |

Holding the machinery fixed is what lets us attribute any performance gap to the
objective rather than to the estimator — the standard ablation-study logic. `flat`
(equal credit) and `retrieval score` are non-marginal baselines.

## Corpus: synthetic facts with known ground truth

Real corpora do not label *which* contribution is decisive for an answer, so faithful
attribution cannot be scored directly on them (this is exactly why the field measures
attribution indirectly, e.g. citation entailment in ALCE, Gao et al. 2023). We
therefore use **invented facts**: each query has exactly one contribution containing
its gold answer (the decisive one), so ground truth is known by construction.

We evaluate two contested regimes, which behave differently and must not be conflated:

- **Adversarial / near-duplicate regime** (`--corpus synthetic --distractors hard`).
  The competitor is the decisive fact's *false twin* — identical template, only the
  value flipped — which the model adopts ~80% of the time (§8.8). Because the true note
  and its twin are lexically near-identical, resemblance and coverage cannot separate
  them; this is also exactly the duplication/paraphrase **gaming** attack. Invented
  facts (base recall ≈ 0) so the model cannot answer from parametric knowledge.
- **Natural / misconception regime** (`--corpus real --distractors hard`). The
  competitor is a *real, documented common misconception* paired with a real fact
  (25 curated facts, e.g. tallest-mountain-base-to-peak, largest-desert,
  average-closest-planet). Here the true and false content differ by a semantically
  distinct real word, so resemblance *can* separate them — an important contrast.
- **Separable regime** (`--distractors random`). Unrelated distractors; every method
  scores 1.0. A sanity check, not a test.

Synthetic data buys exact ground truth at the cost of external validity; the real
corpus restores realism at small scale (n=25). Reporting **both** is what surfaces the
regime-dependence of resemblance (see below).

## Graders: a deterministic control and an LLM robustness check

The reliance and coverage objectives each need a grader. We run two families and
report both, because a result that holds only under one grader is a grader artifact:

- **Keyword (deterministic, model-independent):** `KeywordRecallJudge` (gold recall)
  for reliance; `CoverageJudge` (query-term coverage) for coverage. These are the
  **unbiased control** — reproducible with no model, immune to LLM-judge pathologies.
- **LLM-as-judge:** `LLMJudge` (0–10 correctness vs gold) for reliance;
  `LLMCoverageJudge` (0–10 topical completeness, correctness explicitly ignored) for
  coverage. Less brittle than keyword matching, but **biased**: when the judge model
  is the generator it may prefer its own outputs (self-preference; Zheng et al. 2023,
  *Judging LLM-as-a-Judge with MT-Bench*). We flag this in the report and treat the
  keyword grader as the control. `--judge {keyword,llm}`.

## Metrics and statistics

- **rank-1 accuracy** — fraction of queries where the decisive contribution receives
  the most credit. Tie-aware: a k-way tie counts as 1/k, so `flat` scores true chance
  (1/m), not a spurious argmax win.
- **precision** — mean share of total credit placed on the decisive contribution.
- **95% CI** — Wilson score interval (`benchmark/stats.py`), which is well-behaved at
  the 0/1 boundary where normal-approximation intervals fail. Non-overlapping
  intervals are our bar for "distinct."

## Robustness to grader choice (result)

The objective gap must not depend on the grader. We ran the contested regime under
three graders — the deterministic keyword control, a self-LLM judge (judge = the
qwen-7B generator), and an **independent** LLM judge (llama3.2:3b, a different family,
so self-preference is structurally impossible). rank-1 accuracy:

| objective | keyword (n=50, control) | self-LLM qwen-7B (n=20) | independent llama3.2:3b (n=50) |
| --- | ---: | ---: | ---: |
| resemblance | 0.50 | 0.40 | 0.50 |
| coverage (informativeness) | **0.31** | **0.31** | **0.30** |
| **reliance (ours)** | **0.82 [0.69, 0.90]** | 0.70 [0.48, 0.85] | 0.53 [0.39, 0.66] |

Reports: [keyword](../benchmarks/attribution_truth_hard.md),
[self-LLM](../benchmarks/attribution_truth_hard_llm.md),
[independent](../benchmarks/attribution_truth_hard_indep.md).

**Two findings, stated honestly — one robust, one a real limitation.**

1. **Coverage fails under every grader (robust).** The informativeness/coverage
   objective — the nearest prior art's — sits at the 0.25 chance floor (0.31, 0.31,
   0.30) regardless of who grades. A fluent false twin covers the query as well as the
   truth, so no grader rescues the wrong objective. This is the load-bearing result and
   it does not depend on grader choice.
2. **Reliance is bounded by judge accuracy (limitation).** Reliance is the top method
   in every run, but its *margin* over the resemblance baseline tracks how good the
   quality judge is: clean separation with the precise keyword grader (0.82,
   non-overlapping), eroded to near-chance with the weak independent 3B judge (0.53,
   overlapping resemblance). This is **not** a parsing artifact — a direct probe shows
   llama3.2:3b emits clean integers but is a poor correctness grader, scoring a
   factually *wrong* answer 0.6 (vs 0.8 for the correct one), only 0.2 of
   discrimination. A weak quality signal yields a weak reliance marginal. This is
   exactly the judge-sensitivity §8.6 already reports, now quantified across graders.

**What we therefore claim.** The keyword grader is an *accurate, model-independent*
oracle for these exact-gold synthetic facts, so it is the primary evidence for
separation (0.82). The LLM runs (a) confirm the coverage objective fails independently
of grader, and (b) show reliance needs an accurate quality signal — a strong judge or,
in production, user feedback — which a small 3B judge does not provide. A **strong**
independent judge (a capable, non-generator model) would sharpen (b) and is open work;
it was not run here because only small models were available on local CPU. We do not
claim the independent LLM run confirms separation — it does not, and we report it
plainly.

## Cross-generator external validity (result)

To test the "single model family" limitation, we re-ran the contested regime with a
**different generator** — llama3.2:3b instead of qwen-7B — under the accurate keyword
grader ([report](../benchmarks/attribution_truth_hard_llama_gen.md)):

| objective | qwen-7B generator (n=50) | llama3.2:3b generator (n=50) |
| --- | ---: | ---: |
| resemblance | 0.50 | 0.47 |
| coverage (informativeness) | 0.31 | 0.27 |
| **reliance (ours)** | **0.82 [0.69, 0.90]** | **0.74 [0.60, 0.84]** |

The ordering and the separation hold on the second generator: reliance (0.74) is
non-overlapping with coverage (0.27) and clears resemblance. The effect is not
qwen-specific — evidence that it is a property of the *objective*, not of one model.

## Natural regime: real misconceptions (result — and a retraction)

Re-running the contested regime on the **real** corpus (qwen-7B, keyword grader, n=25,
[report](../benchmarks/attribution_truth_real.md)) changed one conclusion, and we report
it straight:

| objective | adversarial / near-duplicate (n=50) | natural / misconception (n=25) |
| --- | ---: | ---: |
| resemblance | 0.50 | **0.90 [0.72, 0.97]** |
| coverage (informativeness) | 0.31 | 0.27 [0.14, 0.47] |
| **reliance (ours)** | **0.82** | 0.79 [0.59, 0.90] |

**Resemblance recovers to 0.90 on real facts** — so the strong claim "resemblance fails
in the contested regime" holds only for the *near-duplicate* regime and is **retracted
for the natural regime**. The cause is mechanical: near-duplicate twins differ by an
invented token embeddings treat as noise, while real misconceptions differ by a
semantically distinct word ("Mauna Kea" vs. "Everest") that embeddings capture. This
reframes the near-duplicate case as a **gaming** test (the duplication attack), which
resemblance fails and reliance passes.

## What survives, across two regimes

- **Coverage/informativeness fails in *both* regimes** (0.27–0.31) and across all graders
  and generators. Since this is the objective the nearest payment prior art uses, this is
  the robust, load-bearing result.
- **Resemblance is regime-dependent**: safe on natural misconceptions (0.90), gameable by
  near-duplicates (0.50).
- **Reliance is the only objective robust across *both* regimes** (0.82 / 0.79 with an
  accurate signal), degrading only under a weak judge (0.53). On the natural corpus it is
  *not* uniquely best (resemblance edges it), so the positive case for reliance rests on
  cross-regime robustness, not single-regime dominance — stated, not spun.

## Reproducibility

Deterministic given the seed and a temperature-0 model (both Ollama and the
OpenAI-compatible provider set `temperature=0`), so the two objective passes score
*identical* ablated answers — the objective is the only difference.

```
# keyword grader (control), full run
dequorum attribution-truth --model qwen2.5-coder:7b --host http://ollama:11434 \
    --distractors hard --corpus synthetic --output docs/benchmarks/attribution_truth_hard.md

# LLM grader (robustness), smaller n
dequorum attribution-truth --model qwen2.5-coder:7b --host http://ollama:11434 \
    --distractors hard --judge llm --limit 20 --corpus synthetic \
    --output docs/benchmarks/attribution_truth_hard_llm.md
```

Seed defaults to 0. Code: `cli.py::_cmd_attribution_truth`,
`attribution/marginal.py::measure_attribution`, `eval/judge.py`.

## Threats to validity / limitations (stated, not hidden)

1. **Synthetic corpus.** Exact ground truth costs external validity. The result is a
   *mechanism* demonstration; confirming it on a real multi-domain corpus (where
   ground truth must be human-annotated) is open work.
2. **Single model family.** One generator (Qwen 2.5 Coder, 3B/7B). The objective
   contrast is model-agnostic in principle but unverified across families.
3. **Judge as ground-truth proxy.** The keyword judge is coarse (exact-token recall);
   the LLM judge is less brittle but self-preference-biased. We mitigate by reporting
   both; neither is a substitute for human judgement at scale.
4. **Scale.** n=50 (keyword), n=20 (LLM) synthetic facts. Wilson intervals report the
   resulting uncertainty; larger n and a stronger independent judge are open.
5. **Incentive-compatibility (payment, not attribution).** A faithful *attribution*
   score is not automatically a truthful *payment*: leave-one-out and Shapley
   valuations are known to violate incentive-compatibility as prices (Han et al. 2025,
   *Do Data Valuations Make Good Data Prices?*). DeQuorum's conserved-revenue split
   inherits this; making payouts strategy-proof (Myerson/VCG-style rules over reliance
   credit) is scoped as future work, not claimed here. See
   [incentive-compatibility.md](incentive-compatibility.md).

## Methodological lineage (what we borrow)

- **Ablation / leave-one-out attribution** — the LOO estimator and its redundancy
  blind spot (addressed with Shapley) follow the data-valuation line (Data Shapley,
  Ghorbani & Zou 2019).
- **Attribution evaluation** — the correctness-vs-faithfulness distinction and the
  entailment paradigm come from RAG citation work (ALCE, Gao et al. 2023; *Correctness
  is not Faithfulness*, Wallat et al. 2024); we diverge by scoring *causal quality*.
- **True ablation over introspection** — we regenerate rather than ask a judge whether
  a source was used, because introspective removal is unfaithful to real ablation
  (*Agents that Matter*, 2026).
- **LLM-as-judge caveats** — Zheng et al. 2023.

Full citations in memory `key-prior-art-citations`.
