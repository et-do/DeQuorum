# Attribution benchmark

Model: `qwen2.5-coder:7b` · queries measured: 8 · (contribution, answer) pairs: 23

## Is retrieval score a faithful proxy for causal value?

Ground truth per contribution is leave-one-out **marginal value**: how much the answer's resemblance to the contribution drops when it is removed. We correlate that against the cheap retrieval score.

- **Spearman(retrieval_score, marginal_value) = 0.191**
- Mean marginal value across pairs: 0.0158
- Flat credit (the naive ledger) is constant per citation, so by construction it has **zero** rank correlation with measured value — it carries no information about which contribution mattered.

## Faithfulness: does the cheap measure track real answer quality?

Independent ground truth is a judge-measured quality delta (gold-fact recall with the contribution removed). We correlate it against both the embedding marginal and the retrieval score.

- Judge-scored pairs: 23
- **Spearman(embedding_marginal, judge_marginal) = 0.207** (higher ⇒ the cheap measure is faithful to real quality impact)
- Spearman(retrieval_score, judge_marginal) = -0.196 (near-zero ⇒ retrieval score is not a value proxy)

## Per-query credit

### How do I type a generator function in Python that yields ints and returns a str?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `dc7c807ecd38` | 4.886 | 0.0556 | 1.000 |
| `1b8a0f1ed085` | 4.223 | 0.0000 | 0.000 |
| `804b288bdd50` | 3.035 | 0.0000 | 0.000 |

### What's the difference between asyncio.gather and asyncio.wait?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `7c5a3400230d` | 3.595 | 0.0111 | 0.736 |
| `bf576530a6c4` | 2.948 | 0.0040 | 0.264 |
| `4ab99fc759c0` | 1.994 | 0.0000 | 0.000 |

### How do I use ParamSpec to forward decorator signatures?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `833d356b899a` | 2.679 | 0.0000 | 0.500 |
| `7461f01ed4e3` | 2.234 | 0.0000 | 0.500 |

### What protocol does HTTP/3 run on?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `932132d54b80` | 2.045 | 0.0000 | 0.333 |
| `a2aedfbb97bf` | 1.903 | 0.0000 | 0.333 |
| `b6d3daefeefe` | 1.516 | 0.0000 | 0.333 |

### What are Rust's ownership rules?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `991ae43b1c65` | 1.550 | 0.1952 | 1.000 |
| `f46eb04fbcb7` | 6.560 | 0.0000 | 0.000 |
| `2d8f0c61365e` | 0.911 | 0.0000 | 0.000 |

### How do I annotate a Python generator that yields ints and returns a str?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `1b8a0f1ed085` | 2.796 | 0.0035 | 0.499 |
| `dc7c807ecd38` | 2.936 | 0.0032 | 0.454 |
| `7461f01ed4e3` | 2.479 | 0.0003 | 0.047 |

### What's the correct type hint for a generator function that returns a string?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `dc7c807ecd38` | 6.837 | 0.0000 | 0.333 |
| `804b288bdd50` | 2.710 | 0.0000 | 0.333 |
| `7461f01ed4e3` | 2.479 | 0.0000 | 0.333 |

### How should I type a generator's yield and return values in Python?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `dc7c807ecd38` | 6.127 | 0.0801 | 0.882 |
| `804b288bdd50` | 2.541 | 0.0108 | 0.118 |
| `1b8a0f1ed085` | 4.223 | 0.0000 | 0.000 |

## Gaming resistance

Duplicate-stuffing cannot inflate a contributor's marginal-credit share (a redundant copy has ~0 marginal value), whereas it does under flat credit. Proven deterministically in `tests/attribution/test_marginal.py::test_duplicate_stuffing_does_not_inflate_marginal_share`.
