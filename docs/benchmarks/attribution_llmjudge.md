# Attribution benchmark — LLM judge

Model: `qwen2.5-coder:7b` · queries measured: 20 · (contribution, answer) pairs: 57

Same procedure as [attribution.md](attribution.md), but the faithfulness judge is an LLM-as-judge (0–10 correctness rubric) instead of gold-fact recall. The point is to test whether the near-zero faithfulness correlation under the coarse recall judge is a judge artifact.

## Is retrieval score a faithful proxy for causal value?

- **Spearman(retrieval_score, marginal_value) = -0.011**
- Mean marginal value across pairs: 0.0216

## Faithfulness: does the cheap measure track real answer quality?

- Judge-scored pairs: 57
- **Spearman(embedding_marginal, judge_marginal) = 0.148**
- Spearman(retrieval_score, judge_marginal) = 0.093

## Comparison to the gold-recall judge

| Correlation | gold-recall judge | LLM judge |
| --- | ---: | ---: |
| embedding_marginal vs judge_marginal | 0.041 | **0.148** |
| retrieval_score vs judge_marginal | -0.238 | 0.093 |

The judge matters: the embedding marginal's correlation with judged quality roughly triples under the less-brittle LLM judge (0.04 → 0.15), and the spurious negative for retrieval score disappears. So part of the recall-judge near-zero was judge coarseness. But even under the LLM judge the embedding marginal is only **weakly** correlated with quality (0.15) — a real signal, above retrieval score (0.09) and flat credit (0), yet far short of what setting payouts would require. Faithfulness remains unestablished; a stronger judge (held-out human references) and a larger sample are the next step.
