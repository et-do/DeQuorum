# Which Objective Pays the Right Contributor? A Two-Regime Head-to-Head for Attribution-Based Payment in Retrieval-Augmented Generation

**Draft — workshop / preprint.** Status and open items at the bottom. Numbers are from
the DeQuorum reference implementation; see [methodology.md](../research/methodology.md)
for the full protocol and [../benchmarks/](../benchmarks/) for raw reports.

---

## Abstract

Retrieval-augmented generation (RAG) makes it possible, in principle, to pay the people
whose contributed knowledge surfaces in a generated answer, and a growing line of work
proposes exactly this — marginal-value attribution over retrieved documents, with
per-query or subscription payouts to contributors. Every such proposal must choose an
**objective** for "how much did this contribution matter," and that choice has gone
largely unexamined. We show it matters, and that the safe choice is not obvious. Using
one leave-one-out estimator, we compare three objectives — **resemblance** (embedding
similarity, as in retrieval-score attribution), **informativeness/coverage** (a
reference-free judge, the objective of the nearest payout work), and **reliance** (the
causal drop in answer *correctness* when a contribution is ablated) — in two contested
regimes, where a query's decisive true contribution is paired with a competitor
asserting the opposite. In the **adversarial** regime the competitor is a near-duplicate
false twin (a duplication/gaming attack); in the **natural** regime it is a real,
documented misconception. Two findings, reported straight. (1) The
informativeness/coverage objective — the one the nearest payment prior art uses — fails
in **both** regimes, crediting the decisive contribution at chance (0.27–0.31) across
two generator families and three graders. (2) Resemblance is **regime-dependent**: it is
defeated by the near-duplicate attack (0.50, chance) but succeeds on natural
misconceptions (0.90), because real distinguishing content is semantically separable.
Only the **reliance** objective is robust across *both* regimes (0.79–0.82 with an
accurate signal), and — a limitation we also show — only when the quality signal grading
it is accurate; a weak judge erodes it to chance. The practical message: in
attribution-based payment, no single default objective is safe, the informativeness
objective is unsafe everywhere, and a causal-reliance objective is the only one that
survives both a gaming attack and the messiness of real contested facts.

## 1. Introduction

The economics of large language models increasingly turn on a question of credit: when a
model's answer is shaped by content some person contributed, can that person be
identified and paid? Retrieval-augmented generation makes the mechanics plausible — the
retrieved set is a concrete, per-answer list of contributions — and several recent
systems build payment on top of it, distributing revenue in proportion to a
marginal-value attribution score [YeYoganarasimhan2025; AME2026]. Parallel efforts in
data valuation [DataShapley; LoGra; Fairshare] pursue the same goal at training time.

Any such system must answer a prior question these works largely take as settled: **what
should credit be a function of?** A contribution can be scored by how much the answer
*resembles* it, by how much *information* it contributes, or by how much the answer's
*quality* causally depends on it. These objectives coincide when contributions are
unrelated; they come apart when a query has a decisive true fact and a plausible
competitor asserting the opposite. That contested case is not a corner case — conflicting
claims, versioned facts, and misinformation are pervasive — and it comes in two flavours
that turn out to behave very differently:

- **Adversarial:** the competitor is a near-duplicate of the true contribution (a
  duplication or paraphrase attack, the classic way to game marginal credit).
- **Natural:** the competitor is a genuinely different, real misconception.

We isolate the objective and measure it in both. Holding the estimator (leave-one-out
ablation) fixed and varying only the objective, we ask a question with a known answer:
does the method place the most credit on the contribution that actually contains the
truth? Our findings:

- **The informativeness objective is unsafe everywhere.** Coverage/informativeness — the
  objective of the nearest payout proposal — credits the decisive contribution at chance
  in both regimes, across two generator families and three graders.
- **Resemblance is regime-dependent.** It is defeated by the near-duplicate attack but
  works on natural misconceptions. So it is not a general failure, but it is gameable.
- **Only reliance is robust across both regimes.** The causal-quality objective survives
  the gaming attack *and* the natural regime — but only with an accurate quality signal;
  a weak judge collapses it.

