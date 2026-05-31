# HDC / VSA Frontier — Late 2024 / 2025

> Literature sweep run 2026-05-26. Focus: where is the genuine novelty headroom in Vector Symbolic Architectures, especially for attribution-in-bundling?

## TL;DR

**Attribution-in-bundling is unclaimed territory.** No paper combines `{Shapley, hyperdimensional}` or `{credit assignment, bundle, VSA}` with provable bounds. The vocabulary exists ("superposition catastrophe", "problem of 2"); the solutions don't.

## 1. Attribution-in-bundling (priority question)

**Verdict: genuine gap.** The literature touches the question from three sides but never lands on it:

- **Generic "HDC is interpretable" claims** rest on the *reversibility* of bind/unbind plus prototype memory — e.g. Schlegel et al., *PLOS Comp Bio* 2024 ("HDC: a fast, robust and interpretable paradigm for biological data", arXiv:2402.17572) argue HDC is post-hoc explainable and casually mention Shapley analysis *on input features fed to an HDC classifier*, not on bundle contents themselves. This conflates feature attribution with source attribution inside a superposition.
- **Hyperdimensional Probe** (Menchaca Resendiz et al., arXiv:2509.25045, 2025) uses VSA to *decode* LLM activations — orthogonal to bundle attribution.
- **Factorization work** (see §3) recovers *which factors* are present but does not quantify *how much each contributed* to a downstream similarity score, nor gives Shapley-coalitional bounds.
- **FactorHD** (Zhou et al., DAC 2025, arXiv:2507.12366) explicitly names the "superposition catastrophe" and "problem of 2" (multiple identical objects) as open — both are attribution-adjacent failures, and the paper offers an encoding workaround, not an attribution theory.

The closest theoretical scaffolding is Thomas, Dasgupta, Rosing (2021) and **Clarkson et al., "Capacity Analysis of VSAs"** (NeurIPS 2023, OpenReview 6tazBqPem3) which bound *recovery* probability of a single component, not *contribution share* of each.

## 2. Active threads & labs

- **IBM Zurich** (Rahimi, Sebastian, Hersche, Karunaratne) — neuro-vector-symbolic for Raven's (Hersche et al., *Nature Machine Intelligence* 2023), in-memory hardware, factorizers. Most prolific lab.
- **Redwood / Berkeley** (Olshausen, Frady, Sommer, Kymn, Kent) — resonator theory, sparse coding integration, capacity analysis.
- **Heddes & Aksanli (UC Irvine)** — `torchhd` (JMLR 2023); maintenance + applications, not new theory.
- **Neubert / Schubert (TU Chemnitz)** — robotics, place recognition; quieter in 2024–2025.
- **Imani (UC Irvine/Davis)** — HDQF, graph HDC, security applications.
- **Eliasmith / Waterloo (CNRG)** — Spatial Semantic Pointers; Dumont 2024–2025 work on SSP for control/navigation.
- **Camposampiero, Wattenhofer (ETH)** — abstract reasoning with NVSA (Hersche et al., arXiv:2412.05586, 2025).
- **Kleyko (RISE Sweden) + Rachkovskij** — surveys, capacity theory.

## 3. Resonator networks state (2023–2025)

The frontier is dominated by the IBM Zurich group:

- **Langenegger, Karunaratne et al., *Nature Nanotechnology* 2023** — in-memory resonator factorizer on PCM crossbars.
- **Hersche, Terzić, Karunaratne, Langenegger et al., "Factorizers for Distributed Sparse Block Codes"**, *Neurosymbolic AI* journal 2025 — generalized sparse block codes (GSBC), ℓ∞ similarity, threshold + conditional sampling. Tackles **non-orthogonal / noisy** codebooks emerging from CNN feature extractors.
- **Terzić, Hersche et al., "On the Role of Noise in Factorizers"** (MLNCP @ NeurIPS 2024, arXiv:2412.00354) — Asymmetric Codebook Factorizer (ACF); deliberately injected noise escapes limit cycles, ~50× operational capacity gain.
- **Kymn, Kleyko, Frady, Sommer, Olshausen** — "Compositional Factorization of Visual Scenes with Convolutional Sparse Coding and Resonator Networks" (arXiv:2404.19126, 2024) — combines sparse coding with resonators for natural images, directly addressing the **non-orthogonal codebook** problem.
- **Poduval, Zou, Velasquez, Imani, "Hyperdimensional Quantum Factorization"** (CVPR 2024 / arXiv:2406.11889) — quantum-search formulation, quadratic speedup.

**What's missing from all of these: convergence bounds yes, attribution bounds no.** None give per-factor confidence in the presence of distractors / off-codebook noise.

## 4. Genuinely open questions (2025)

1. **Attribution / source-share inside a bundle** — Shapley-decomposition of `sim(B, q)` over the bundled atoms, with sample-complexity / dimensionality bounds. Nobody has published this. **← Experiment 1 target.**
2. **Factorization on truly non-orthogonal, learned codebooks with attribution bounds** — Kymn+Olshausen 2024 and the GSBC paper address recovery, not certified bounds. Open.
3. **Compositional "problem of 2" / multiplicity** — explicitly called out by FactorHD (Zhou 2025) and unresolved: representing and *attributing* multiple instances of the same symbol within one bundle.
4. **Deterministic HDC encoders with learning-theoretic guarantees** — most current encoders are either random or learned-but-opaque; bridging is open per the Frontiers 2024 "holographic adaptive encoder" agenda.

## Citations

- [Hersche et al., Factorizers for Distributed Sparse Block Codes (2025)](https://journals.sagepub.com/doi/10.3233/NAI-240713)
- [Terzić/Hersche et al., On the Role of Noise in Factorizers (NeurIPS MLNCP 2024)](https://arxiv.org/abs/2412.00354)
- [Kymn/Olshausen et al., Compositional Factorization with Convolutional Sparse Coding + Resonators (2024)](https://arxiv.org/pdf/2404.19126)
- [Poduval et al., Hyperdimensional Quantum Factorization (CVPR 2024)](https://arxiv.org/abs/2406.11889)
- [Zhou et al., FactorHD (DAC 2025)](https://arxiv.org/html/2507.12366)
- [Schlegel et al., HDC interpretable paradigm (PLOS CB 2024)](https://arxiv.org/pdf/2402.17572)
- [Hyperdimensional Probe (2025)](https://arxiv.org/html/2509.25045v1)
- [Hersche et al., NVSA for Raven's (Nature MI 2023)](https://www.nature.com/articles/s42256-023-00630-8)
- [Hersche et al., LLMs vs Neuro-symbolic on arithmetic reasoning (2024/2025)](https://arxiv.org/pdf/2412.05586)
- [Capacity Analysis of VSAs (NeurIPS 2023)](https://openreview.net/forum?id=6tazBqPem3)
- [Kleyko/Rachkovskij HDC/VSA Survey Part I](https://arxiv.org/abs/2111.06077) / [Part II](https://arxiv.org/abs/2112.15424)
- [Modelling neural probabilistic computation using VSAs (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11655797/)
