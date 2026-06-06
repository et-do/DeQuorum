# Attribution benchmark

Model: `qwen2.5-coder:7b` · queries measured: 10 · (contribution, answer) pairs: 28

## Is retrieval score a faithful proxy for causal value?

Ground truth per contribution is leave-one-out **marginal value**: how much the answer's resemblance to the contribution drops when it is removed. We correlate that against the cheap retrieval score.

- **Spearman(retrieval_score, marginal_value) = -0.116**
- Mean marginal value across pairs: 0.0105
- Flat credit (the naive ledger) is constant per citation, so by construction it has **zero** rank correlation with measured value — it carries no information about which contribution mattered.

## Per-query credit

### How do I type a generator function in Python that yields ints and returns a str?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `dc7c807ecd38` | 4.886 | 0.0730 | 0.697 |
| `1b8a0f1ed085` | 4.223 | 0.0318 | 0.303 |
| `804b288bdd50` | 3.035 | 0.0000 | 0.000 |

### What's the difference between asyncio.gather and asyncio.wait?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `4ab99fc759c0` | 1.994 | 0.0054 | 1.000 |
| `7c5a3400230d` | 3.595 | 0.0000 | 0.000 |
| `bf576530a6c4` | 2.948 | 0.0000 | 0.000 |

### How do I use ParamSpec to forward decorator signatures?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `833d356b899a` | 2.679 | 0.0095 | 1.000 |
| `7461f01ed4e3` | 2.234 | 0.0000 | 0.000 |

### What protocol does HTTP/3 run on?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `a2aedfbb97bf` | 1.903 | 0.0115 | 0.634 |
| `b6d3daefeefe` | 1.516 | 0.0066 | 0.366 |
| `932132d54b80` | 2.045 | 0.0000 | 0.000 |

### What are Rust's ownership rules?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `2d8f0c61365e` | 0.911 | 0.0520 | 0.656 |
| `991ae43b1c65` | 1.550 | 0.0272 | 0.344 |
| `f46eb04fbcb7` | 6.560 | 0.0000 | 0.000 |

### How do I write a Python metaclass?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `1b8a0f1ed085` | 1.398 | 0.0000 | 0.333 |
| `7461f01ed4e3` | 1.239 | 0.0000 | 0.333 |
| `dc7c807ecd38` | 0.783 | 0.0000 | 0.333 |

### What is Python's GIL and how does it affect threading?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `7d7e08192aa6` | 3.158 | 0.0000 | 0.333 |
| `bf576530a6c4` | 2.390 | 0.0000 | 0.333 |
| `4ab99fc759c0` | 2.083 | 0.0000 | 0.333 |

### How does Rust's match expression work with enums?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `2d8f0c61365e` | 1.443 | 0.0098 | 1.000 |
| `f46eb04fbcb7` | 3.168 | 0.0000 | 0.000 |

### What's the difference between pip and pipx?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `328a4a3ec465` | 0.994 | 0.0238 | 1.000 |
| `d0bd20996879` | 1.845 | 0.0000 | 0.000 |
| `5ff8b011b06b` | 0.891 | 0.0000 | 0.000 |

### What is HTTP/2 server push?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `932132d54b80` | 1.563 | 0.0262 | 0.613 |
| `774ba925c308` | 2.351 | 0.0165 | 0.387 |
| `a2aedfbb97bf` | 2.819 | 0.0000 | 0.000 |

## Gaming resistance

Duplicate-stuffing cannot inflate a contributor's marginal-credit share (a redundant copy has ~0 marginal value), whereas it does under flat credit. Proven deterministically in `tests/attribution/test_marginal.py::test_duplicate_stuffing_does_not_inflate_marginal_share`.