No single default objective is safe; the field's informativeness default is unsafe
everywhere; and causal reliance is the one objective that holds across both regimes,
conditional on signal quality. That is a cautionary, actionable result for a field
already shipping payment on top of attribution.

## 2. Related work

**Attribution-based contributor payment.** The closest work is Ye & Yoganarasimhan
[YeYoganarasimhan2025], which computes per-document Shapley value over a RAG summary with
explicit per-query and subscription payouts to creators; its value function is a
reference-free judge scoring information *coverage*. AME [AME2026] proposes a unified
attribution-plus-revenue framework for generative-AI markets. We do not propose a new
payment framework; we isolate and evaluate the **objective** these systems credit
against, and show the coverage/informativeness objective fails in both contested regimes.

**Data valuation and pricing.** Data Shapley [DataShapley], scalable influence functions
[LoGra], and seller-compensation mechanisms [Fairshare] value data at *training* time; we
operate at inference time on the retrieved set. Han et al. [HanPrices2025] show valuation
scores are not incentive-compatible *prices* in report-based markets (§7).

**Citation and attribution faithfulness.** RAG citation work distinguishes citation
*correctness* from *faithfulness* [WallatFaithfulness2024] and evaluates citations by
entailment against the retrieved set [ALCE]. We adopt the faithfulness distinction but
score *causal quality* rather than entailment, tie it to economic credit, and — heeding
that introspective "did the model use this" judgments are unfaithful to true ablation
[AgentsThatMatter2026] — ablate and regenerate rather than introspect.

**Standards and markets.** Content-attribution/licensing standards (OpenAttribution, RSL)
exclude payment; data DAOs (Vana) pay at training/asset granularity, not per-answer
grounding. The contribution → per-answer attribution → payment loop is unoccupied as an
open standard.

## 3. Setup

A query $q$ is answered by grounding a model on a retrieved set
$S = \{d_1,\dots,d_m\}$; a payment mechanism splits the query's revenue across authors
by a credit vector $c \in \Delta^m$ over $S$, derived from a per-contribution value
$v_i$ that an **objective** assigns. Each objective is computed by the same
**leave-one-out (LOO)** estimator: generate $a = M(q,S)$, and for each $d_i$ regenerate
$a_{-i} = M(q, S\setminus\{d_i\})$; normalise the non-negative marginals to get $c$.

- **Resemblance:** $v_i = \max(0, \text{sim}(a,d_i) - \text{sim}(a_{-i},d_i))$ (embedding
  cosine) — the objective implicit in retrieval-score attribution.
- **Coverage (informativeness):** $v_i = g(a) - g(a_{-i})$, $g$ a reference-free judge of
  how completely $a$ covers the query, ignoring correctness — the nearest payout work's
  objective [YeYoganarasimhan2025].
- **Reliance (ours):** $v_i = h(a) - h(a_{-i})$, $h$ scoring answer *correctness* against
  ground truth.

Only $\text{sim}, g, h$ differ; the estimator and regenerations are shared, so any gap is
attributable to the objective.

## 4. Experimental design

**Two contested regimes.** Both need the ground-truth decisive contribution, which real
corpora do not label, so each query has exactly one contribution containing its gold
answer plus a competitor asserting the opposite. In the **adversarial** regime the
competitor is a *near-duplicate false twin* — identical template, only the value flipped
(a synthetic corpus of invented facts, so the model cannot answer from parametric
knowledge; $n=50$). In the **natural** regime the competitor is a *real, documented
misconception* paired with a real fact (a curated corpus of ~44 real facts across
geography, physics, biology, language, and everyday reasoning — e.g. tallest mountain
base-to-peak = Mauna Kea, largest desert = Antarctica, camel humps store fat; see the
[datasheet](../research/contested-facts-datasheet.md)). An automated test asserts every
true/misconception pair is separable by the grader, guarding against curation errors.

**Metric.** rank-1 accuracy (tie-aware; equal credit scores chance $1/m$), with 95%
Wilson intervals; $m=4$, chance $0.25$.

