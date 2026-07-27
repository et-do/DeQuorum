# Attribution faithfulness vs known ground truth

Model: `llama3.2:3b` · facts 50 · contributions per query 4 (1 decisive + its false twin + others) · grader: keyword (deterministic, model-independent — KeywordRecallJudge / CoverageJudge)

**Hard / contested regime:** each query's distractor set includes the fact's own false twin (near-identical wording, flipped value — the version the model adopts ~80% of the time). This is the regime that matters for payouts: credit must land on the TRUE note even when a plausible competitor is present.

Each invented fact has exactly one decisive contribution (the note containing its gold). We measure how well each credit method recovers it: **rank-1** is how often the decisive contribution gets the most credit; **precision** is the share of credit placed on it (flat baseline = 0.25).

The three marginal methods share one leave-one-out machinery and differ only in the **objective** the ablation is scored against — the variable this experiment isolates: *resemblance* (embedding similarity to the removed note), *coverage* (reference-free topical informativeness — the Ye & Yoganarasimhan 2025 payout objective), and *reliance* (recall of the true gold — ours). Only reliance is truth-sensitive; resemblance and coverage are both satisfied equally by a fact and its fluent false twin.

| method | rank-1 accuracy (95% CI) | mean credit on decisive (95% CI) |
| --- | ---: | ---: |
| flat (baseline) | 0.250 [0.15, 0.38] (n=50) | 0.250 [0.15, 0.38] (n=50) |
| retrieval score | 0.500 [0.37, 0.63] (n=50) | 0.450 [0.32, 0.59] (n=50) |
| resemblance (embedding marginal) | 0.465 [0.33, 0.60] (n=50) | 0.467 [0.34, 0.60] (n=50) |
| coverage (informativeness marginal) | 0.265 [0.16, 0.40] (n=50) | 0.263 [0.16, 0.40] (n=50) |
| reliance (quality marginal) | 0.735 [0.60, 0.84] (n=50) | 0.735 [0.60, 0.84] (n=50) |

**Best method: reliance (quality marginal)** (rank-1 0.735, precision 0.735) — clears the flat baseline, so it recovers real causal value.
 Flat chance is 0.25. This is the faithful-value question of Claim 5, measured against ground truth instead of a noisy judge correlation.
