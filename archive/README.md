# archive/

Shelved exploratory code. Kept because the questions it asks are still interesting and the property tests are still useful as patterns.

## Contents

- `vsa/` — Bipolar hyperdimensional computing primitives (bind, bundle, unbind, cosine) plus the pivotal-decomposition attribution functional. Was the candidate for Experiment 1 (a per-source attribution method for HDC bundles).
- `tests_vsa/` — Property tests for the above (hand-computed cases, semivalue axioms, empirical Banzhaf-vs-Shapley gap).
- `01-hdc-attribution-functional.md` — The original Experiment 1 spec.

## Why this is here, not in dequorum/

Project pivoted from **Path R** (research — invent novel non-LLM AI math) to **Path E** (engineering — build a crowdsourced LLM/MoE/LoRA network with peer review and tokenomics for OSS code knowledge). The HDC-specific math doesn't transfer to neural-network attribution; the core primitives (`Node`, `Signature`, `ProofObject`, `AttributionLedger`) and the four invariants do.

The literature reviews under `research/notes/` remain active — especially [04 (attribution math)](../research/notes/04-attribution-math-frontier.md), which is directly relevant to MoE gating-weight attribution.

## Key finding from Experiment 1 (worth remembering)

The "pivotal-decomposition" attribution formula proposed in the spec turned out to be mathematically **identical to Leave-One-Out (LOO) attribution**. The pivotality structure of HDC bundling gives LOO a closed-form `O(nd)` per-dimension expression — useful as an interpretability artifact, but not novel as a scalar attribution method. Empirically the LOO/Shapley gap was max ~0.08, mean ~0.02-0.05 on `n ∈ {3,5,7,9}`, `d ∈ {128, 1024}` random bipolar codebooks.
