# Attribution faithfulness vs known ground truth

Model: `qwen2.5-coder:7b` · facts 25 · contributions per query 4 (1 decisive + its false twin + others) · grader: keyword (deterministic, model-independent — KeywordRecallJudge / CoverageJudge)

**Hard / contested regime:** each query's distractor set includes the fact's own false twin (near-identical wording, flipped value — the version the model adopts ~80% of the time). This is the regime that matters for payouts: credit must land on the TRUE note even when a plausible competitor is present.

Each invented fact has exactly one decisive contribution (the note containing its gold). We measure how well each credit method recovers it: **rank-1** is how often the decisive contribution gets the most credit; **precision** is the share of credit placed on it (flat baseline = 0.25).

The three marginal methods share one leave-one-out machinery and differ only in the **objective** the ablation is scored against — the variable this experiment isolates: *resemblance* (embedding similarity to the removed note), *coverage* (reference-free topical informativeness — the Ye & Yoganarasimhan 2025 payout objective), and *reliance* (recall of the true gold — ours). Only reliance is truth-sensitive; resemblance and coverage are both satisfied equally by a fact and its fluent false twin.

| method | rank-1 accuracy (95% CI) | mean credit on decisive (95% CI) |
| --- | ---: | ---: |
| flat (baseline) | 0.250 [0.12, 0.44] (n=25) | 0.250 [0.12, 0.44] (n=25) |
| retrieval score | 0.480 [0.30, 0.67] (n=25) | 0.447 [0.27, 0.64] (n=25) |
| resemblance (embedding marginal) | 0.900 [0.72, 0.97] (n=25) | 0.856 [0.67, 0.95] (n=25) |
| coverage (informativeness marginal) | 0.270 [0.14, 0.47] (n=25) | 0.270 [0.14, 0.47] (n=25) |
| reliance (quality marginal) | 0.787 [0.59, 0.90] (n=25) | 0.787 [0.59, 0.90] (n=25) |

**Best method: resemblance (embedding marginal)** (rank-1 0.900, precision 0.856) — clears the flat baseline, so it recovers real causal value.
 Flat chance is 0.25. This is the faithful-value question of Claim 5, measured against ground truth instead of a noisy judge correlation.