**Graders.** A deterministic model-independent control (keyword gold-recall for reliance;
query-term coverage for coverage) and an LLM-as-judge (0–10 correctness vs. reference;
0–10 topical completeness, correctness ignored), run self-judged and with an
**independent** judge of a different family [MTBench2023].

**Models.** Generators qwen-2.5-coder 7B and llama-3.2 3B (a second family); independent
judge llama-3.2 3B; temperature 0; fixed seed. Full protocol and commands in
[methodology.md](../research/methodology.md).

## 5. Results

**The two regimes behave differently, and that is the point (Table 1).** Under the
accurate keyword grader with the qwen-7B generator: in the adversarial (near-duplicate)
regime, resemblance is a coin flip (0.50) and only reliance separates (0.82); in the
natural (misconception) regime, resemblance recovers sharply (0.90) and reliance stays
strong (0.79). Coverage fails in **both** (0.31, 0.27).

*Table 1. rank-1 accuracy (95% CI), qwen-7B, keyword grader.*

| objective | adversarial / near-duplicate (n=50) | natural / misconception (n=25) |
| --- | ---: | ---: |
| flat (equal credit) | 0.25 [0.15, 0.38] | 0.25 [0.12, 0.44] |
| retrieval score | 0.50 [0.37, 0.63] | 0.48 [0.30, 0.67] |
| resemblance | 0.50 [0.37, 0.63] | **0.90 [0.72, 0.97]** |
| coverage (informativeness) | 0.31 [0.20, 0.45] | 0.27 [0.14, 0.47] |
| **reliance (ours)** | **0.82 [0.69, 0.90]** | 0.79 [0.59, 0.90] |

Resemblance's swing is mechanical: near-duplicate twins differ only by a token embeddings
treat as noise, so the answer resembles both equally; real misconceptions differ by a
semantically distinct word ("Mauna Kea" vs. "Everest"), which embeddings capture. This is
why the near-duplicate case doubles as a **gaming** test — it is exactly the
duplication/paraphrase attack a contributor would mount — and resemblance is the objective
that attack defeats.

**Coverage's failure is robust across graders and generators (Table 2).** In the
adversarial regime, coverage stays at the chance floor under a second generator family
and an independent judge (0.27–0.31 everywhere); resemblance never exceeds 0.50; reliance
is top whenever the signal is accurate but degrades under a weak judge (details below).

*Table 2. Adversarial-regime rank-1 across conditions. Bold = accurate-grader.*

| objective | kw / qwen-7B | kw / llama-3B | self-LLM 7B | indep. 3B |
| --- | ---: | ---: | ---: | ---: |
| resemblance | 0.50 | 0.47 | 0.40 | 0.50 |
| coverage | 0.31 | 0.27 | 0.31 | 0.30 |
| **reliance** | **0.82** | **0.74** | 0.70 | 0.53 |

**Reliance is bounded by signal quality.** It separates cleanly under the accurate
keyword oracle on both generators (0.82, 0.74) but falls to 0.53 under a weak independent
3B judge — not a parsing artifact: that judge emits clean integers but scores a factually
*wrong* answer 0.6 vs. 0.8 for the correct one (0.2 of discrimination). A weak quality
signal yields a weak reliance marginal.

**Summary of who survives what.** Coverage: fails both regimes. Resemblance: passes
natural, fails adversarial (gameable). Reliance: passes both, given an accurate signal.

## 6. Discussion

**No default objective is safe; the choice must be made deliberately.** The three methods
share one estimator and diverge only in what they optimise. Coverage is truth-agnostic —
a fluent false answer covers the query as well as a true one — so it cannot separate
truth from misconception in either regime. Resemblance tracks lexical/semantic overlap,
which distinguishes real misconceptions but not deliberate near-duplicates, making it
safe against honest content but **gameable** by the standard duplication attack. Only
causal reliance — credit by the drop in answer *correctness* — is robust to both, because
it asks the one question that both a gaming duplicate and a plausible misconception are
designed to obscure: does the answer's *quality* actually depend on this contribution?

