# Category Theory in AI/ML — Late 2024 / 2025

> Literature sweep run 2026-05-26. Focus: how close is the published categorical-AI literature to a working provenance-functor system?

## TL;DR

**No published "provenance functor for ML inference" framework exists.** The DB-provenance literature (Green/Tannen semirings) and the categorical-ML literature (Markov categories, parametric lenses) run in parallel silos. Bridging them — a strict monoidal functor `F: 𝒞_compute → 𝒞_prov` faithful on composition — is a clean open seam.

## 1. Categorical provenance / attribution (priority question)

The two literatures exist in separate silos and the bridge is essentially open:

- **Database side:** Green / Karvounarakis / Tannen semiring provenance (2007) is the canonical formalism. Active extensions in 2024 include Bourgaux et al., *Semiring Provenance for Lightweight Description Logics* (arXiv:2310.16472) and Grädel et al., *Provenance Analysis and Semiring Semantics for First-Order Logic* (arXiv:2412.07986). These are semantics for queries/logic, **not for compositional inference morphisms**.
- **Category side:** Semirings are commutative-monoid objects; provenance semirings naturally live in symmetric monoidal categories. But there is **no paper** explicitly framing provenance semirings as morphism-decorations in a monoidal / Markov category, nor anything like a "lineage-aware monoidal category." Closest cousins: graded monads / effect systems (e.g., Katsumata, Kura, Ivašković's Cambridge thesis 2023 on graded monads for static analysis) — these track *effects*, and could in principle carry provenance, but no one has written that paper.
- **The closest near-miss:** Tull, Lorenz, Clark, et al., *Towards Compositional Interpretability for XAI* (arXiv:2406.17583, 2024) frames DisCoCirc-style models as "compositionally interpretable" with diagrammatic explanations via influence constraints and rewrite rules. This is the *interpretability* analogue of what we're describing, but it does not formalize attribution receipts as functorial output.

**Verdict: genuinely open seam.** A "decorated cospan / decorated PROP" treatment where decorations are provenance-semiring elements, with a functor `F: 𝒞_compute → 𝒞_prov` faithful on composition, would be novel.

## 2. DisCoPy / DisCoCirc

**Active, not stalled, but narrowing toward quantum.** DisCoPy v1.2.2 shipped Dec 2025 (github.com/discopy/discopy); ~2000 commits on main. The reference paper is Toumi, Yeung, Poór, de Felice, *DisCoPy: the Hierarchy of Graphical Languages in Python* (arXiv:2311.10608, 2023). Lambeq (Quantinuum) has absorbed the QNLP-specific layer. Recent DisCoCirc work: Laakkonen / Meichanetzidis / Coecke, *Quantum Algorithms for Compositional Text Processing* (arXiv:2408.06061, 2024); Waseem et al., *Efficient Generation of Parameterised Quantum Circuits from Large Texts* (arXiv:2505.13208, 2025). **Center of gravity is now quantum circuits for NLP**, not classical categorical ML.

## 3. Categorical ML / functorial programming

- **Categorical probability:** Very active. Fritz, Gonda, Houghton-Larsen, Lorenzin, Perrone, Stein, *Dilations and information flow axioms* (arXiv:2211.02507); Fritz/Perrone, *Absolute continuity, supports and idempotent splitting* (arXiv:2308.00651); Fritz et al., *Hidden Markov Models and the Bayes Filter in Categorical Probability* (arXiv:2401.14669, 2024); *Categorical algebra of conditional probability* (arXiv:2502.14941, 2025). Theory-dense, code-light.
- **Categorical foundations of deep learning:** Cruttwell / Gavranović / Ghani / Wilson / Zanasi, *Deep Learning with Parametric Lenses* (arXiv:2404.00408, 2024) is the consolidation paper. Gavranović's thesis *Fundamental Components of Deep Learning* (arXiv:2403.13001, 2024) and the ICML position paper *Categorical Deep Learning is an Algebraic Theory of All Architectures* (arXiv:2402.15332, 2024) are the standard references. Also Shiebler et al. survey, *Towards a Categorical Foundation of Deep Learning* (2024).
- **Compositional generalization:** *Functorial Neural Architectures from Higher Inductive Types* argues compositional generalization ≡ functoriality of the decoder — a sharp, testable claim.
- **Lenses / optics for ML:** Cybercat Institute's *Building a Neural Network from First Principles using Free Categories and Para(Optic)* (2024) plus Hirose's Haskell impl are the cleanest running examples.

## 4. Theory–practice gap

**Large.** DisCoPy / lambeq and the Cybercat Para(Optic) Haskell demo are essentially the only nontrivial running artifacts. The Cruttwell / Gavranović / Zanasi line has demonstrator code (boolean-circuit learning per Wilson / Zanasi arXiv:2101.10488) but nothing competitive with PyTorch. **A small experimental system that actually composes morphisms-with-receipts and runs end-to-end would be a real contribution** — most of this literature stops at the diagram.

## 5. Open questions worth chasing

1. **Provenance-functorial semantics for compositional inference.** Build a strict monoidal functor `F: 𝒞_compute → 𝒞_prov` where 𝒞_prov has morphisms labeled by elements of a provenance semiring (à la Green/Tannen) and prove `F` is faithful on composition — i.e., the receipt determines the trace up to rewrite. Untouched.
2. **Markov-category attribution.** Categorical probability has conditionals and disintegrations (Fritz et al.) but no formal notion of *attribution* of an output to specific input morphisms. Can one define an attribution-preserving subclass of Markov categories analogous to "causal" ones?
3. **Functoriality ≡ compositional generalization, made constructive.** The HIT/functor argument is currently existential. A constructive synthesis procedure that *compiles* a functor specification into a parameter-sharing scheme with provable generalization bounds would be new.

## Citations

- [DisCoPy hierarchy (arXiv:2311.10608)](https://arxiv.org/abs/2311.10608)
- [Quantum Algorithms for Compositional Text Processing (arXiv:2408.06061)](https://arxiv.org/pdf/2408.06061)
- [Efficient PQCs from Large Texts (arXiv:2505.13208)](https://arxiv.org/pdf/2505.13208)
- [Towards Compositional Interpretability for XAI — Tull et al. (arXiv:2406.17583)](https://arxiv.org/abs/2406.17583)
- [Deep Learning with Parametric Lenses (arXiv:2404.00408)](https://arxiv.org/pdf/2404.00408)
- [Fundamental Components of Deep Learning — Gavranović thesis (arXiv:2403.13001)](https://arxiv.org/abs/2403.13001)
- [Categorical Deep Learning is an Algebraic Theory (arXiv:2402.15332)](https://arxiv.org/abs/2402.15332)
- [HMMs in Categorical Probability (arXiv:2401.14669)](https://arxiv.org/abs/2401.14669)
- [Categorical algebra of conditional probability (arXiv:2502.14941)](https://arxiv.org/pdf/2502.14941)
- [Absolute continuity in categorical probability (arXiv:2308.00651)](https://arxiv.org/abs/2308.00651)
- [Dilations and information flow (arXiv:2211.02507)](https://arxiv.org/pdf/2211.02507)
- [Provenance Semantics for First-Order Logic (arXiv:2412.07986)](https://arxiv.org/abs/2412.07986)
- [Semiring Provenance for Description Logics (arXiv:2310.16472)](https://arxiv.org/abs/2310.16472)
- [Cybercat: NN from First Principles using Para(Optic)](https://cybercat.institute/2024/04/15/neural-network-first-principles/)
- [ACT 2024 Proceedings (EPTCS 429)](https://arxiv.org/abs/2509.18357)
- [DisCoPy GitHub](https://github.com/discopy/discopy)
