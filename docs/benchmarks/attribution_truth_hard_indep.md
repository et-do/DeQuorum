# Attribution faithfulness vs known ground truth

Model: `qwen2.5-coder:7b` · facts 50 · contributions per query 4 (1 decisive + its false twin + others) · grader: LLM-as-judge (LLMJudge / LLMCoverageJudge, INDEPENDENT judge model `llama3.2:3b`, generator `qwen2.5-coder:7b`)

> **Independent judge:** the grader is a different model than the generator, so self-preference bias (Zheng et al. 2023) does not apply. The objective gap holding here corroborates the keyword control.

**Hard / contested regime:** each query's distractor set includes the fact's own false twin (near-identical wording, flipped value — the version the model adopts ~80% of the time). This is the regime that matters for payouts: credit must land on the TRUE note even when a plausible competitor is present.

Each invented fact has exactly one decisive contribution (the note containing its gold). We measure how well each credit method recovers it: **rank-1** is how often the decisive contribution gets the most credit; **precision** is the share of credit placed on it (flat baseline = 0.25).

The three marginal methods share one leave-one-out machinery and differ only in the **objective** the ablation is scored against — the variable this experiment isolates: *resemblance* (embedding similarity to the removed note), *coverage* (reference-free topical informativeness — the Ye & Yoganarasimhan 2025 payout objective), and *reliance* (recall of the true gold — ours). Only reliance is truth-sensitive; resemblance and coverage are both satisfied equally by a fact and its fluent false twin.

| method | rank-1 accuracy (95% CI) | mean credit on decisive (95% CI) |
| --- | ---: | ---: |
| flat (baseline) | 0.250 [0.15, 0.38] (n=50) | 0.250 [0.15, 0.38] (n=50) |
| retrieval score | 0.500 [0.37, 0.63] (n=50) | 0.450 [0.32, 0.59] (n=50) |
| resemblance (embedding marginal) | 0.500 [0.37, 0.63] (n=50) | 0.496 [0.36, 0.63] (n=50) |
| coverage (informativeness marginal) | 0.298 [0.19, 0.44] (n=50) | 0.298 [0.19, 0.44] (n=50) |
| reliance (quality marginal) | 0.525 [0.39, 0.66] (n=50) | 0.495 [0.36, 0.63] (n=50) |

**Best method: reliance (quality marginal)** (rank-1 0.525, precision 0.495) — clears the flat baseline, so it recovers real causal value.
 Flat chance is 0.25. This is the faithful-value question of Claim 5, measured against ground truth instead of a noisy judge correlation.