**Deployability hinges on the quality signal.** Reliance needs a correctness signal, and
real deployments lack gold answers; the natural production signal is user feedback — a
contribution is worth crediting to the degree that answers relying on it are rated well.
Our weak-judge result is the cautionary flip side: an inaccurate signal collapses the
measure, so the signal, not the estimator, is what to invest in.

## 7. Incentive-compatibility

A faithful attribution score is not automatically a truthful *price*. Han et al.
[HanPrices2025] show LOO/Shapley valuations violate incentive-compatibility as prices in
**report-based** markets; that critique targets mechanisms eliciting private cost/value
reports, and the setting here elicits none (value is measured ex post), so it does not
transfer directly. What a marginal-credit objective buys is **manipulation-resistance** of
submitted content — and our adversarial regime is precisely a manipulation (near-duplicate)
test, on which reliance holds and resemblance does not. Report-based strategy-proofness —
a truthful, budget-balanced payment whose allocation is the reliance value (navigating the
VCG/Green–Laffont tension) — is scoped but unsolved.

## 8. Limitations

- **Corpora.** The adversarial corpus is synthetic (exact ground truth, at the cost of
  external validity); the natural corpus is real but small (n=25) and hand-curated. On
  the natural corpus, reliance is not uniquely best (resemblance edges it), so the
  positive case for reliance rests on *robustness across regimes*, not on dominating any
  single one.
- **Scale and models.** $n \le 50$; two small model families. Wilson intervals report the
  uncertainty; the natural corpus especially warrants a larger, independently-annotated
  set.
- **Judge accuracy.** The reliance result requires an accurate grader; a strong
  independent judge and a real user-feedback signal are untested.
- **Mechanism design.** Strategy-proof pricing is scoped, not solved (§7).

## 9. Conclusion

In attribution-based contributor payment for RAG, the credit objective is a first-order
choice with no safe default. The informativeness objective that current payout work uses
fails to distinguish true from false in both an adversarial near-duplicate regime and a
natural-misconception regime; resemblance is safe against honest content but gameable by
duplication; and only a causal-reliance objective is robust across both, conditional on an
accurate quality signal. Before building payment on top of attribution, evaluate the
objective in *both* contested regimes, and invest in the quality signal a faithful
objective depends on.

---

## Draft status / open items

**Have (this repo):** the isolation design; two contested regimes (adversarial synthetic
+ natural real-misconception); six reproducible runs; honest robustness, regime nuance,
and limitations; related-work positioning; the incentive-compatibility framing.

**In progress / queued:**
- **Natural corpus grown to ~44** (from 25), domain-tagged, with a
  [datasheet](../research/contested-facts-datasheet.md). *Still open:* third-party
  annotation and further scale — the set is single-author curated.
- **Strong generator + strong *independent* judge, both regimes** — specified as a
  ready-to-run GPU section (notebook `notebooks/gpu_benchmarks.ipynb` §13). This
  resolves the one soft spot in the current evidence: the local judge was a weak 3B
  model that eroded reliance to 0.53; a capable different-family judge tests whether
  reliance separation survives an *independent* strong grader. Results fold into
  Tables 1–2 when returned.

**Still needed (toward a full paper):**
1. Third-party annotation of the natural corpus.
2. A small **human eval** corroborating the strong-judge run.
3. A **user-feedback quality signal** on real answers — tests the deployable form.

**Venue:** data-centric ML / attribution / regulatable-ML workshops, or FAccT. The
strong-model + independent-judge runs (queued) are the main lift toward a stronger
venue.

**Citation keys** (resolve against `docs/research/key-prior-art-citations` / memory):
YeYoganarasimhan2025 (arXiv:2505.23842), AME2026 (2606.16075),
WallatFaithfulness2024 (2412.18004), AgentsThatMatter2026 (2605.27621),
DataShapley (Ghorbani & Zou 2019), LoGra (2405.13954), Fairshare (2502.00198),
HanPrices2025 (2504.05563), ALCE (Gao et al. 2023), MTBench2023 (Zheng et al. 2023).
