# Per-Query Attribution Math — Late 2024 / 2025

> Literature sweep run 2026-05-26. Focus: the cross-cutting "credit assignment" question that underlies decentralized AI architectures.

## TL;DR

**Nothing published combines (deterministic per-query attribution) × (decentralized inference) × (strategy-proofness / incentive compatibility).** Each pairwise edge is covered; the triple is open. HDC bundling attribution in particular is treated as folk practice with no formal theory.

## 1. The underexplored intersection (priority question)

Each pairwise edge is covered:

- **VeriLLM** (Sun et al., 2025, arXiv:2509.24257) and the **ZKML survey** (Zhang et al., 2025, arXiv:2502.18535) handle *verifiable inference* but treat the model as monolithic — they prove *that* an output came from a stated model, not *how* to split credit across data sources.
- **Shapley-style context attribution** — MaxShapley (Cho et al., arXiv:2512.05958), TokenShapley (arXiv:2507.05261) — handles RAG-style per-query attribution but assumes a trusted central evaluator and no adversarial reporting.
- **Bittensor's Yuma Consensus** handles incentive-compatible scoring but uses validator opinion polls, not a deterministic attribution function.

**Concretely missing:** a deterministic per-query attribution functional `A(query, sources) → simplex` that is

1. cheap enough to compute online,
2. verifiable in a zk circuit or via succinct commitments, and
3. strategy-proof against sources misreporting embeddings / weights.

MaxShapley is the closest near-miss because it explicitly frames "incentive-compatible context attribution," but it operates centrally and not under cryptographic verification. **This is where novel work is most plausible.**

## 2. Data Shapley and beyond

The 2024–2025 frontier moved decisively off retraining-based Shapley.

- **In-Run Data Shapley** (Wang, Mittal, Song, Jia, ICLR 2025 — outstanding paper) computes per-iteration Shapley contributions in a single training pass, making foundation-scale attribution feasible.
- **Data Banzhaf** (Wang & Jia, AISTATS 2023) and **Weighted Banzhaf** (Li & Yu, NeurIPS 2023) replace Shapley with Banzhaf-family semivalues, provably more robust to SGD stochasticity.
- **Owen Sampling for Federated Contribution** (arXiv:2508.21261, 2025) accelerates estimation.

For per-*inference* (not per-training) attribution, published methods are essentially TokenShapley, MaxShapley, and *Scalable Data Attribution via Forward-Only Test-Time Inference* (arXiv:2511.19803). Owen values for hierarchical attribution and stratified Shapley estimators are published but not yet applied to streaming inference.

## 3. Influence functions / TRAK

**TRAK** (Park, Georgiev, Ilyas, Leclerc, Madry, ICML 2023) remains the production-relevant scalable estimator; **DataInf**, **LoGRA** (claims 6,500× throughput on Llama-3-8B), and the **Multi-stage Influence Function** (arXiv:2505.05017) push EK-FAC to LLM scale.

DataInf-style per-query attribution at inference is published but not in production: latency for a single query is still seconds-to-minutes on multi-billion-parameter models, and faithfulness on chat-style generation degrades sharply (Choe et al., "Do Influence Functions Work on Large Language Models?", arXiv:2409.19998 — answer: only partially). Datamodels remain training-time only; nobody has published a production-deployed per-query datamodel.

## 4. Decentralized / federated attribution

Published:

- **ShapFed** (IJCAI 2024) and CGSV for federated client attribution
- **FedOwen** (2025) for Owen-sampling efficiency
- **"Volatility of Shapley-Based Contribution Metrics in FL"** (arXiv:2405.08044) documents instability under FedAvg

Cryptographically verifiable inference exists (zkDL, ZKAUDIT, VeriLLM, Inference Labs' Bittensor SN2) but verifies *correctness*, not *attribution*.

**Not published, as far as I can find:** any system that

- (a) survives FedAvg parameter mixing while preserving per-contributor credit, and
- (b) produces a zk-verifiable per-query attribution receipt.

This is a clean gap.

## 5. The blending problem — status by architecture

| Architecture | Standard attribution practice | Formalization status |
| --- | --- | --- |
| Linear models | coefficient × feature | Closed-form, uncontroversial |
| MoE | gating weights as attribution | **Not formalized as a semivalue** — gating weights are not Shapley-consistent and nobody has proven the gap (MoE knowledge-attribution arXiv:2601.08383) |
| HDC bundling | bundling coefficients | **No formal attribution theory published** — Kleyko 2024 survey treats decomposition as capacity, not attribution |
| GNN / attention | attention weights | Widely critiqued (Liu et al., "Faithfulness Violation Test," ICML 2022); ARC-JSD (arXiv:2505.16415) offers JSD-based alternative |

Only linear and (loosely) MoE have anything resembling formalization. **HDC and attention-as-attribution remain hand-wavy.**

## Citations

- [Data Shapley in One Training Run (ICLR 2025)](https://arxiv.org/abs/2406.11011)
- [TokenShapley (arXiv:2507.05261)](https://arxiv.org/pdf/2507.05261)
- [MaxShapley (arXiv:2512.05958)](https://arxiv.org/pdf/2512.05958)
- [Forward-Only Test-Time Attribution (arXiv:2511.19803)](https://arxiv.org/pdf/2511.19803)
- [Data Banzhaf (AISTATS 2023)](https://arxiv.org/abs/2205.15466)
- [Weighted Banzhaf (NeurIPS 2023)](https://papers.nips.cc/paper_files/paper/2023/hash/bdb0596d13cfccf2db6f0cc5280d2a3f-Abstract-Conference.html)
- [TRAK (ICML 2023)](https://arxiv.org/abs/2303.14186)
- [Influence Functions on LLMs (Grosse et al. 2023)](https://arxiv.org/abs/2308.03296)
- [Do Influence Functions Work on LLMs? (arXiv:2409.19998)](https://arxiv.org/pdf/2409.19998)
- [Multi-stage Influence EK-FAC (arXiv:2505.05017)](https://arxiv.org/pdf/2505.05017)
- [ShapFed / Shapley-Driven FL (arXiv:2406.00569)](https://arxiv.org/html/2406.00569v1)
- [FedOwen (arXiv:2508.21261)](https://arxiv.org/pdf/2508.21261)
- [Volatility of Shapley in FL (arXiv:2405.08044)](https://arxiv.org/pdf/2405.08044)
- [VeriLLM (arXiv:2509.24257)](https://arxiv.org/html/2509.24257)
- [ZKML Survey (arXiv:2502.18535)](https://arxiv.org/pdf/2502.18535)
- [Bittensor Critical Analysis (arXiv:2507.02951)](https://arxiv.org/html/2507.02951v1)
- [Faithfulness Violation Test (ICML 2022)](https://proceedings.mlr.press/v162/liu22i/liu22i.pdf)
- [ARC-JSD context attribution (arXiv:2505.16415)](https://arxiv.org/pdf/2505.16415)
- [MoE Knowledge Attribution (arXiv:2601.08383)](https://arxiv.org/pdf/2601.08383)
- [Cost-Aware PoQ for Decentralized LLM (arXiv:2512.16317)](https://arxiv.org/pdf/2512.16317)
