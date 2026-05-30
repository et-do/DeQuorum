# KG Reasoning + Cryptographic Provenance — Late 2024 / 2025

> Literature sweep run 2026-05-26. Focus: published systems that do multi-hop KG inference where each hop carries a cryptographic receipt back to an institutional source.

## TL;DR

Components exist (VeriDKG path proofs, W3C VC 2.0 signatures, Scallop semiring provenance) but **no published system glues them into multi-hop KG inference where each hop is signed by its institutional issuer.** Cryptographic semirings — semiring elements that are aggregatable signatures (e.g., BLS) — are an unwritten paper.

## 1. Cryptographic provenance (priority question)

Splits sharply along industrial (W3C / web3) vs. academic DB lines.

### Academic DB / authenticated graphs

- **VeriDKG** (Zhou et al., *PVLDB* Vol. 17, 2023/24, "VeriDKG: A Verifiable SPARQL Query Engine for Decentralized Knowledge Graphs"). Uses Merkle accumulators + a novel RGB-Trie + q-SBDH-based cryptographic accumulators to produce verifiable answers over distributed RDF sources. Verifies *query correctness*, not per-edge institutional attribution — but its proof structure is the natural substrate to bolt receipts onto.
- **ZKGraph** (Wu et al., arXiv:2507.00427, 2025). zk-SNARK-based verifiable graph query execution but explicitly does *not* track per-edge provenance or multi-source signatures.
- **zkSPARQL** (Wright, Shadbolt, Zhao et al., ISWC 2025). Proves correct SPARQL evaluation over signed / Merkle-committed RDF in a holder's VC wallet via Noir circuits — **single-holder only, no multi-issuer attribution**.

### Industrial / W3C stack

Three 2024 pieces compose into roughly what we want but **no one has glued them end-to-end:**

1. **RDF Dataset Canonicalization (RDF-canon)** — W3C Recommendation March 2024, enables stable hashing and signing of named graphs.
2. **Data Integrity BBS Cryptosuites** — W3C CR draft 2025, unlinkable selective-disclosure signatures over RDF.
3. **VC Data Model 2.0** — W3C 2024, issuer-attestation envelope.

Combining these to sign per-edge named-graph quads from distinct institutional issuers is *standardized and possible*, but **no published academic system does multi-hop inference where each hop carries its issuer's BBS / Ed25519 signature back to the originating institution.** That gap is the open territory.

## 2. Neuro-symbolic + attribution

Provenance in NeSy is almost entirely *baked into the inference algorithm*, not post-hoc — but **never cryptographic.**

- **Scallop** (Li, Huang, Naik et al., *PLDI* 2023; DOI 10.1145/3591280) — the flagship. Built directly on Green-Karvounarakis-Tannen provenance semirings extended to differentiable reasoning over Datalog with recursion / negation / aggregation. Every derived fact carries a semiring tag identifying contributing input tuples — i.e., **per-rule, per-fact attribution is native.**
- **DeepProbLog** (Manhaeve et al.) — similarly exposes derivation traces but treats them probabilistically, not as signed receipts.
- **Mileo et al.** (*Neurosymbolic AI* journal, 2025, "Towards a neuro-symbolic cycle for human-centered explainability") and the Bellomarini et al. chapter in the **Tannen Festschrift** (OASIcs Vol. 119, 2024) — explicitly use provenance to explain LLM-over-KG reasoning.

**None of these sign anything.**

## 3. Multi-hop with signed paths

**No published system** does multi-hop KG inference where each step carries a cryptographic signature from the contributing source. Components exist separately (VeriDKG's path proofs, VC signatures, Scallop's semiring trace) but the composition is unpublished as of late 2025.

## 4. Green-Tannen semirings, 2023–2025

Very active.

- **Bourgaux, Ozaki, Peñaloza** (arXiv:2310.16472, *AAAI* / DL workshops 2023–24) extended semiring provenance to lightweight description logics (EL, ELHr) — directly relevant to OWL-style KG inference.
- **Scallop** (above) is the NeSy instantiation.
- The **Tannen Festschrift** (OASIcs Vol. 119, 2024, Dagstuhl) collects several 2024 applications including ontological reasoning and provenance-aware DB design.

## 5. Genuinely open problems

1. **Cryptographic semirings.** No published semiring whose elements are *aggregatable signatures* (e.g., BLS) such that the semiring sum/product over a proof tree yields a single verifiable receipt over all contributing issuers. Combining Green-Tannen with signature aggregation is open.
2. **Per-hop attribution under recursion / negation.** Scallop handles differentiable provenance under recursion, but doing this with *cryptographic* (non-idempotent, non-commutative) tags — and proving soundness — is unresolved.
3. **Federated NeSy with adversarial sources.** No published treatment of multi-hop NeSy inference where some institutional edge-owners are Byzantine and proofs must remain sound; current verifiable-FL work (e.g., SoK Verifiable FL, ePrint 2025/2296) covers training, not symbolic inference.

## Citations

- [VeriDKG (PVLDB Vol. 17)](https://www.vldb.org/pvldb/vol17/p912-zhou.pdf)
- [ZKGraph (arXiv:2507.00427)](https://arxiv.org/abs/2507.00427)
- [zkSPARQL (ISWC)](https://zksparql.org/)
- [Scallop (PLDI 2023)](https://dl.acm.org/doi/10.1145/3591280)
- [Semiring Provenance for Lightweight DLs (arXiv:2310.16472)](https://arxiv.org/abs/2310.16472)
- [Tannen Festschrift OASIcs Vol. 119](https://drops.dagstuhl.de/entities/volume/OASIcs-volume-119)
- [RDF Dataset Canonicalization W3C Rec 2024](https://www.w3.org/news/2024/rdf-dataset-canonicalization-is-a-w3c-recommendation/)
- [VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [Neuro-Symbolic AI in 2024 Systematic Review](https://arxiv.org/html/2501.05435v1)
- [SoK Verifiable Federated Learning (ePrint 2025/2296)](https://eprint.iacr.org/2025/2296.pdf)
- [Survey on DIDs/VCs (arXiv:2402.02455)](https://arxiv.org/abs/2402.02455)
