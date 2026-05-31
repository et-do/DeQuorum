# archive/

Shelved exploratory code. Kept because the questions it asks are still interesting and the property tests are still useful as patterns.

## Contents

### HDC research (Experiment 1, Path R)

- `vsa/` — Bipolar hyperdimensional computing primitives (bind, bundle, unbind, cosine) plus the pivotal-decomposition attribution functional. Was the candidate for Experiment 1 (a per-source attribution method for HDC bundles).
- `tests_vsa/` — Property tests for the above (hand-computed cases, semivalue axioms, empirical Banzhaf-vs-Shapley gap).
- `01-hdc-attribution-functional.md` — The original Experiment 1 spec.

### Deterministic toy pipeline (early scaffolding, Path R)

These were the original deterministic-AI scaffolding modules — a 3-node toy "expert network" (chemical → pharma → legal), categorical composition primitives, and a signed knowledge graph router. They demonstrated the four invariants (reproducibility, provenance, explicit failure, compositional locality) without an LLM. Useful as patterns but **not used by the active Path E pipeline**.

- `category/` — `Morphism` + `compose()` building a `ProofObject` chain from arbitrary `Node` calls.
- `expert_network/` — 3-node deterministic pipeline (`ChemicalNode`, `PharmaNode`, `LegalNode`) wired via the category module.
- `graph/` — `KnowledgeGraph` with signed-edge attribution via shortest-path routing.
- `tests_category/`, `tests_expert_network/`, `tests_graph/` — unit tests for the above.
- `tests_invariants/` — property tests (hypothesis-based) for the four invariants, exercised against the toy pipeline and the graph router.

## Why this is here, not in src/dequorum/

The project pivoted from **Path R** (research — invent novel non-LLM AI math) to **Path E** (engineering — DeQuorum: crowdsourced LLM/MoE/LoRA network with peer review and tokenomics). The HDC-specific math doesn't transfer to neural-network attribution; the deterministic toy doesn't ship as a product.

What DOES carry forward from Path R, in active use under `src/dequorum/`:

- The core primitives in `core/`: `Node`, `Signature`, `ProofObject`, `AttributionLedger`, `CompositionError`/`MissingData`, canonical hashing.
- The conceptual model of signing every output and chaining signatures end-to-end.
- The four invariants as a quality bar (now enforced informally rather than by a dedicated invariants test suite — those tests targeted only the archived toy modules).

The literature reviews under `research/notes/` remain active references — especially [04 (attribution math)](../research/notes/04-attribution-math-frontier.md), which is directly relevant to MoE gating-weight attribution.

## Key finding from Experiment 1 (worth remembering)

The "pivotal-decomposition" attribution formula proposed in the spec turned out to be mathematically **identical to Leave-One-Out (LOO) attribution**. The pivotality structure of HDC bundling gives LOO a closed-form `O(nd)` per-dimension expression — useful as an interpretability artifact, but not novel as a scalar attribution method. Empirically the LOO/Shapley gap was max ~0.08, mean ~0.02-0.05 on `n ∈ {3,5,7,9}`, `d ∈ {128, 1024}` random bipolar codebooks.

## Restoring

If a piece becomes useful again, `git mv archive/<thing> src/dequorum/<thing>` brings it back. Imports inside archived files already use the `dequorum.` prefix from the original codebase.
