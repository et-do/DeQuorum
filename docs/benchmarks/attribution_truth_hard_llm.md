# Attribution faithfulness vs known ground truth

Model: `qwen2.5-coder:7b` · facts 20 · contributions per query 4 (1 decisive + its false twin + others) · grader: LLM-as-judge (LLMJudge / LLMCoverageJudge, judge model `qwen2.5-coder:7b`)

> **Caveat (LLM judge):** the judge model is the generator, so scores may carry self-preference bias (Zheng et al. 2023, *Judging LLM-as-a-Judge*). The keyword grader — deterministic and model-independent — is the unbiased control; the objective gap holding under BOTH graders is the robustness claim.

**Hard / contested regime:** each query's distractor set includes the fact's own false twin (near-identical wording, flipped value — the version the model adopts ~80% of the time). This is the regime that matters for payouts: credit must land on the TRUE note even when a plausible competitor is present.

Each invented fact has exactly one decisive contribution (the note containing its gold). We measure how well each credit method recovers it: **rank-1** is how often the decisive contribution gets the most credit; **precision** is the share of credit placed on it (flat baseline = 0.25).

The three marginal methods share one leave-one-out machinery and differ only in the **objective** the ablation is scored against — the variable this experiment isolates: *resemblance* (embedding similarity to the removed note), *coverage* (reference-free topical informativeness — the Ye & Yoganarasimhan 2025 payout objective), and *reliance* (recall of the true gold — ours). Only reliance is truth-sensitive; resemblance and coverage are both satisfied equally by a fact and its fluent false twin.

| method | rank-1 accuracy (95% CI) | mean credit on decisive (95% CI) |
| --- | ---: | ---: |
| flat (baseline) | 0.250 [0.11, 0.47] (n=20) | 0.250 [0.11, 0.47] (n=20) |
| retrieval score | 0.500 [0.30, 0.70] (n=20) | 0.460 [0.27, 0.67] (n=20) |
| resemblance (embedding marginal) | 0.400 [0.22, 0.61] (n=20) | 0.409 [0.23, 0.62] (n=20) |
| coverage (informativeness marginal) | 0.312 [0.15, 0.53] (n=20) | 0.312 [0.15, 0.53] (n=20) |
| reliance (quality marginal) | 0.700 [0.48, 0.85] (n=20) | 0.686 [0.47, 0.84] (n=20) |

**Best method: reliance (quality marginal)** (rank-1 0.700, precision 0.686) — clears the flat baseline, so it recovers real causal value.
 Flat chance is 0.25. This is the faithful-value question of Claim 5, measured against ground truth instead of a noisy judge correlation.
