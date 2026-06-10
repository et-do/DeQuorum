# Product, Incentive & Architecture Direction — mid-2026

> Direction/decision record written 2026-06-10. Unlike notes 01–04 (external literature sweeps), this synthesizes our **own** experimental results (the GPU benchmark suite under [docs/benchmarks/](../../benchmarks/)) into product and architecture decisions. It answers: given what we now have, is the current path the strongest, and what should we build and test next.

## TL;DR

The **architecture is sound** — the pivot from Path R (invent novel non-LLM math) to Path E (route → retrieve → distill on an open LLM + LoRA, with signed peer review and a kickback economy) is settled and correct. But one problem gates the entire thesis: a **faithful value measure for attribution**. Marginal-value attribution correlates with judged quality at only ρ ≈ 0.04–0.15 (Claim 5). Until that's solved the economic layer is theoretical, and it is *also* where our only genuine novelty lives (note 04). So the strongest path forward is not a new architecture — it is to treat **faithful, strategy-proof, verifiable attribution as the core bet**, and to build the data and governance components that make it possible.

## 1. Is the current path the strongest? — Yes on architecture, with one dominating caveat

What our benchmarks established (see [docs/benchmarks/](../../benchmarks/)):

- **Grounding works** where the base model is ignorant: novelty lift +0.69 (C2). The mechanism is real.
- **Routing, coverage, and the judge are sound** — clean in/out-of-domain separation (C1), a validated quality judge (6b, pairwise 0.94–1.00). The measurement substrate is trustworthy.
- **Attribution ranks and resists gaming**, but its *link to value is weak and judge-sensitive* (Claim 5). This is the crux.
- **The model has no defense against false content**: grounding adopts a false contribution 87.5% of the time (falsehood-bench), and when a true and false contribution are both retrieved the answer follows ordering, not truth (conflict-bench). Correctness rests **entirely** on governance.

So two things are load-bearing and under-resourced relative to their importance: **(a)** the faithful value measure (for payouts), and **(b)** governance robustness (for correctness). Everything else is comparatively commodity.

## 2. The core bet — attribution-by-construction

Our attribution is *post-hoc* (leave-one-out ablation): expensive and only weakly faithful. The strongest lever to fix it is to make credit a **structural property of inference** rather than something measured afterward: route to **per-contributor / per-domain LoRA adapters** so that *which adapter fired = who gets credited*. If a cheap, deterministic router picks the owning contributor, credit becomes cheap to compute, reproducible by anyone, and faithful by construction — closing the gap that post-hoc LOO and embedding-marginal cannot. Note 04 independently flags "MoE gating as a semivalue" as formally unclaimed, so this is both the product fix and the novelty.

- **New experiment:** `attribution-route` (notebook §10 / E7) — trains one adapter per contributor, routes queries with an embedding router, and reports routing accuracy + routed-vs-owning recall. First measurement of whether credit-by-routing is viable at small scale.
- **Corollary (re-weighting the roadmap):** distillation showed memorization risk, a forgetting tax, and non-zero entanglement (distill_attribution, OLMo). The sovereign endgame may lean **more on retrieval + small attributable adapters** and less on full-model retraining than the whitepaper currently implies. Worth revisiting §3.5's "RAG-as-foundation" framing once E7 has data.

## 3. The missing data component — a user-feedback ground truth

