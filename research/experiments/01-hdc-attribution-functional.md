# Experiment 1 — HDC Bundle Attribution Functional

> **Status:** draft spec. Authored 2026-05-27. No code written yet.
> **Goal:** define and validate a per-source attribution functional for HDC bundles, with closed-form computation and game-theoretic axioms.

## 1. Claim

> Bipolar HDC bundling is structurally a **per-dimension binary voting game**. The Banzhaf power index for that game gives a per-source attribution functional `A(B, q, v_i)` that:
>
> 1. is computable in `O(nd)` (vs. `O(2^n · d)` for naïve coalitional Shapley),
> 2. satisfies the standard semivalue axioms (symmetry, dummy, linearity in `q`),
> 3. agrees with full Shapley up to a known scaling factor on symmetric majority games, and
> 4. captures the non-linearity of the `sign()` threshold that bundling-coefficient attribution misses.

If all four hold, this is the first formal attribution theory for HDC bundles ([notes 01](../notes/01-vsa-hdc-frontier.md) §1 confirmed the gap).

## 2. Background

- HDC bundling is the operation that *destroys source identity* in superpositions. Practitioners use bundling coefficients or cosine similarities as ad-hoc attribution; the 2024 Kleyko HDC survey treats this as a capacity question, not an attribution one ([notes 04](../notes/04-attribution-math-frontier.md) §5).
- Resonator networks ([Hersche 2025](https://journals.sagepub.com/doi/10.3233/NAI-240713), [Kymn 2024](https://arxiv.org/pdf/2404.19126), [Terzić 2024](https://arxiv.org/abs/2412.00354)) recover *which* factors are present but never quantify *how much each contributed* to a downstream similarity score.
- Game-theoretic semivalues for ML attribution — Data Shapley ([Ghorbani & Zou 2019](https://arxiv.org/abs/1904.02868)), Data Banzhaf ([Wang & Jia 2023](https://arxiv.org/abs/2205.15466)), Weighted Banzhaf ([Li & Yu 2023](https://papers.nips.cc/paper_files/paper/2023/hash/bdb0596d13cfccf2db6f0cc5280d2a3f-Abstract-Conference.html)) — exist at the training-data level. **None have been applied to HDC bundles.**
- The voting-theoretic backbone (Banzhaf 1965, Penrose 1946, Shapley-Shubik 1954) is settled mathematics. The novelty is the bridge.

## 3. Definitions

Let:

- `d ∈ ℕ` — dimensionality (e.g. 10,000).
- `n ∈ ℕ` — number of source vectors in the bundle. Assume `n` odd for clean tie-breaking.
- `v_1, ..., v_n ∈ {-1, +1}^d` — the source vectors.
- `S ∈ ℤ^d` — pre-threshold sum, `S[k] = Σ_i v_i[k]`.
- `B = sign(S) ∈ {-1, +1}^d` — the bundle.
- `q ∈ {-1, +1}^d` — a query vector.
- `sim(B, q) := (1/d) Σ_k B[k] · q[k] ∈ [-1, +1]` — cosine on bipolar vectors.
- A coalition `T ⊆ {1, ..., n}` defines `B_T = sign(Σ_{i ∈ T} v_i)` (assume |T| odd).

The **coalitional game** is `v(T) := sim(B_T, q)`.

### Pivotality

Source `i` is **pivotal** at dimension `k` under coalition `T` iff
`sign(Σ_{j ∈ T} v_j[k]) ≠ sign(Σ_{j ∈ T, j ≠ i} v_j[k])`.

For the grand coalition `T = {1, ..., n}`, this reduces to a clean condition: `i` is pivotal at `k` iff `|S[k]| = 1` and `v_i[k] = sign(S[k])` (i.e., `i` voted with a one-vote-majority bloc).

## 4. Candidate functional

Define the **per-dimension Banzhaf attribution**:

```
A(B, q, v_i) := (1/d) Σ_k 𝟙[ pivotal(i, k) ] · v_i[k] · q[k]
```

Equivalently, restricting the sum to the pivotal dimensions:

```
A(B, q, v_i) = (1/d) Σ_{k : |S[k]| = 1, v_i[k] = sign(S[k])} q[k] · sign(S[k])
```

### Why this is closed-form O(nd)

For each dimension `k`:
1. Compute `S[k]` in `O(n)`.
2. Check `|S[k]| = 1` in `O(1)`.
3. If pivotal, all sources with `v_i[k] = sign(S[k])` get credited `q[k] · sign(S[k]) / d`.

Total work: `O(nd)`. No coalitional enumeration, no Monte Carlo.

## 5. Required axioms (semivalue conditions)

The functional `A` must be tested against (and ideally proven to satisfy):

| # | Axiom | Statement |
| - | ----- | --------- |
| A1 | **Symmetry** | If `v_i ≡ v_j` then `A(B, q, v_i) = A(B, q, v_j)`. |
| A2 | **Dummy** | If `v_i` is never pivotal at any `k`, then `A(B, q, v_i) = 0`. |
| A3 | **Linearity in `q`** | `A(B, q_1 + q_2, v_i) = A(B, q_1, v_i) + A(B, q_2, v_i)`. |
| A4 | **Anti-symmetry in `v_i`** | `A(B, q, -v_i) = -A(B, q, v_i)` *holds only if we hold the rest of the bundle fixed and recompute B; this needs careful treatment.* |
| A5 | **Efficiency (conditional)** | `Σ_i A(B, q, v_i) = sim(B, q)`? **Open — likely fails in general, holds only at "tight" dimensions. This is the most interesting axiom to test.** |

A1–A3 should hold by construction. A4 is delicate because flipping `v_i` changes `B`. A5 (efficiency) is the **load-bearing open question**: when does the Banzhaf sum equal the game value?

## 6. Conjectures to prove

| # | Conjecture | Notes |
| - | ---------- | ----- |
| C1 | `A` satisfies A1–A3 exactly. | Should follow from definition; write proof. |
| C2 | `A` equals the exact per-dimension Banzhaf power index, normalized by `q[k]`. | The bridge to voting theory. |
| C3 | On symmetric games (all `v_i` drawn uniformly from `{-1, +1}^d`), `E[A(B, q, v_i)] = (1/n) · E[sim(B, q)] · P[pivotal]`. | A characterization of the expected attribution. |
| C4 | The L∞ gap between `A` and the exact Shapley value `φ_i^{Sh}` is `O(1/√n)` on random codebooks. | Bound the approximation error. |
| C5 | For `n` large, `Σ_i A ≈ sim(B, q) · c(n)` for a known constant `c(n) → 1`. | "Asymptotic efficiency." |

These are conjectures, not theorems. Some will turn out false — those are the most informative results.

## 7. Empirical hypotheses

To test on synthetic data:

- **H1** (efficiency rate). For `n ∈ {3, 5, 7, 9, 11}` and `d ∈ {1024, 4096, 10000}`, measure `Σ_i A(B, q, v_i) / sim(B, q)`. Plot as a function of `n, d`.
- **H2** (Shapley agreement). For `n ≤ 11`, compute exact Shapley via brute coalition enumeration and compare with `A`. Quantify L1, L2, L∞ gap.
- **H3** (sample complexity). How many bundle / query pairs are needed for the empirical `A` distribution to converge?
- **H4** (failure modes). What happens when `n` is even, or when source vectors are non-orthogonal (drawn from a low-rank codebook)?
- **H5** (vs. resonator factorization). On the same codebooks where resonator networks succeed at factor recovery, does `A` give attribution that ranks the *correct* factors higher than the distractors? Baseline against [Hersche 2025 GSBC](https://journals.sagepub.com/doi/10.3233/NAI-240713).

## 8. Baselines

| Baseline | What it computes | Why it's interesting |
| -------- | ---------------- | -------------------- |
| **Bundling coefficient** | `1/n` for every source | Folk practice; should fail to discriminate |
| **Per-source cosine** | `sim(v_i, q) / n` | Linear pre-threshold approximation; ignores `sign()` |
| **Monte Carlo Shapley** | sample coalitions, average marginals | Ground-truth Shapley up to sampling variance |
| **Resonator factorization presence** | binary "is factor present" | Adjacent task — recovery, not attribution |

`A` should beat the first two on a faithfulness metric (e.g., remove-and-rescore), match the third within bounded error, and complement the fourth.

## 9. Falsification criteria

Concrete observations that would *kill* the claim:

1. If `A` satisfies efficiency asymptotically with `c(n) → 0` rather than `c(n) → 1`, then the functional is uninformative at scale. **Falsifies C5.**
2. If the L∞ gap to exact Shapley does not converge faster than `O(1)`, then `A` is not a tight Banzhaf approximation. **Falsifies C4.**
3. If `A` ranks sources *anti-correlated* with the remove-and-rescore baseline more than ~5% of the time, the functional is misleading. **Falsifies usefulness.**
4. If a published paper already states C1–C5 with proofs, **the experiment is unpublishable as novelty** (but is still useful internal validation). The literature sweep ([notes 01](../notes/01-vsa-hdc-frontier.md), [notes 04](../notes/04-attribution-math-frontier.md)) found no such paper as of 2025-05.

## 10. Implementation roadmap (ties into `ai_playground/vsa/`)

Phase 0 — primitives (done). `random_hypervector`, `bind`, `bundle`, `cosine` already exist.

Phase 1 — exact reference. Add `ai_playground/vsa/attribution.py`:
- `banzhaf_attribution(bundle_components, query) -> dict[int, float]` — the `A` functional.
- `exact_shapley(bundle_components, query) -> dict[int, float]` — brute-force `O(2^n d)` ground truth.
- `remove_and_rescore_attribution(bundle_components, query) -> dict[int, float]` — model-faithful baseline.

Phase 2 — property tests under `tests/vsa/test_attribution.py`:
- Symmetry, dummy, linearity in `q` (hypothesis tests).
- Bit-exact reproducibility (carries from `core` invariants).
- Empirical L∞ gap between `banzhaf_attribution` and `exact_shapley` for small `n`.

Phase 3 — empirical sweep under `research/experiments/01-hdc-attribution-functional/`:
- `run_h1_efficiency.py` — sweep `(n, d)`, plot efficiency rate.
- `run_h2_shapley_agreement.py` — L1/L2/L∞ gap at small `n`.
- `run_h3_sample_complexity.py` — convergence with sample count.
- `run_h4_codebook_structure.py` — non-orthogonal codebooks.
- `run_h5_vs_resonator.py` — comparison against GSBC factorizer (needs `torchhd` or a reimpl).
- Plots saved to `results/`. Raw data saved as parquet / numpy.

Phase 4 — write-up. If results survive falsification, draft a paper. If they don't, document what failed and why — that's the novel knowledge.

## 11. Stretch goals (only after Phase 3)

- Extend to **multi-set bundles** (the "problem of 2" — same vector bundled multiple times). FactorHD identifies this as open.
- Extend to **non-bipolar VSAs** (FHRR, MAP, sparse block codes). The pivotality argument changes for complex-valued and sparse representations.
- Derive **strategy-proofness** conditions: can a malicious source forge `v_i` to inflate its `A`? (Connection to mechanism design.)
- Connect to **categorical attribution** ([notes 02](../notes/02-categorical-ai-frontier.md) §1): show `A` is a Markov-category morphism with provenance decoration.

## 12. References (deduped from notes)

Primary game-theoretic background:

- Banzhaf, J. F. (1965). *Weighted voting doesn't work: A mathematical analysis*. Rutgers Law Review.
- Shapley, L. S. & Shubik, M. (1954). *A method for evaluating the distribution of power in a committee system*. APSR.
- Owen, G. (1995). *Game Theory* (3rd ed.).

HDC / VSA:

- Kleyko, D. et al. (2022). *VSA / HDC Survey* — [Part I (arXiv:2111.06077)](https://arxiv.org/abs/2111.06077), [Part II (arXiv:2112.15424)](https://arxiv.org/abs/2112.15424).
- Hersche, M. et al. (2025). *Factorizers for Distributed Sparse Block Codes*. [Sage Neurosymbolic AI](https://journals.sagepub.com/doi/10.3233/NAI-240713).
- Zhou, Y. et al. (2025). *FactorHD* (DAC 2025). [arXiv:2507.12366](https://arxiv.org/html/2507.12366).
- Clarkson, K. et al. (2023). *Capacity Analysis of VSAs*. [NeurIPS 2023](https://openreview.net/forum?id=6tazBqPem3).

Attribution math:

- Wang, J. & Jia, R. (2023). *Data Banzhaf*. [AISTATS 2023](https://arxiv.org/abs/2205.15466).
- Wang, J. et al. (2025). *In-Run Data Shapley*. [ICLR 2025 outstanding paper](https://arxiv.org/abs/2406.11011).
- Park, S. M. et al. (2023). *TRAK*. [ICML 2023](https://arxiv.org/abs/2303.14186).

## 13. Open questions / unknowns going in

- We don't yet know whether `A` satisfies efficiency (A5) at all, or only asymptotically.
- We don't know whether the closed-form holds for even `n` with deterministic tie-breaking.
- We don't know whether the pivotality argument extends to bind-then-bundle compositions (the typical HDC encoding pattern).
- We don't know whether `A` is monotone in `v_i`'s alignment with `q`; this matters for incentive compatibility.

These unknowns are the experiment.
