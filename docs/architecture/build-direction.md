# Build direction: from whitepaper findings to product & protocol

This is a decision record. It translates the experimental findings in
[WHITEPAPER.md](../WHITEPAPER.md) §8 into concrete build direction: what the
architecture must change, what we are inventing vs. integrating, and whether
DeQuorum ships as a user platform or a protocol other LLM providers strap on to.
It supersedes nothing in [research/notes/05](../research/notes/05-product-and-incentive-frontier.md);
it confirms that note's thesis with data and turns it into a work plan.

## Verdict

1. **The architecture is sound — no pivot.** The findings validate exactly the
   primitives the system was built on: signed contributions + proof chains,
   route → retrieve → ground, governance/voting, and an attribution ledger.
   Changes are component-level, dictated by the data, not a re-architecture.
2. **The product is the protocol; the platform is how it gets built.** Our
   defensible, novel value is the accountability + governance + valuation layer —
   not the model (a commodity that the experiments show is *defenseless* without
   governance) and not retrieval. We build the platform first as the reference
   implementation, corpus seed, and — critically — the user-feedback source the
   faithful payout measure requires; we draw protocol seams from day one.

## Findings → component changes

| Whitepaper finding | Build consequence | Status |
| --- | --- | --- |
| Grounding helps only where the base is ignorant (C2, +0.69) | Target domains outside base-model knowledge; don't compete on general Q&A | product/positioning |
| Model has no defense against false content; governance fixes it (C7) | Governance is the **correctness system**, gating both retrieval and (future) training — not optional moderation | architecture invariant |
| Vote-gated retrieval drives false adoption 0.83→0.125 (C7) | Serve only the current, highest-voted version of a claim | **already enforced** via supersede→status |
| Reputation voting → ~9× sybil resistance (C7); §4.1 specifies weighting | Apply tier/reputation **weights** in the live vote tally (currently flat `SUM(score)`) | **this change** |
| Contribution channel is an injection vector, 0.24→0.10 hardened (C7) | Instruction-data separation in the grounding prompt; sanitize contribution text upstream | **this change** (prompt) |
| Faithful credit needs a *quality* signal, not resemblance (C5, 0.89 vs 0.50) | Payout ledger uses a quality-grounded marginal (judge / user feedback) or routing-by-construction; capture per-answer feedback | feedback loop (next) |
| Citation set is cryptographically verifiable (C4) | Keep the proof chain as the audit + payout substrate; expose it | already shipped (`/verify`) |
| Distillation: attribution survives but quality gain unproven, costs real (C6) | RAG-first is the serving substrate; LoRA/ownership is a v2 tier — do not build the training pipeline now | deferred |

## Innovating vs. building on top of

**Integrate (commodity — do not reinvent):** open base models, inference runtime
(Ollama/vLLM), embeddings, BM25 / pgvector retrieval, LoRA (peft), FastAPI /
React / Postgres, quantization.

**Invent (the defensible core — all validated in §8):**
1. Verifiable per-contribution attribution + proof chains (`core/proof.py`,
   `core/ledger.py`, `core/crypto.py`).
2. The faithful credit/valuation measure — quality-grounded marginal +
   routing-by-construction (`attribution/`).
3. Governance-as-correctness — vote-gated retrieval + reputation-weighted voting
   bound to the grounding set (`review/`, `retrieval/`).
4. Attribution that survives distillation (`distill/`).
5. The economic loop tying proof chain → credit → payout.

Every innovation is in the accountability/governance/valuation layer; none is in
the model or retrieval. That is the signal that the product is a *layer*.

## Protocol seams

Core-protocol packages (callable by a third-party LLM provider) vs. app/infra:

- **Protocol core:** `core` (signing, proof chain, ledger), `identity`
  (contributors, tiers, keys), `knowledge` (contributions, lineage, status),
  `review` (voting, governance transitions), `retrieval` (vote-gated grounding),
  `attribution` (credit/payout).
- **App / infra (reference implementation):** `web`, `auth`, `chat`, `comments`,
  `routing`, `taxonomy`, `intake`, `db`, `inference`.