Embedding-resemblance marginal value *failed* as a value signal (§8.6). The highest-value signal we are **not** collecting is **explicit answer quality** — thumbs up/down, "did this help" — tied to the proof chain. That gives a downstream, human-judged ground truth to train and validate attribution against, replacing resemblance with actual usefulness. This single product component attacks the faithfulness crux harder than any estimator change. It should be the first thing built once the public instance has traffic (it is implied by §9's "structured logging of every (query, retrieval, answer)" but should be elevated from logging to an explicit feedback signal).

## 4. Incentives need sticks, not just carrots

Paying for cited contributions creates a clean attack: submit plausible-but-false content that ranks well and farm citations. Falsehood-bench + conflict-bench prove the model won't catch it, so the economic design needs **negative incentives**:

- **Stake / slashing** for contributors — skin in the game, forfeited when a contribution is later voted false.
- **Losable reputation** — today reputation (tier) only goes up; it must fall when your accepted contribution is overturned.

Without these, the kickback economy rewards confident falsehood.

## 5. Governance — two decisions our data already supports

- **Move from flat to reputation-weighted voting.** The governance simulation (governance-sim) showed flat (one-account-one-vote, shipping today) breaks at ~0.35× the honest electorate in sybils, while reputation-weighting holds to ~3.2× — a ~9× attacker-cost multiplier (≈ 1/sybil-weight). This is the quantitative case for weighting votes by earned reputation.
- **Gate retrieval by governance rank.** conflict-bench shows that surfacing competing true/false versions together corrupts the answer, and that grounding only on the upvoted version recovers correctness. Retrieval must only ever surface the current LIVE / highest-voted version — never competing versions simultaneously. This should be a hard architectural requirement, not an optimization.

## 6. Quantization (TurboQuant et al.) — a cost lever, not a pillar

Sovereignty means people can *self-host* the intelligence, and the main barrier is inference cost / hardware. Quantization (data-free, near-optimal-distortion vector quantization — TurboQuant is representative) directly lowers it, in two places already on the roadmap: **edge inference** (broadening who can host — the literal meaning of "publicly owned") and the deferred **dense-retrieval tier** (quantized embedding vectors / KV-cache). But it is commodity — everyone can quantize — so adopt it opportunistically, never as a differentiator. And it can erode the very things we measure, so it needs a guardrail:

- **New experiment:** `quant-bench` (notebook §5c) — runs the C2 grounding benchmark across quantization levels of the same model. If lift holds q4→q8, cheap edge self-hosting is safe; if it collapses at low bit-width, there's a precision floor for hosts.

## 7. What stays ruled out / deferred (not swept under the rug)

- **HDC/VSA, categorical, KG-routing as inference substrates** — already tried and archived ([archive/](../../../archive/)); correct call. Reopen only if a knowledge graph becomes a first-class *source* (not an inference shape).
- **Strategy-proof / ZK-verifiable attribution and cryptographic semirings** (notes 03–04) — genuine open research, high-risk. Pursue *only* through the attribution-by-construction thread, since that's the version that serves the product.
- **Collusion among reputable accounts and adaptive attacks** — the governance sim models a single worst-case lockstep-sybil adversary only. Named as open.
- **Shapley-vs-marginal credit deep-dive** — incremental on the existing Claim 5 result; deferred in favor of the feedback-ground-truth and routing threads, which are higher-leverage.

## 8. Priority order

1. **User-feedback data loop** → the faithful value ground truth everything depends on (product/data; needs traffic).
2. **Attribution-by-construction** (per-contributor adapter routing) → the core research bet (`attribution-route`, E7).
3. **Negative incentives** (stake/slash, losable reputation) → close the contribute-false-to-farm attack.
4. **Reputation-weighted + vote-gated governance** → already justified by governance-sim + conflict-bench; make them requirements.
5. **Quantization** → opportunistic, behind `quant-bench`. Not a pillar.

## Experiments added this round (in the GPU notebook)

| Command | Tests | Whitepaper link |
| --- | --- | --- |
| `retrieval-bench` | grounding through the real BM25 retriever with false distractors (the production read path) | C2 → C2b |
| `conflict-bench` | true vs false both retrieved: answer follows order, vote-gating recovers it | §4 governance ↔ §3 serving |
| `governance-sim` | sybil resistance of flat vs reputation-weighted voting (no model/DB) | §4.1 |
| `quant-bench` | does quantizing the base erode grounding lift (the cost lever) | §3.3 / §9 edge inference |
| `attribution-route` | attribution-by-construction: can cheap routing assign credit faithfully | Claim 5 / §8.9 |
