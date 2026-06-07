# Attribution benchmark

Model: `qwen2.5-coder:7b` · queries measured: 20 · (contribution, answer) pairs: 57

(Full gold-annotated question set, run on GPU.)

## Is retrieval score a faithful proxy for causal value?

Ground truth per contribution is leave-one-out **marginal value**: how much the answer's resemblance to the contribution drops when it is removed. We correlate that against the cheap retrieval score.

- **Spearman(retrieval_score, marginal_value) = 0.194**
- Mean marginal value across pairs: 0.0203
- Flat credit (the naive ledger) is constant per citation, so by construction it has **zero** rank correlation with measured value — it carries no information about which contribution mattered.

## Faithfulness: does the cheap measure track real answer quality?

Independent ground truth is a judge-measured quality delta (gold-fact recall with the contribution removed). We correlate it against both the embedding marginal and the retrieval score.

- Judge-scored pairs: 57
- **Spearman(embedding_marginal, judge_marginal) = 0.041** (higher ⇒ the cheap measure is faithful to real quality impact)
- Spearman(retrieval_score, judge_marginal) = -0.238 (near-zero ⇒ retrieval score is not a value proxy)

At this scale neither cheap signal tracks judged quality: the embedding marginal is essentially uncorrelated with it (0.041), and retrieval score is weakly negative (-0.238). The embedding marginal is therefore not validated as a payout signal as currently defined.

## Per-query credit

### How do I type a generator function in Python that yields ints and returns a str?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `62a52531794a` | 4.886 | 0.0717 | 0.736 |
| `62697c42ce11` | 4.223 | 0.0258 | 0.264 |
| `2b74fc4fc22c` | 3.035 | 0.0000 | 0.000 |

### What's the difference between asyncio.gather and asyncio.wait?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `4474c61fa149` | 3.595 | 0.0000 | 0.333 |
| `0d047f05fd9c` | 2.948 | 0.0000 | 0.333 |
| `23ccae3b9805` | 1.994 | 0.0000 | 0.333 |

### How do I use ParamSpec to forward decorator signatures?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `5575dafe3397` | 2.679 | 0.0000 | 0.500 |
| `3fae6cd26e41` | 2.234 | 0.0000 | 0.500 |

### What protocol does HTTP/3 run on?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `2d996fd25ca2` | 2.045 | 0.0000 | 0.333 |
| `96138f26f030` | 1.903 | 0.0000 | 0.333 |
| `47de6f6b60b1` | 1.516 | 0.0000 | 0.333 |

### What are Rust's ownership rules?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `f2f70a7b1e7b` | 1.550 | 0.0529 | 0.743 |
| `d7866787c48e` | 6.560 | 0.0183 | 0.257 |
| `0d9dcb392ae8` | 0.911 | 0.0000 | 0.000 |

### How do I annotate a Python generator that yields ints and returns a str?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `62a52531794a` | 2.936 | 0.0074 | 0.412 |
| `62697c42ce11` | 2.796 | 0.0058 | 0.324 |
| `3fae6cd26e41` | 2.479 | 0.0047 | 0.264 |

### What's the correct type hint for a generator function that returns a string?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `62a52531794a` | 6.837 | 0.0542 | 1.000 |
| `2b74fc4fc22c` | 2.710 | 0.0000 | 0.000 |
| `3fae6cd26e41` | 2.479 | 0.0000 | 0.000 |

### How should I type a generator's yield and return values in Python?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `62a52531794a` | 6.127 | 0.0980 | 0.861 |
| `2b74fc4fc22c` | 2.541 | 0.0158 | 0.139 |
| `62697c42ce11` | 4.223 | 0.0000 | 0.000 |

### When should I use asyncio.gather instead of asyncio.wait?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `b4210f4ce3d4` | 0.768 | 0.0321 | 1.000 |
| `4474c61fa149` | 5.856 | 0.0000 | 0.000 |
| `19b148e8eb13` | 2.201 | 0.0000 | 0.000 |

### How do asyncio.gather and asyncio.wait differ in handling results?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `4474c61fa149` | 3.595 | 0.0520 | 0.928 |
| `23ccae3b9805` | 1.188 | 0.0041 | 0.072 |
| `b4210f4ce3d4` | 1.689 | 0.0000 | 0.000 |

### What is the completion-semantics difference between gather and wait in asyncio?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `23ccae3b9805` | 2.262 | 0.0534 | 0.459 |
| `4474c61fa149` | 3.184 | 0.0406 | 0.349 |
| `b4210f4ce3d4` | 2.862 | 0.0223 | 0.192 |

### How do I preserve a decorator's signature using ParamSpec?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `5575dafe3397` | 1.642 | 0.0408 | 0.493 |
| `62a52531794a` | 2.023 | 0.0259 | 0.313 |
| `3fae6cd26e41` | 1.239 | 0.0161 | 0.194 |

### What is ParamSpec used for in Python typing?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `5575dafe3397` | 3.284 | 0.1560 | 0.694 |
| `62a52531794a` | 2.023 | 0.0688 | 0.306 |
| `62697c42ce11` | 2.281 | 0.0000 | 0.000 |

### How does PEP 612 ParamSpec help type a decorator's Callable?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `5575dafe3397` | 4.263 | 0.0000 | 0.333 |
| `62a52531794a` | 3.517 | 0.0000 | 0.333 |
| `3fae6cd26e41` | 1.524 | 0.0000 | 0.333 |

### Which transport protocol underlies HTTP/3?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `47de6f6b60b1` | 2.454 | 0.0204 | 1.000 |
| `96138f26f030` | 1.903 | 0.0000 | 0.000 |
| `499fc4c4b40e` | 0.923 | 0.0000 | 0.000 |

### Does HTTP/3 use QUIC, and what does QUIC run on?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `96138f26f030` | 1.903 | 0.0085 | 1.000 |
| `47de6f6b60b1` | 7.162 | 0.0000 | 0.000 |
| `2d996fd25ca2` | 2.045 | 0.0000 | 0.000 |

### What is the transport layer for HTTP/3?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `47de6f6b60b1` | 3.032 | 0.0295 | 1.000 |
| `499fc4c4b40e` | 3.981 | 0.0000 | 0.000 |
| `96138f26f030` | 2.819 | 0.0000 | 0.000 |

### What are the core ownership rules in Rust?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `d7866787c48e` | 5.661 | 0.0916 | 0.825 |
| `f2f70a7b1e7b` | 1.550 | 0.0194 | 0.175 |
| `0d9dcb392ae8` | 1.211 | 0.0000 | 0.000 |

### How does Rust enforce memory safety through ownership?

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `0d9dcb392ae8` | 1.443 | 0.0288 | 0.605 |
| `d7866787c48e` | 4.457 | 0.0188 | 0.395 |

### Explain Rust's borrowing and ownership model.

| contribution | retrieval score | marginal value | credit weight |
| --- | ---: | ---: | ---: |
| `d7866787c48e` | 4.457 | 0.0608 | 0.846 |
| `f2f70a7b1e7b` | 1.549 | 0.0111 | 0.154 |

## Gaming resistance

Duplicate-stuffing cannot inflate a contributor's marginal-credit share (a redundant copy has ~0 marginal value), whereas it does under flat credit. Proven deterministically in `tests/attribution/test_marginal.py::test_duplicate_stuffing_does_not_inflate_marginal_share`.