An external provider integrates by: (a) submitting/serving contributions through
`knowledge` + `review`, (b) grounding answers through `retrieval` (vote-gated),
(c) honoring the `core` proof chain, and (d) settling via `attribution`. The base
model and UI are theirs. The existing JSON API in `web/app.py` (contributions,
votes, lineages, `/verify`, chat stream) is the embryonic protocol surface; the
work is to make `attribution`/`ledger` and `retrieval` first-class services with
a documented contract (the `services-roadmap` already calls for extracting
`ledger`).

## Platform → protocol sequencing

1. **Platform now (reference + bootstrap + flywheel).** A working app is required
   to seed the corpus, prove the contract end-to-end, and — load-bearing — produce
   the per-answer user feedback the faithful valuation depends on (C5). You cannot
   run a quality-grounded payout without it.
2. **Protocol seams from day one.** Keep the core packages free of app/infra
   dependencies; expose `retrieval` (grounding) and `attribution` (credit) behind
   a stable API so integration is configuration, not a rewrite.
3. **Protocol as the product / mission vehicle.** The endgame is other providers
   strapping on: any LLM → attributed, governed, paid knowledge → users get paid →
   dependence on a few labs weakens. The integrator wedge is access to a governed,
   rights-cleared corpus of exactly the knowledge their base lacks (the C2 regime),
   plus verifiable sourcing and a turnkey contributor-compensation rail.

## Work plan & status

1. **Harden the grounding prompt** (`inference/pipeline.py`) — references are
   *data, not instructions*. From the injection result (0.24→0.10 at no recall
   cost). ✅ **done**
2. **Tier-weighted vote tally** (`review/tally.py`, `knowledge/store.py`) — apply
   the tier vote-weights (the ~9× sybil lever). ✅ **done**
3. **Serving provider abstraction** (`inference/provider.py`,
   `OpenAICompatibleModel`) — open model on a fast hosted endpoint, config-selected;
   dev/test stay free on Ollama. ✅ **done** (see [model-serving.md](model-serving.md))
4. **Per-answer feedback capture** (`chat` `message_feedback`, `POST …/feedback`) —
   the quality signal the faithful payout measure needs. ✅ **done**
5. **Settlement** (`economics/settlement.py`) — turn a query's revenue + grounding
   credits + feedback into a per-recipient payout split; conserves revenue,
   quality-gates the contributor pool. ✅ **done** (pure/tested)
6. **Wire settlement end-to-end** (`economics/ledger.py: settle_message`,
   `settlements` table, chat-store persistence) — reads an answer's grounding set +
   feedback, computes credits, and persists a per-query payout. ✅ **done**.
   `settle_message` takes injectable `credit_weights`; `marginal_credit_weights`
   computes the **faithful** weights (the §8.6 quality-grounded marginal — weights
   by the *judge* marginal, not resemblance: 0.89 vs 0.50). Equal-split is the
   default fallback. Remaining: a **trigger** (batch job or operator endpoint — not
   the chat hot path) wired with a production `score_answer` quality judge (or
   routing-by-construction once the training tier lands).
7. **Extract `attribution`/`ledger` + `retrieval` as documented services**
   (`dequorum.services`: `LedgerService`, `GroundingService`) — the first concrete
   protocol-surface step. ✅ **done**: in-process facades with a documented contract
   ([protocol-services.md](protocol-services.md)) — `LedgerService` is the
   services-roadmap's `ledger` audit boundary (settle / settle_faithful / get /
   journal); `GroundingService` is vote-gated retrieval behind a stable, impl-agnostic
   seam. Lifting either into a standalone service is wrapping the facade in transport.
   Remaining: route the reference `web` app through these facades, then the standalone
   `ledger` deploy + worker/Cloud Tasks settlement trigger (per `services-roadmap`).

## Deferred (intentionally)

- The **distillation / training tier**: sound as a long-horizon ownership play,
  but §8.7 shows no robust quality gain at feasible scale and real costs
  (entanglement, forgetting, memorization). RAG-first; revisit when the corpus is
  large and the economics justify the GPU budget.
- **Non-custodial signing, collusion-resistant governance, machine unlearning,
  dense/cross-encoder retrieval** — known gaps, scoped in §8.9–§8.10, not blocking.
