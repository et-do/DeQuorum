<!--
  Canonical source for the DeQuorum whitepaper.

  A second copy of the same prose lives at
    services/frontend/src/content/whitepaper.ts
  which the in-browser /whitepaper route renders. When editing the
  whitepaper, update BOTH files so the docs version and the web
  version stay in sync.
-->

# DeQuorum

### A crowdsourced, verifiable, contributor-owned foundational AI

**Whitepaper · v0.1 · June 2026**

---

## Abstract

DeQuorum is a foundational AI system designed from the ground up around a simple inversion of the current model: instead of a small handful of companies training AI on the world's knowledge and capturing the entire upside, **the people who contribute the knowledge, verify it, host the compute, and use the system all share in what it earns.**

The system is built in three layers. A **base language model** handles fluent reasoning. A **knowledge layer** of signed, peer-reviewed contributions grounds the model's answers in claims that real human contributors stand behind. Over time, the contribution layer's content is distilled into the base model itself through low-rank fine-tuning, so what began as retrieval becomes a trained, contributor-owned model — with the aim of matching closed alternatives on quality while remaining radically more transparent on attribution and economics.

Every claim in the system is cryptographically signed by its author, and every answer carries a verifiable proof chain showing which contributions shaped it. Revenue from a query is designed to flow back to the contributors, reviewers, and infrastructure providers whose work produced the answer, in proportion to a measured estimate of each contribution's value.

This paper states what DeQuorum is and why it is structured as it is, and reports what the v0.1 prototype does and does not yet establish. The accountability machinery — verifiable attribution and attribution that survives distillation — is demonstrated. The quality advantage of grounding is conditional, large only where the base model is ignorant; and the cheap value measure is at best weakly correlated with answer quality, leaving a faithful payout estimator as the central open problem (§8).

---

## 1. The problem

The current foundation-model market has three structural defects that compound:

**Closedness.** The largest models are trained by a small number of organizations on datasets the public cannot inspect. When such a model emits a claim, you have no principled way to ask "where did this come from?" — the lineage from training data to output token is a corporate asset, not a verifiable trail.

**Asymmetric capture.** The training data overwhelmingly comes from human-generated content: Wikipedia, Stack Overflow, scientific preprints, code repositories, public conversations, books. Almost none of the revenue these models generate flows back to those contributors. The value is extracted upstream — the data — and captured downstream — by the model operators.

**No accountability mechanism.** When a foundation model gets a factual claim wrong, the cost is paid by the user who acted on the wrong claim. There is no contributor whose reputation is on the line, no voting body that can mark a claim as obsolete, no review pipeline that can correct a class of errors at the source. The model is the source.

These three defects feed each other. Closedness makes accountability impossible, which makes asymmetric capture politically tolerable, which gives the operators the budget to keep training in private. DeQuorum exists because the alternative — open, accountable, and economically symmetric — is buildable.

---

## 2. The thesis

> **Foundation models don't have to be built and owned by a small number of corporations. The knowledge that goes into them already isn't.**

DeQuorum proposes that the right architecture for a publicly-useful AI looks like this:

- A **shared base model** anyone can run, swap, or fork.
- A **contribution pipeline** where any individual with verifiable domain knowledge can submit signed claims, and where the network's voting body — not a corporate trust-and-safety team — decides which claims get to ground the model's answers.
- A **revenue distribution layer** that follows attribution end-to-end: when a query earns revenue, the contributors whose facts shaped the answer, the reviewers who triaged them, and the compute hosts who served them all receive a calculated share.
- A **training feedback loop** that, over time, distills the contribution corpus directly into the model's weights via low-rank fine-tuning, so the network's knowledge ceases to be a retrieval-time augmentation and becomes the model itself.

The result is a system of accountability for the production of intelligence.

---

## 3. The architecture

### 3.1 The three-tier model

At inference time, a question travels through three concentric tiers, each fast-to-slow and broad-to-narrow:

```mermaid
flowchart BT
    Q([User question])
    T1["<b>Tier 1 — ROUTE</b><br/>~10ms · taxonomy-aware partition<br/>(category classifier)"]
    T2["<b>Tier 2 — RETRIEVE</b><br/>~100ms · BM25 + dense + cross-encoder<br/>+ authority filter (per-vote refresh)"]
    T3["<b>Tier 3 — TRAIN</b><br/>months/quarters · LoRA / full-model<br/>retraining on approved contributions"]
    A([Grounded answer])

    Q --> T1 --> T2 --> T3 --> A

    classDef tier fill:#0a0a0a,stroke:#888,color:#fafafa,rx:6,ry:6;
    classDef io fill:#fafafa,stroke:#888,color:#0a0a0a,rx:14,ry:14;
    class T1,T2,T3 tier;
    class Q,A io;
```

**Routing** picks which domain (or domains) the question concerns. A taxonomy of categories — the same taxonomy contributions are filed under — collapses the search space by 100×–1000×. A medical question never reaches the legal partition; a Python question never reaches the macroeconomics partition.

**Retrieval** finds the relevant contributions within the routed partition. The retrieval design combines three complementary signals (the lexical signal is the implemented baseline; see §3.4):

1. *Sparse* (BM25) retrieval, which catches exact-keyword matches that embeddings miss: entity names, identifiers, numbers, version strings.
2. *Dense* (vector ANN) retrieval, which catches paraphrase and conceptual similarity.
3. *Cross-encoder* reranking, which reads the question and each candidate passage *together* and scores how well one actually answers the other.

A final filter applies governance: only `LIVE` contributions surface, weighted by tally and contributor tier.

**Training** is the long game. As a category accumulates ~10,000 approved contributions, the network trains a domain-specific low-rank adapter (LoRA) on the `(question-like, contribution)` pairs. The adapter encodes that knowledge into the model's weights. Retrieval falls back to "contributions added since the last training cycle" — a much smaller set. Multiple adapters can be composed at inference time for cross-domain questions.

The architectural bet is that **the system that wins long-term is the one that learns from its contribution corpus, not just retrieves over it.** Retrieval is the way the network operates before it has earned the right to train. The training tier is the long-term moat — a moat the existing closed players cannot reach, because they do not own a verifiable contribution pipeline.

### 3.2 The contribution as the atomic unit

The atomic unit of value in DeQuorum is the **contribution**: a signed factual claim, attributed to a contributor and filed under a category in the curated taxonomy. Every contribution carries:

- **The claim itself** — natural-language text, with optional citations to external sources.
- **A cryptographic signature** — Ed25519 over the canonical bytes of the claim's contents. Anyone can verify, at any later time, that this exact text was authored by the holder of this exact key.
- **Lineage metadata** — version number, parent version, and a stable lineage identifier that survives edits. The history of a claim is reconstructible from any point.
- **Categorization** — which taxonomy node it belongs to.
- **A governance status** — see §4.

Once `LIVE`, a contribution is eligible to appear in any answer the network produces in its category. When it appears, the proof chain attached to the answer records *which* contributions grounded it, signed end-to-end so a downstream consumer can verify the attribution without trusting the operator.

### 3.3 Layering over a swappable base model

DeQuorum is not tied to any one base model. The system ships a **registry** of license-pure base models (Apache-2.0, MIT, Llama 3 Community License — the openness rule is encoded in the registry contract). Operators select which model the network is currently running. A documented model-swap procedure ensures any swap is one constant change away, with the same retrieval pipeline working unchanged on top.

This matters for two reasons. First, the open-model landscape is moving fast, and a network designed around a specific model would freeze its own ceiling at that model's release date. Second, the long-term distillation path (§3.5) needs to *replace* the base model with a contributor-trained one. A network that can't swap its model also can't take ownership of it.

### 3.4 Mathematical formalism

The three tiers each admit a short formal statement. The notation isn't load-bearing for the system — the implementations could swap algorithms within each tier — but writing it down makes the *boundary* between tiers explicit and the *failure modes* identifiable.

**Tier 1 — routing.** Let $\mathcal{C}$ be the set of taxonomy categories and let $\mathcal{E}_c \subseteq \mathcal{E}$ be the curated personas attached to category $c$. Given a query $q$, the routing layer computes

$$
\hat{c} = \mathop{\mathrm{argmax}}_{c \in \mathcal{C}} \; s_R(q, c)
$$

where $s_R$ is a routing score. In the current implementation $s_R$ is cosine similarity between a sentence-transformer embedding of $q$ and the centroid embedding of $c$'s category prompts. Routing is accepted iff $s_R(q, \hat{c}) \geq \tau_R$ for a threshold $\tau_R$ (currently $0.30$); otherwise the system falls through to the base assistant.

Because $|\mathcal{C}|$ is constant in the corpus size and retrieval (Tier 2) only ever runs on contributions filed under $\hat{c}$, routing collapses the per-query search space by a factor of $|\mathcal{D}| / |\mathcal{D}_{\hat{c}}|$, where $\mathcal{D}$ is the full contribution corpus and $\mathcal{D}_c$ is its partition under category $c$. For a uniform taxonomy this equals the partition factor $|\mathcal{C}|$; for the power-law taxonomies real-world domains produce, the factor is larger in the head and smaller in the tail.

**Tier 2 — retrieval.** Within partition $\mathcal{D}_{\hat{c}}$, the system computes two scores per candidate contribution $d$:

$$
s_{\text{sparse}}(q, d) = \text{BM25}(q, d), \qquad s_{\text{dense}}(q, d) = \frac{\langle \phi(q), \phi(d) \rangle}{\|\phi(q)\| \, \|\phi(d)\|}
$$

where $\phi$ is the sentence embedder. The fused score combines them via Reciprocal Rank Fusion:

$$
s_{\text{fused}}(q, d) = \frac{1}{k + r_{\text{sparse}}(d)} + \frac{1}{k + r_{\text{dense}}(d)}
$$

with $k = 60$ a smoothing constant and $r_*(d)$ the rank of $d$ under each scorer. The top-50 by $s_{\text{fused}}$ then pass through a cross-encoder reranker $g(q, d) \in \mathbb{R}$ that reads $(q, d)$ jointly, producing the final top-$K$ retrieval set $R_K(q)$.

An authority filter applies governance: $R_K(q)$ is restricted to contributions with `status = LIVE`, `version = current`, $\text{tally}(d) \geq \tau_T$, and $\text{tier}(\text{author}(d)) \geq \tau_A$. The `version = current` restriction is load-bearing, not cosmetic: §8.8 shows that surfacing competing versions of a claim side by side lets the model adopt a falsehood, while gating to the single governance-promoted version drives that to zero. The augmented prompt sent to the base model is then

$$
\text{prompt}(q) = \text{persona}(\hat{c}) \;\|\; \text{format}\bigl(R_K(q)\bigr) \;\|\; q
$$

where $\|$ denotes concatenation. The base model's generation conditions on this concatenation; the proof chain (§4.2) records the elements of $R_K(q)$ as the contributions that grounded the answer.

The scoring stack above defines the retrieval design. The present implementation instantiates the lexical scorer $s_{\text{sparse}}$ together with the governance filter; the dense and cross-encoder stages are specified here as the design's intended form. The interface to the rest of the system is identical in either case — a governed top-$K$ set $R_K(q)$ that feeds both the prompt and the proof chain — so the results of §8 are independent of which scorers are active.

**Tier 3 — training.** Given a corpus $\mathcal{D}_c^{\text{live}}$ of approved contributions in category $c$, the system constructs training pairs $(q_i, a_i)_{i=1}^N$ by (a) sampling existing query–answer logs whose retrieval intersected $\mathcal{D}_c^{\text{live}}$, and (b) synthesizing question-like prompts from each $d \in \mathcal{D}_c^{\text{live}}$ via a templated inverse. A LoRA adapter is then fine-tuned on the base model $M$.

LoRA replaces a weight matrix $W \in \mathbb{R}^{m \times n}$ in $M$ with $W + BA$, where $B \in \mathbb{R}^{m \times r}$ and $A \in \mathbb{R}^{r \times n}$ are learned and $r \ll \min(m, n)$. The total trainable parameter count is $r(m + n)$ instead of $mn$ — typically a 100–1000× reduction. Multiple adapters $\{B_c A_c\}_{c}$ trained on different categories can be composed at inference time:

$$
W' = W + \sum_{c \in \mathcal{A}} \alpha_c B_c A_c
$$

for active-adapter set $\mathcal{A}$ and per-adapter scaling $\alpha_c$.

A retrieval-to-training transition is justified for category $c$ once $|\mathcal{D}_c^{\text{live}}|$ exceeds an empirical threshold (≈ $10^4$ in our current estimate). After the transition, retrieval inside the partition continues to serve "fresh contributions added since the last training cycle" — a much smaller, lower-latency set.

**Proof-chain integrity.** Every signed entity (contribution, vote, comment, triage verdict) carries a signature $\sigma_e = \mathrm{Sign}_{k}\bigl(H(\mathrm{payload}_e)\bigr)$ over the canonical bytes of its payload, where $k$ is the actor's Ed25519 signing key and $H$ is BLAKE2b. The proof chain attached to an answer is the ordered list

$$
\Pi(a) = \bigl[\sigma_{d_1}, \sigma_{d_2}, \dots, \sigma_{d_K}, \sigma_{a}\bigr]
$$

where $d_1, \dots, d_K \in R_K(q)$ and $\sigma_a$ is the operator's signature over the produced answer. Verification of $\Pi(a)$ requires only the public keys of the contributors and the operator — no trust in the storage layer. The ledger payout computation (§5) iterates exactly over $\Pi(a)$, so the same data structure that lets an end user audit an answer also drives revenue distribution.

**Tier-weighted voting.** Let $V(d) = \{v_1, \dots, v_n\}$ be the votes cast on contribution $d$, each $v_i \in \{-1, 0, +1\}$ submitted by contributor $u_i$ at tier $t_i$. The effective tally is

$$
T(d) = \sum_{i=1}^n w(t_i) \cdot v_i, \qquad w: \mathrm{Tier} \to \mathbb{R}_{\geq 0}
$$

with $w$ the tier-weight map of §4.1. Promotion to `LIVE` requires $T(d) \geq \tau_{\text{approve}}$; rejection requires $T(d) \leq -\tau_{\text{reject}}$; veto is implemented as an extra term in $w$ that is *only* applied during the triage stage. Decoupling triage-weight from vote-weight is the formal expression of the "curators unblock; community decides" rule.

### 3.5 From retrieval to training

Once the contribution pipeline produces enough high-consensus content in a domain — empirically, on the order of $10^4$ approved claims — the next step is to fine-tune. A LoRA adapter is small (a few percent of the base model's parameters), cheap to train (single-GPU-hours), and composable: multiple adapters stack at inference time, so a question that spans medicine and law can light up both adapters at once.

This is where DeQuorum diverges from every existing RAG product. RAG-as-a-feature is a retrieval-time augmentation: the model knows nothing, and the augmentation tells it. RAG-as-a-foundation, plus a contribution pipeline, plus distillation, becomes a *trained model* that the network owns. The retrieval layer never goes away — it serves fresh contributions until the next training cycle — but the model itself starts carrying the network's knowledge.

The contribution corpus, the trained adapters, and the proof chains tying them to specific contributors stay in the open. No competitor with a closed pipeline can reach the same place, because none of them owns a contribution network.

---

## 4. Governance: how contributions become law

A contribution is just text until the network has decided whether to trust it. DeQuorum runs every contribution through a four-stage lifecycle, with a different group of participants holding power at each stage and a different accountability mechanism at each transition.

```mermaid
flowchart LR
    D([DRAFTED])
    T([IN_TRIAGE])
    V([IN_VOTE])
    L([LIVE])
    R([REJECTED])

    D -- "submit (author)" --> T
    T -- "approve-to-vote<br/>(2 curators · tier ≥ 3)" --> V
    T -- "reject" --> R
    V -- "tally ≥ τ_approve<br/>(broader community)" --> L
    V -- "tally ≤ −τ_reject" --> R

    classDef live fill:#0a0a0a,stroke:#888,color:#fafafa,rx:14,ry:14;
    classDef rej fill:#fafafa,stroke:#888,color:#0a0a0a,rx:14,ry:14;
    class D,T,V live;
    class L,R rej;
```

1. **Submit.** Anyone with a verified identity and an active agreement can submit. The contribution carries the contributor's signature.
2. **Triage.** Reviewers with sufficient tier read, discuss, and request edits in a comment-thread interface that mirrors a code-review tool. They vote *approve-to-vote*, *reject*, or *abstain*. Two approvals with no curator veto move the contribution to the next stage.
3. **Vote.** The broader community — a wider pool of tier-1+ voters — assesses whether the triaged contribution actually deserves to ground answers. Vote weight is tier-weighted (per §4.1). A threshold tally promotes to `LIVE`; a threshold negative tally rejects.
4. **Live.** Eligible to appear in any answer. Stays live until a newer version supersedes it.

Three side flows attach:

- **Comments** thread under every contribution; triage rationale, review discussion, and post-acceptance clarification share one signed comment model.
- **Edit requests** are pull-request-style proposed changes: a reviewer drafts a new version and submits it as a suggestion, which the original author accepts — creating a new lineage version with attribution preserved — or declines.
- A **public activity feed** surfaces submissions, triage, votes, and acceptances across the network, both as external evidence of the governance process and as a reading surface for non-contributing users.

### 4.1 Tier-weighted voting

A static one-vote-one-account model is sybil-vulnerable. DeQuorum solves this with a tier ladder:

| Tier | Name | How earned | Vote weight | Submission cap |
| --- | --- | --- | --- | --- |
| 0 | Anonymous | default for new accounts | 0 (recorded, not counted) | 0 |
| 1 | Email Verified | verified email address | 0 (recorded, not counted) | 5/day |
| 2 | Social Proof | verifiable social handle | 1.0 | 50/day |
| 3 | Credentialed / Reputation | W3C VC OR sustained consensus history | 2.5 | 500/day |
| 4 | Curator | elected by the community | 1.0, but *veto power* in triage | 10,000/day |

The asymmetry is intentional. **Curators wield veto in triage but have *less* weight in the community vote.** The function of a curator is to keep the queue *moving* — to reject obvious noise, request edits, unblock discussion. The function of the community vote is to keep the network *correct*. Conflating those roles into a single weighting collapses the system into oligarchy or into noise.

The tier weighting is the system's sybil defense, and §8.8 quantifies why it matters: a flat one-account-one-vote tally is breached once an attacker fields sybils numbering ~0.35× the honest electorate, whereas weighting by earned reputation — the effect the ladder encodes, since new accounts at tiers 0–1 carry zero weight — raises that break-in point ~9×. Because an approved-but-false contribution will be repeated by the model (§8.8), this margin directly bounds how much falsehood can ever reach the grounding corpus.

### 4.2 Every signature, recorded forever

The proof chain is not a UI nicety. The same `Signature` primitive that signs contributions also signs comments, votes, triage verdicts, and edit requests. Every state transition has a record of who triggered it, and that record is cryptographically tied to the actor's keypair. The result is a system where the question "who decided this contribution gets to ground answers?" has a verifiable, auditable answer.

This matters at three different scales:

- **Per-query**: an end user reading an answer can demand to see the chain that produced it.
- **Per-contribution**: an external auditor can trace a contribution from submission through triage through vote to its current `LIVE` status, with every reviewer's signature.
- **Per-distillation**: when a contribution makes it into a LoRA adapter or a full retraining cycle, the cryptographic lineage from contributor to model weight is preserved in the network's ledger.

This is realized in the implementation. Contributions are signed with Ed25519 over the BLAKE2b hash of the canonical payload, and the API exposes `GET /v1/contributions/{id}/verify`, which rebuilds the signed payload from stored fields and reports two independent checks: content integrity (the stored text still hashes to the signed payload and identifier) and signature validity (the signature verifies against the contributor's published public key). The endpoint is unauthenticated and returns the public key and signature, so a third party can reproduce the check without trusting the operator; altering either the stored content or the signature causes verification to fail. The empirical treatment is in §8.5.

The scope of this guarantee is bounded by key custody. Contributor keys are at present derived server-side from the authenticated identity, so the scheme guarantees content integrity and public checkability against the published key, but not resistance to forgery by the operator, which could re-derive a key. Non-custodial signing with client-held keys is required for that stronger property and is on the roadmap (§9). We state the boundary explicitly rather than imply a guarantee the implementation does not yet provide.

---

## 5. Economics: the kickback model

DeQuorum's economic premise is straightforward: **revenue flows to the participants whose work produced the value.**

When a query against the network earns money — through subscription, per-query billing, or aggregate sponsorship — that revenue is split according to a transparent ledger:

| Recipient | What earns them a share | Why |
| --- | --- | --- |
| **Contributor** | their contributions grounded the answer | the knowledge layer is what makes the answer trustworthy |
| **Reviewer** | their triage and votes moved the relevant contributions to `LIVE` | review is itself unpaid work in every comparable system; DeQuorum pays it |
| **Compute host** | their hardware served the inference | running models costs real money and must be sustainable for non-corporate operators |
| **Network operator** | infrastructure beyond compute (storage, identity, payments, governance tooling) | the connective tissue has real costs |
| **Treasury** | research, dispute resolution, infrastructure reserves | the network needs a slow-money pool for things no individual share can fund |

The exact split is governance-tunable. The principle is fixed: **every role that contributed to the answer is named on the ledger.** Payouts use conventional rails (Stripe ACH at modest scale; the protocol is payment-rail-agnostic). A contributor whose contribution is cited in 100,000 queries receives a real, calculated payout — not a "thanks for your contribution" badge.

The kickback model is not an afterthought to the architecture. It is *why* the architecture is structured the way it is. The cryptographic signatures, the proof chain, the lineage tracking — all of these are load-bearing for revenue distribution. The audit trail that an end user uses to verify an answer is the same audit trail that the ledger uses to compute payouts. There is no separate "monetization layer" because the entire system is the monetization layer.

### 5.1 Unit economics

A redistribution model is only credible if the underlying query is profitable enough to redistribute from. We therefore separate two things the §5 split conflates: the *real costs* the network must cover (compute, paid to a host; fixed infrastructure, paid to the operator) and the *redistribution* the model exists to deliver (the contributor, reviewer, and treasury shares). The network is viable only when each role's revenue share covers its real cost; the remainder is what actually reaches the people who supplied the knowledge.

The model below is per answered query, and every figure is an explicit input. The reference point uses a ~7B open model on commodity GPU pricing, a typical grounded prompt, and a modest per-query price:

| Quantity | Value | Basis |
| --- | ---: | --- |
| Tokens (in / out) | 1500 / 300 | persona + 3 contributions + question; short answer |
| Inference cost | \$0.00014 | \$0.05 / \$0.20 per 1M input/output tokens |
| Infra cost / query | \$0.00040 | \$400/month over 1M queries |
| **Total real cost** | **\$0.00056** | inference + infra + a \$0.00002 embedding call |
| Revenue / query | \$0.01000 | per-query price (or subscription-amortized) |
| Host margin | +\$0.00234 | 25% share − compute |
| Operator margin | +\$0.00110 | 15% share − infra |
| **To contributors** | **\$0.00400** | 40% share — **\$4.00 per 1,000 cited queries** |

Two results matter for the proof-of-concept. First, at this price point the model **closes**: both cost-bearing roles run a positive margin and roughly \$6 of every \$10 in revenue is redistributed to knowledge providers, with \$4 reaching contributors directly. Second, viability is **volume-dependent** — fixed infrastructure dominates at low query counts, and the break-even price (the lowest price at which the host and operator shares still cover their real costs) is ≈ \$0.0027 per query at one million queries per month but rises sharply below that. The economic claim is therefore conditional, not unconditional: the kickback model is sound *at scale and at a defensible price*, and the model makes the exact threshold explicit rather than assumed.

The sensitivities that move the result most are the output-token count and the served model size (both scale inference cost), and query volume (which amortizes fixed infra). All are inputs to `dequorum cost-model`, so the analysis can be re-run against measured production figures as they become available.

---

## 6. Open foundations

DeQuorum is open source under Apache 2.0, and the production stack is intentionally open-license top to bottom. This is a load-bearing design choice, not a stylistic one: a system whose claim to legitimacy is *contributor accountability* cannot itself rest on an opaque substrate. Every component below was selected so that anyone who wants to verify, fork, or operate a DeQuorum instance can do so without asking permission of a closed vendor.

| Layer | Component | License |
| --- | --- | --- |
| Base LLMs | Qwen 2.5 (default), Mistral 7B, Phi-4, Granite 3.1, Llama 3 family | Apache 2.0 / MIT / Llama 3 Community License (gated by the registry's openness rule) |
| Inference server | [Ollama](https://ollama.com/) | MIT |
| App / API | [FastAPI](https://fastapi.tiangolo.com/), [uvicorn](https://www.uvicorn.org/), [psycopg 3](https://www.psycopg.org/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/) | MIT / BSD |
| Retrieval | [sentence-transformers](https://www.sbert.net/), [Hugging Face Transformers](https://huggingface.co/docs/transformers) | Apache 2.0 |
| Database | [PostgreSQL 16](https://www.postgresql.org/) | PostgreSQL License (BSD-style) |
| Frontend | [React](https://react.dev/), [Vite](https://vitejs.dev/), [TanStack Router / Query](https://tanstack.com/), [Tailwind](https://tailwindcss.com/) | MIT |
| Proxy | [Caddy](https://caddyserver.com/) | Apache 2.0 |

The base-model registry encodes the openness rule directly. A profile cannot be the default unless its license is in the `OPEN_LICENSES` set. This rule applies to every swap, every adapter, every successor model — there is no path by which DeQuorum's serving substrate becomes proprietary by accident.

**The one exception** is Firebase Auth, used today as the credential surface because solving email + social signin is not the problem this project sets out to solve. It is wrapped behind a small `dequorum.auth` module so that swapping to an open identity provider (Supabase Auth, Ory Kratos, Auth.js, or self-hosted) is a one-file change. Making that swap before any external launch is on the v0.2 milestone list — the goal state is zero closed dependencies in the critical path.

The openness commitment extends to the network's outputs as well: the contribution corpus, the proof chains, the trained LoRA adapters, and the per-query attribution records all stay in the open. The network's value compounds *because* its inputs and outputs are inspectable. A closed contribution pipeline would invalidate the accountability claim that distinguishes DeQuorum from the closed alternatives it argues against.

---

## 7. Why this is novel

A comparison against the most-cited adjacent systems makes the differentiation concrete:

| System | Open weights? | Contribution pipeline? | Verifiable attribution? | Revenue to contributors? |
| --- | --- | --- | --- | --- |
| OpenAI / Anthropic | No | No | No | No |
| Llama (Meta) | Yes | No | No | No |
| Wikipedia | (no AI) | Yes | Per-edit, not per-claim | No |
| Stack Overflow | (no AI) | Yes | Yes | No (data was sold to AI companies; contributors paid nothing) |
| HuggingFace | Yes (model hosting) | No | No | No |
| Perplexity / You.com | No (model) | No | Inline web citations | No |
| **DeQuorum** | **Yes** | **Yes** | **Per-claim, signed, lineaged** | **Yes** |

DeQuorum is not the first system to do any of these things in isolation. It is, to our knowledge, **the first to combine all four into a single end-to-end system**, where each property reinforces the others — open weights enable independent verification; the contribution pipeline produces the data the weights will eventually train on; verifiable attribution makes payouts computable; payouts incentivize the contribution pipeline.

The closest comparable in spirit is Wikipedia, but Wikipedia famously has no economic mechanism, no AI integration, and no architecture for distilling its content into a model the contributors own. The closest comparable in technology is Perplexity, but Perplexity has no contribution pipeline — it cites web pages, not contributors, and the web pages were not written for Perplexity. DeQuorum is what happens when those two threads — the contributor commons and the AI inference layer — are designed together, from scratch, with the economic mechanism load-bearing in the architecture.

---

## 8. Experimental validation

The architectural claims of §3 are testable, and this section reports the results, organized as experimental design, results per claim, and limitations. Every experiment is reproducible from the reference implementation; the exact commands and full per-item records are in [docs/benchmarks/](benchmarks/), and the construction-level properties are encoded as deterministic tests. Results are reported at the scale the present seed corpus and inference budget allow; sample sizes are stated throughout and their consequences discussed in §8.9.

### 8.1 Experimental design

Two benchmark surfaces are reported, because the cost profile is very different:

- **Routing-only** (fast — N=127). Tests just the routing layer: does the system pick a qualified category? Doesn't generate answers, so it doesn't pay Ollama latency. Scales to hundreds of questions in seconds; full report in [docs/benchmarks/routebench.md](benchmarks/routebench.md).
- **Full-pipeline** (slow — N=15). Vanilla vs DeQuorum-full vs DeQuorum-no-retrieval, with real model generation. Bound by Ollama latency at ~30–60 seconds per query × 3 conditions, so the practical N is small. Side-by-side answers in [docs/benchmarks/qwen-bench.md](benchmarks/qwen-bench.md).

**Buckets.** Question pool composition for the routing-only benchmark:

| Bucket | N | Source | Tests |
| --- | ---: | --- | --- |
| `seeded` | 5 | Hand-curated, matches existing contributions | Lift over base model when grounding exists |
| `seeded_generated` | 60 | Template-filled from category specialty tags (12 per category × 5 categories) | Routing scales beyond hand-curated questions |
| `unseeded` | 5 | In-domain, no specific contribution | Graceful degradation to persona-only |
| `out_of_domain` | 5 | Hand-curated topics no category covers | Refusal vs hallucination |
| `ood_mmlu_like` | 42 | MMLU-shaped questions across 42 OOD subjects (anatomy, law, history, …) | Refusal at scale across hard-science/social-science/humanities |
| `ood_truthfulqa_like` | 10 | TruthfulQA-shaped questions where vanilla models commonly hallucinate | Refusal on tricky factual claims |

Full-pipeline benchmark uses the 15 hand-curated questions (5 per `seeded` / `unseeded` / `out_of_domain` bucket).

**Conditions** (full-pipeline only; routing-only collapses to one). Each question is run three ways for an apples-to-apples comparison:

- **A. Vanilla.** Bare base model, generic system prompt. No DeQuorum at all.
- **B. DeQuorum full.** Route → retrieve → augmented category prompt → signed proof chain.
- **C. DeQuorum no-retrieval.** Router + category persona only; retrieval is skipped. This isolates the contribution of the *retrieval* layer (B vs C) from the contribution of the *routing/persona* layer (C vs A).

**Setup.** Base model: Qwen 2.5 Coder 7B (Apache-2.0) via Ollama. Router: embedding-based with acceptance threshold $\tau_R = 0.30$, selected by the sweep in §8.2.1. Composition: pick-best. Seed corpus: 25 peer-approved contributions across five routable categories (python-typing, python-async, python-packaging, rust-ownership, http-protocol). Each result row links to the corresponding question record in the benchmark reports.

**A third surface: the feasibility and safety suite.** Several claims below concern mechanisms the two surfaces above cannot isolate — grounding on knowledge the base lacks (§8.3), propagation of a false contribution (§8.8), conflict between contradictory contributions (§8.8), sybil resistance of the vote (§8.8), and the survival of attribution through distillation (§8.7). These run as self-contained benchmarks with no database and no production corpus, on a single GPU, so each isolates one mechanism without the confounds of corpus scale or retrieval tuning. They use an eight-fact *invented* corpus — specific, plausible, but fictional, so no pretrained model can have memorized it — and, where training is involved, low-rank adapters over open base models (Qwen 2.5 0.5B, and the open-data OLMo-2 1B). Commands and full records are in [docs/benchmarks/](benchmarks/).

**The grader is validated before it is used.** Every quality number in this section is only as trustworthy as the grader that produced it, so both graders are tested directly: each scores a known-correct answer and a plausible-but-false variant of every invented fact against the true gold. The keyword grader separates correct from plausibly-wrong by $+0.71$ (pairwise accuracy $0.94$) and the LLM grader by $+0.73$ (pairwise accuracy $1.00$); a grader unable to tell the two apart would make every downstream number suspect, and neither is. The LLM grader is the less brittle of the two and is preferred wherever the distinction is subtle. Full record in [docs/benchmarks/judge.md](benchmarks/judge.md).

### 8.2 Claim 1 — Routing collapses the search space without missing the right domain

Routing decisions across all 127 questions at the production threshold $\tau_R = 0.30$:

| Bucket | N | Accept rate | Mean score | Expected | Verdict |
| --- | ---: | ---: | ---: | --- | --- |
| `seeded` | 5 | **100%** | 0.56 | 100% | ✓ |
| `seeded_generated` | 60 | **100%** | 0.59 | 100% | ✓ |
| `unseeded` | 5 | **100%** | 0.50 | 100% (correct family) | ✓ |
| `out_of_domain` | 5 | **0%** | — | 0% | ✓ |
| `ood_mmlu_like` | 42 | **0%** | — | 0% | ✓ |
| `ood_truthfulqa_like` | 10 | **0%** | — | 0% | ✓ |

Full per-question detail in [docs/benchmarks/routebench.md](benchmarks/routebench.md). The accept rate is exactly what the architectural claim predicted: 100% on every in-domain bucket, 0% on every OOD bucket.

The interesting finding is that this clean separation required *tightening* the routing threshold from the original $0.18$ to $0.30$. We arrived there via the threshold sweep below.

#### 8.2.1 Threshold sweep

A threshold tuned against the 15 hand-curated questions alone ($\tau_R = 0.18$) leaks on the 42-question MMLU-shaped out-of-domain pool. Sweeping $\tau_R$ locates the operating point:

| $\tau_R$ | OOD MMLU accept rate | Seeded accept rate | Seeded-generated accept rate |
| ---: | ---: | ---: | ---: |
| 0.18 | 19% (8 / 42 leaked) | 100% | 100% |
| 0.25 | 2% (1 / 42) | 100% | 100% |
| **0.30** (production) | **0%** | 100% | 100% |
| 0.35 | 0% | 100% | 100% |

The eight leaks at $\tau_R = 0.18$ are misroutings in which MMLU questions such as *"What are the first-line antibiotics for community-acquired pneumonia?"* score 0.20 against `python-packaging`: the embedder responds to English structural patterns ("first-line X for Y?") rather than topical content. At $\tau_R = 0.30$ the leakage is eliminated with no loss of true positives. The leak is invisible at the 15-question scale and unambiguous across 42 stratified MMLU subjects — the reason the routing-only benchmark uses the larger pool.

#### 8.2.2 Search-space reduction

At $|\mathcal{C}| = 5$ routable categories in this configuration, routing collapses retrieval to one-fifth of the corpus per accepted query — an empirical $5\times$ reduction. The architecture predicts that this factor grows with taxonomy size; confirming the growth requires a larger set of routable categories than the present corpus provides (§8.10).

### 8.3 Claim 2 — Contributor-sourced grounding produces measurably different answers

Conditions A, B, and C are compared on the five seeded queries, scored by gold-fact recall:

| Condition | Mean gold-fact recall |
| --- | ---: |
| A — vanilla (bare base model) | 0.78 |
| B — DeQuorum full (route → retrieve → ground) | 0.80 |
| C — router + persona, retrieval suppressed | 0.43 |

The result does not support a simple "grounding always wins" reading, and is reported as measured. Full grounding edges the bare base model (0.80 vs 0.78) but only narrowly, and the persona-only condition underperforms the base outright (0.43). The cause is headroom: the five seeded facts — generator typing, asyncio completion semantics, `ParamSpec`, QUIC-over-UDP, Rust ownership — lie largely within a 7B code model's existing knowledge, so retrieval has little to add on a recall measure, while the persona prompt's stylistic framing can suppress a fact the base would otherwise state plainly. The measurable advantage of grounding is therefore concentrated where the base model *lacks* the knowledge — the regime isolated in §8.7, where a model scoring 0.0 on a fact reaches 0.5 once the contribution is supplied.

The conditions nonetheless produce distinguishable answers. Only condition B reproduces the exact contribution wording — the `Generator[Y, S, R]` formulation, the QUIC-over-UDP phrasing — which a keyword-recall measure does not fully credit:

| Seeded query | A. Vanilla output | B. DeQuorum full | C. No-retrieval |
| --- | --- | --- | --- |
| [Generator typing — `Generator[int, None, str]`?](benchmarks/qwen-bench.md#seeded-1-how-do-i-type-a-generator-function-in-python-that-yields-ints-and-returns-a-str) | Gives a runnable but incorrect example (`yield` + `return` semantics conflated). | Returns the exact `Generator[Y, S, R]` annotation with `int / None / str` slots correctly identified. | Correctly states the `Generator[…]` form (persona alone helps). |
| [asyncio.gather vs asyncio.wait](benchmarks/qwen-bench.md#seeded-2-whats-the-difference-between-asynciogather-and-asynciowait) | Conflates completion semantics in one direction. | Explains: gather collects results in order, wait returns (done, pending) sets; cancellation differs. | Partial: identifies the API surface but not the completion contract. |
| [ParamSpec usage (PEP 612)](benchmarks/qwen-bench.md#seeded-3-how-do-i-use-paramspec-to-forward-decorator-signatures) | Vague description, doesn't mention `ParamSpec`. | Direct, correct example with `P = ParamSpec("P")` and `Callable[P, R]`. | Names `ParamSpec` but example is approximate. |
| [HTTP/3 transport](benchmarks/qwen-bench.md#seeded-4-what-protocol-does-http3-run-on) | Says "UDP" without mentioning QUIC explicitly. | "QUIC, which runs on UDP" — the exact fact in the retrieved contribution. | Says "QUIC on UDP" because the persona surfaces it. |
| [Rust ownership rules](benchmarks/qwen-bench.md#seeded-5-what-are-rusts-ownership-rules) | General "one owner" gesture, no `Drop` semantics. | Lists the three rules + `Drop` invocation on scope exit. | Lists the three rules, slightly less crisp on `Drop`. |

The qualitative reads above are a single reviewer's, and the keyword-recall measure tempers them: the persona-only column in particular reads better than its 0.43 recall, because gold-fact recall rewards the plain statement of a fact over a well-shaped but hedged answer.

The decisive difference between these conditions is structural rather than in content quality: every B-condition answer carries a signature chain — one signature per retrieved contribution plus the operator's — while A and C carry none. That property, not the recall margin, is what makes attribution and payouts (§5, §8.5–§8.6) computable at all.

**Grounding on knowledge the base lacks.** The narrow margin above is a consequence of headroom, not of grounding being weak. To isolate the effect, a second experiment uses eight *invented* facts — specific and plausible but fictional, so no pretrained model can have memorized them — each posed to the bare model and again with the fact supplied as a reference (full table in [docs/benchmarks/novelty.md](benchmarks/novelty.md)):

| Condition | Mean gold-fact recall |
| --- | ---: |
| Base model | 0.23 |
| Grounded | 0.92 |

Grounding lifts recall from 0.23 to 0.92 — a **+0.69** gain. The residual 0.23 in the base condition is the coarse keyword judge crediting generic tokens the model guesses (e.g. "Byzantine", "associativity"); on the purely invented terms (*melanoquin*, the Cindervault re-sharding rule) the base scores zero. The contrast with the seeded result is the finding for Claim 2: grounding produces a large, measurable gain precisely where the base model is ignorant, and little where it is not. A production network's value therefore depends on sourcing contributions *outside* the base model's training distribution — recent, niche, proprietary, or otherwise unmemorized knowledge — which is also where the contributor commons has its natural advantage.

**The production read path: grounding through retrieval, not an oracle.** The $+0.69$ figure is an *oracle* result — the model is handed the exact correct note. Production never does that: it retrieves from a corpus of many contributions and grounds on the top-$k$. The gap between the two is the loss the serving path introduces, and it is not small. Repeating the invented-fact experiment through the real BM25 retriever over a corpus seeded with a plausible *false* variant of every fact (full record in [docs/benchmarks/retrieval.md](benchmarks/retrieval.md)):

| Read path | True-note hit@k | Grounded recall | False-claim adoption |
| --- | ---: | ---: | ---: |
| Oracle (exact note) | — | 0.92 | — |
| Retrieval, top-1 | 0.50 | 0.56 | 0.44 |
| Retrieval, top-3 / top-5 | 1.00 | 0.62 | **0.75** |

Two findings, both consequential. First, retrieved-grounded recall (0.62) sits roughly a third below the oracle (0.92): BM25 recovers the true note but does not rank it cleanly above its lexically-similar false twin, so the answer is grounded on a noisier context. Second, and more important, the false twin is co-retrieved on essentially every query at $k \geq 3$, and the model then states the false claim **75%** of the time. Counter-intuitively, retrieving *more* is *less* safe here: at top-1 the model sometimes sees only the true note (false adoption 0.44), whereas at top-3 both are always present (0.75). The implication is sharp — the grounding benefit of Claim 2 is real but the serving path, not the model, decides whether a retrieved falsehood reaches the answer. That hand-off is the subject of Claim 7 (§8.8).

### 8.4 Claim 3 — Refusal over hallucination on out-of-domain questions

The honesty-about-limits claim says the system should refuse when no category is qualified, rather than emitting plausible-sounding output from the base model.

| Out-of-domain query | A. Vanilla | B. DeQuorum full |
| --- | --- | --- |
| [Who won the 2022 FIFA World Cup?](benchmarks/qwen-bench.md#out_of_domain-1-who-won-the-2022-fifa-world-cup) | Answers (Argentina, correct). | Refuses: "no qualified category above the routing threshold." |
| [Best way to braise short ribs?](benchmarks/qwen-bench.md#out_of_domain-2-whats-the-best-way-to-braise-short-ribs) | Answers (long recipe). | Refuses with same message. |
| [Main causes of WWI?](benchmarks/qwen-bench.md#out_of_domain-3-what-were-the-main-causes-of-world-war-i) | Answers (multi-paragraph). | Refuses. |
| [How do I treat a bee sting?](benchmarks/qwen-bench.md#out_of_domain-4-how-do-i-treat-a-bee-sting) | Answers (medical advice). | Refuses. |
| [Chemical formula for table salt?](benchmarks/qwen-bench.md#out_of_domain-5-whats-the-chemical-formula-for-table-salt) | Answers (NaCl). | Refuses. |

Refusal rate: **5/5 (100%)** for DeQuorum on out-of-domain; **0/5 (0%)** for the vanilla baseline.

This is the safety-relevant axis. A vanilla foundation model has no principled mechanism for "I shouldn't answer this." DeQuorum's routing threshold is that mechanism. The bee-sting case in particular is the kind of question where confidently-wrong base-model output has real-world cost; the routing layer's refusal moves that cost off the user.

The economic interpretation of refusal is non-trivial. In a query-billed network, the operator earns nothing from a refused query. The system therefore has a structural incentive *not* to refuse — and yet, by design, it does. This is the same alignment pressure that makes "calibrated confidence" hard for closed-model operators; DeQuorum encodes it directly in the routing math.

### 8.5 Claim 4 — Attribution is cryptographically verifiable

Accountability (§1, §4.2) requires that attribution be checkable rather than asserted. The guarantees here are properties of the signing scheme and hold by construction rather than statistically. Each contribution is signed with Ed25519 — a 64-byte signature over the BLAKE2b hash of its canonical payload — and the 32-byte public key is stored with the contributor record. Two independent properties follow. *Integrity*: altering the stored text or metadata after signing is detected, because the recomputed hash no longer matches the signed one. *Authorship*: a signature validates only under the public counterpart of the signing key, and fails under any other key or any mutation of the signature itself.

These guarantees are exposed to consumers directly. The endpoint `GET /v1/contributions/{id}/verify` is unauthenticated and returns the integrity and signature-validity verdicts together with the public key and signature, so any third party can reproduce the check without trusting the operator — the distinction between a record that is merely *signed* and one that is *verifiable*.

The guarantee is bounded by key custody. Because contributor keys are at present derived server-side from the authenticated identity (§4.2), the scheme establishes integrity and public verifiability but not resistance to forgery by the operator itself. Non-custodial signing with client-held keys is required to close that gap and is carried as a limitation in §8.9.

### 8.6 Claim 5 — Credit resists manipulation, but a faithful value measure is unresolved

The economic design (§5) depends on a quantity the per-citation ledger does not supply: how much each contribution actually shaped a given answer. Equal credit per citation is uninformative — it cannot distinguish a decisive contribution from an incidental one — and it is manipulable. This section defines and evaluates an alternative.

**Measure.** For a retrieved contribution $d$, its *marginal value* is the reduction in the answer's resemblance to $d$'s content when $d$ is removed from the context and the answer is regenerated. Credit is the marginal value normalized across the cited set, and payouts (§5) follow that distribution rather than citation count. Per-query credit is recorded in [docs/benchmarks/attribution.md](benchmarks/attribution.md).

On the full gold-annotated set (20 queries, 57 contribution–answer pairs, Qwen 2.5 Coder 7B), retrieval score is at best weakly related to marginal value (Spearman $\rho = 0.19$) and flat per-citation credit is constant by construction. Neither is admissible as a payout proxy; a causal measure is required.

**Faithfulness — weak and judge-sensitive.** The harder question is whether the embedding-based marginal reflects genuine answer quality, evaluated against an independent judge and a corresponding judge-based marginal. The answer depends on the judge. Under gold-fact recall — a coarse, keyword-overlap grader — the embedding marginal is essentially uncorrelated with the judge marginal (Spearman $\rho \approx 0.04$ at the full 57-pair scale). Under an LLM-as-judge, a less brittle grader, the correlation rises to $\rho \approx 0.15$ — still weak, but clearly above retrieval score ($0.09$) and flat credit ($0$ by construction). Two things follow. First, part of the apparent near-zero was judge coarseness, not the measure: a better grader recovers a positive signal. Second, even the better grader leaves the embedding marginal only *weakly* correlated with quality — the right direction, but far short of what setting real payouts would require. Faithfulness is therefore **unestablished**: the measure ranks contributions within an answer and resists manipulation, but its link to answer quality is weak and sensitive to how quality is measured. A stronger judge (held-out human references) and a larger sample are needed to determine whether the signal strengthens; until then, a faithful value estimator is the open problem for the economic layer (§8.9).

**Manipulation resistance.** Marginal credit is robust to the standard attacks, each holding by construction:

- *Duplication.* A near-duplicate raises a contributor's share under per-citation credit (from $1/2$ to $2/3$ in the two-contributor case) but not under marginal credit, since the duplicate carries no additional marginal value.
- *Padding.* An off-topic contribution appended to inflate citation count earns negligible marginal credit.
- *Paraphrase and collusion.* A reworded copy — including one submitted under a second account — cannot raise the combined Shapley share, because the coalition value saturates once the underlying fact is present.

Each property is encoded as a deterministic test in the reference implementation.

**Redundancy.** Leave-one-out under-credits content that is valuable but redundant with a sibling contribution, since either alone appears removable. We address this with a Shapley-value estimator (`attribution.shapley_attribution`, computed exactly for small cited sets), which distributes credit across redundant contributions in proportion to their marginal coalition value while preserving the manipulation-resistance above.

**A structural alternative: attribution by construction.** The measures above are *post-hoc* — they re-run inference with a contribution removed and read the difference, which is expensive and, as shown, only weakly faithful. A different design makes credit a *property of inference itself*: train one low-rank adapter per contributor, then route each query to an adapter rather than measuring after the fact. If the router picks the *owning* contributor, the routing decision *is* the attribution — cheap, deterministic, and reproducible by anyone with the public router and the contribution text. We test the routing half directly: eight per-contributor adapters, queries routed by embedding similarity between the query and each contributor's note (full record in [docs/benchmarks/attribution_route.md](benchmarks/attribution_route.md)).

| Base | Routing accuracy (picks the owner) | Routed recall | Owning-adapter recall |
| --- | ---: | ---: | ---: |
| Qwen 2.5 0.5B | **1.00** | 0.17 | 0.17 |
| OLMo-2 1B | **1.00** | 0.23 | 0.23 |

Routing accuracy is perfect at both model sizes, and the routed adapter's recall equals the owning adapter's exactly (routing cost $0.00$): the router never sends a query to a worse adapter. This is the strongest evidence yet for a *faithful, verifiable* credit signal — the central open problem of this section — because it sidesteps the resemblance proxy entirely. Two caveats keep the result honest. The routed *recall* is low (0.17–0.23) only because each adapter here trains on a single example (one contributor = one fact); the same OLMo-1B reaches owning-recall 1.00 when one adapter trains on the full corpus (§8.7), so the ceiling is the training recipe, not the mechanism — richer per-contributor data is the obvious next step (§8.10). And the perfect routing is measured over eight *well-separated* topics; routing among near-duplicate or overlapping contributions in a single category is the regime that will stress it, and is untested.

**Relation to prior work.** Data valuation — data-Shapley and influence functions — is well developed for model *training*. Faithful, manipulation-resistant attribution for retrieval-grounded *generation*, where a signed proof chain makes the credited set explicit, is to our knowledge unaddressed. The measure is also the system's payout function, so the research question and the contributor's incentive are one and the same.

### 8.7 Claim 6 — Distilled knowledge remains attributable to its contributor

The architecture's long-horizon claim (§3.5) is that the contribution corpus is eventually absorbed into the model's weights. For the economic model to survive that transition, credit assignable at retrieval time must remain assignable after distillation. We test this at small scale by fine-tuning a low-rank adapter (Qwen 2.5 0.5B, two epochs) on the seed contributions and measuring whether the model answers a grounded query correctly with retrieval disabled. Full results are in [docs/benchmarks/distill.md](benchmarks/distill.md).

| Recall of the HTTP/3 → "QUIC over UDP" fact | base | adapter (full corpus) | adapter (target contributor withheld) |
| --- | ---: | ---: | ---: |
|  | 0.00 | 0.50 | 0.00 |

The base model does not produce the fact; training on the corpus installs it; withholding a single contributor's examples removes it again. The fact is therefore entirely attributable to that contributor under a leave-one-contributor-out test — the training-time counterpart of the inference-time attribution of Claim 5. We are not aware of a prior system that both distils community contributions into a model and traces a distilled fact back to its author.

**Attribution across the whole corpus, and what it costs.** The single-fact result generalizes to a per-contributor sweep over all eight invented facts, repeated across seeds, on two open base models. Four quantities matter for the architecture (full records in [docs/benchmarks/distill_attribution.md](benchmarks/distill_attribution.md) and `distill_attribution_olmo.md`):

| | Qwen 2.5 0.5B (3 seeds) | OLMo-2 1B |
| --- | ---: | ---: |
| Knowledge gain (mean recall lift) | +0.26 | +0.75 |
| Attributable fraction (per-contributor) | 0.27 | 0.88 |
| **Entanglement** (disturbance to *other* facts, ≈0 ideal) | 0.20 | 0.15 |
| **Forgetting tax** (Δ on base-known control) | +0.04 | −0.20 |

The larger model learns far more (gain +0.75) and attributes far more cleanly (0.88 of each fact traceable to its owner), which is the encouraging direction. But two costs that bear directly on "certifiable ownership" are non-zero and must be reported: **entanglement** stays around 0.15–0.20 — removing one contributor measurably disturbs others, so attribution is clean but not yet *clean enough* to certify single ownership — and the 1B model pays a **−0.20 forgetting tax**, degrading knowledge it already had. Owning the corpus is not free.

**Real learning or memorization?** A held-out paraphrase of each query — never trained on — separates the two: if recall holds on the paraphrase, the model learned the fact; if it collapses, it memorized the prompt. The two models fall on opposite sides. The 0.5B adapter generalizes (paraphrase recall 96% of trained-query recall), but the 1B adapter does *not* (paraphrase recall only 29% of trained-query recall) — it memorized the training phrasings. Capacity bought attribution *and* memorization. This is reported as the genuine, two-edged finding it is, not smoothed over: distillation at this scale installs and attributes facts, but whether it installs robust *knowledge* is model- and recipe-dependent.

**Composition does not yet hold.** Training two domain adapters and composing them at inference (the mechanism §3.1 anticipates for cross-domain questions) did not, at 0.5B, produce a model that recalls both sets while remaining ablatable per-adapter: ablating one adapter left the other's recall unchanged (full record in [docs/benchmarks/distill_compose.md](benchmarks/distill_compose.md)). Compositional per-adapter attribution is therefore recorded as *inconclusive at this scale*, not proven — a larger base and more examples per adapter are needed.

**Limitations.** The results establish attribution and quantify its costs, not a robust quality gain. Aggregate gold-fact recall across the five seeded queries did not improve under distillation of the seed corpus ($0.367 \to 0.300$); at this many training examples on sub-billion-parameter models this is expected, and far below the ~$10^4$-contribution regime the architecture anticipates (§3.5). The mechanism, the attribution property, the entanglement and forgetting costs, and the memorization caveat are demonstrated; a robust quality improvement at scale is not yet claimed.

### 8.8 Claim 7 — Correctness is a governance property, and it is testable

Claim 2 and its retrieval-path corollary establish that grounding faithfully repeats whatever contribution reaches the context — including a false one. This is the system's central safety boundary, stated bluntly: **the model provides no defense against false content.** Correctness is therefore not a property of the model but of the governance layer that decides which contributions ground answers. This section measures both halves — how completely the model adopts a falsehood, and whether governance can hold the line.

**The model adopts whatever it is grounded on.** Grounding each invented fact on a plausible-but-false variant, and measuring whether the answer states the false claim (full record in [docs/benchmarks/falsehood.md](benchmarks/falsehood.md)):

| Condition | False-claim recall |
| --- | ---: |
| Base model (control) | 0.19 |
| Grounded on the false variant | **0.88** |

The base model rarely volunteers the falsehood (0.19); grounded on it, the model repeats it 88% of the time. Grounding is faithful to the contribution, not to the truth — the same property that makes the knowledge layer powerful is what makes governance load-bearing.

**Conflict, and the fix.** Production retrieval surfaces multiple contributions, so before governance resolves a dispute the model can see a true and a false contribution about the same fact at once. Grounding on both (in both orderings), then on the governance-promoted version alone (full record in [docs/benchmarks/conflict.md](benchmarks/conflict.md)):

| Condition | True-claim recall | False-claim recall |
| --- | ---: | ---: |
| Both present (avg of orderings) | 0.88 | 0.62 |
| — true listed first | 0.88 | 0.75 |
| — false listed first | 0.88 | 0.50 |
| **Vote-gated to the upvoted version** | **0.92** | **0.00** |

With both present the model cannot arbitrate: it adopts the false claim 62% of the time, and the rate swings 0.25 on ordering alone — it follows presentation, not truth. Gating retrieval to the governance-promoted version eliminates false adoption entirely ($0.62 \to 0.00$) while raising true recall to 0.92. This is an architectural requirement, not an optimization: **retrieval must surface only the current, highest-voted version of a claim, never competing versions side by side.**

**Can governance hold the line under attack?** Vote-gating only works if the vote itself resists capture. Since approving a false contribution is what lets it ground answers, the safety metric is the false-approval rate under a sybil attack — an adversary creating fake accounts to upvote falsehoods and downvote truths. We simulate the live aggregation (net-tally threshold) against a truth-correlated honest electorate, comparing one-account-one-vote with reputation-weighted voting where freshly-created accounts carry little weight (full record in [docs/benchmarks/governance.md](benchmarks/governance.md)):

| Aggregation rule | First false contribution approved at |
| --- | ---: |
| Flat (one account, one vote — shipping today) | **0.35×** the honest electorate in sybils |
| Reputation-weighted | **3.20×** |

Flat voting is linear in accounts, which are nearly free to create, so it breaks once the attacker fields about a third as many sybils as there are honest voters. Weighting votes by earned reputation raises the break-in point by roughly the inverse of a sybil's weight — here ~$9\times$. This is the quantitative case for the tier-weighted voting of §4.1 over raw head-count, and it bounds how much false content can ever reach the grounding corpus. The simulation models a single worst-case lockstep adversary; collusion among already-reputable accounts and adaptive strategies are not captured and remain open (§8.10).

**Taken together**, Claim 7 is the safety story. The model has no built-in defense against falsehood (0.88 adoption), but the two governance mechanisms convert that into a defended system: vote-gated retrieval drives false adoption to 0.00, and reputation-weighted voting raises the attacker's cost ~$9\times$. Correctness is something the network *does*, not something the model *has* — and both mechanisms are testable and, at this scale, hold.

### 8.9 Limits of the current evaluation

The results above are preliminary, and the following limitations bound their interpretation:

- **Sample size.** Five questions per bucket is a smoke test rather than a statistical study; the aim at v0.1 is to show that each mechanism reproduces across categories, not to estimate population-scale accuracy.
- **Single-domain seed corpus.** All five routable categories are technical. The out-of-domain refusal in §8.4 is encouraging precisely because no medical contributor yet exists; the harder question — discrimination among adjacent in-domain categories once they are populated — cannot be measured on the present corpus.
- **Automated judging is coarse.** The condition comparison in §8.3 is scored by gold-fact recall, with an LLM-as-judge available as an alternative. Gold-fact recall is a blunt measure and LLM judging carries known biases; held-out, human-written reference answers remain the appropriate standard.
- **The attribution value measure is only weakly faithful, and judge-sensitive.** At the full 57-pair scale the embedding marginal correlates with judged quality at ρ ≈ 0.04 under a coarse gold-recall judge and ρ ≈ 0.15 under an LLM judge (§8.6) — a real but weak signal, not yet strong enough to set payouts. A faithful estimator (better judge, larger N, or a redefined measure) is the central open problem for the economic layer.
- **The routing threshold is coarsely tuned.** $\tau_R = 0.30$ comes from a four-point sweep (§8.2.1) over $N=127$: the lowest threshold achieving zero out-of-domain leakage on the tested distribution, which may be conservative on a broader one. A finer sweep against a held-out validation set, with a reported ROC curve, is the appropriate next step.
- **Distillation is shown only at small scale, and carries costs.** §8.7 establishes attribution under distillation but not a robust quality gain, which the architecture anticipates only near the ~$10^4$-contribution regime; it also surfaces non-zero entanglement (~0.15–0.20), a forgetting tax (up to −0.20 at 1B), and prompt memorization at the larger model — all measured on the eight-fact corpus and likely to shift with corpus size and recipe.
- **Routing-based attribution is tested only on well-separated topics.** The perfect routing accuracy of §8.6 is over eight distinct topics with single-example adapters. The realistic stressor — near-duplicate or overlapping contributions within one category, and adapters trained on many examples per contributor — is not yet measured; routed *quality*, as opposed to routed *attribution*, is consequently not yet established.
- **The governance simulation models one adversary.** The sybil result of §8.8 assumes a single lockstep attacker against a truth-correlated honest crowd. Collusion among already-reputable accounts, adaptive attacks, and a non-stationary honest electorate are not captured.
- **Quantization is a single-point check.** §3.3's edge-inference path is probed only at 4-bit (grounding lift +0.69 preserved); a clean q4-vs-q8-vs-fp16 comparison to locate a precision floor for self-hosting is outstanding.
- **Signing is custodial.** The verification of §8.5 establishes integrity and public checkability, but contributor keys are presently derived server-side. Resistance to forgery by the operator requires client-held keys; until then, the "no trust in the operator" property is scoped to verification rather than to signing custody.

### 8.10 Future work

The central open problem is a **faithful value measure**. The embedding-resemblance marginal, the natural cheap candidate, is only weakly faithful at scale (§8.6), so the work is less to run it on more data than to find a measure that tracks judged quality. Two routes are now distinguished by evidence. The first is a *judge-grounded estimator* — the Shapley variant scored against a held-out human-referenced judge rather than gold-fact recall, or a redefinition of marginal value against answer correctness rather than resemblance. The second, and the more promising given the §8.6 result, is *attribution by construction*: the per-contributor adapter routing that already attributes at 100% accuracy on separated topics. The decisive experiments there are (i) training each adapter on many examples per contributor so routed *quality* — not just routed attribution — can be measured, and (ii) stressing the router with near-duplicate, overlapping contributions inside a single category, where a payout signal would actually be contested. A faithful value measure is the prerequisite for the economic layer either way.

Beyond it, four further axes. **Serving safety**: §8.8 shows vote-gated retrieval drives false adoption to zero on a synthetic conflict; the production analogue is wiring the authority filter (§3.4) so retrieval can only ever surface the current highest-voted version, and measuring false adoption on the live corpus. **Governance under stronger adversaries**: extending the §8.8 sybil simulation to collusion among reputable accounts and adaptive attacks, and tuning the reputation weighting accordingly. **Scale and retrieval**: a larger, multi-domain corpus to turn the per-claim results of §8.2–§8.4 into statistical estimates and to stress routing as adjacent categories populate, and instantiating the dense and cross-encoder stages of §3.4 to close the retrieval loss measured in §8.3. **Sovereign inference**: a clean multi-level quantization comparison (§8.9) to fix a precision floor for edge self-hosting.

---

## 9. Roadmap

### 0–6 months — Pipeline depth
- Client-held signing keys (WebCrypto): move key custody off the server so contribution and vote signatures are non-custodial, closing the forgery gap noted in §8.5 and §8.9.
- Phase 2 of governance: triage stage, with reviewer comment + edit-request workflow.
- Hybrid retrieval (sparse + dense + cross-encoder rerank) replacing pure dense ANN.
- Vote-gated retrieval: surface only the current highest-voted version of a claim, never competing versions side by side — the architectural requirement that §8.8 shows drives false-claim adoption to zero.
- Reputation-weighted vote aggregation in place of flat tally, for the ~9× sybil-resistance gain quantified in §8.8.
- Structured logging of every `(query, retrieval, answer)` interaction — with explicit user quality feedback — as both training data for distillation and the held-out signal a faithful value measure (§8.10) can be validated against.
- First public network instance with 100 invited contributors across 3 categories.

### 6–18 months — Network growth
- Phase 3 of governance: PR-style edit requests with attribution-preserving acceptance.
- Phase 4: public activity feed, revision-diff viewer.
- First domain-specific LoRA adapter, trained on the densest category's approved contributions.
- Payment integration (Stripe ACH for U.S., expanding); first non-trivial contributor payouts.

### 18–36 months — Federation and ownership
- Cross-instance query routing; multiple DeQuorum networks federate like Mastodon servers.
- Full-model retraining on the cross-network corpus, with contribution lineage preserved in the model card.
- Governance transition from founder-controlled to community-elected.
- W3C Verifiable Credentials for credential signals on contributions and votes.

### 3+ years — The trained tier owns the model
- The base model in the registry shifts from "best available open foundation model" to "the network's own trained foundation model."
- Edge inference: base + LoRA combos run on CDN-adjacent GPUs, dropping latency to ~50ms class.
- The contribution corpus becomes a public research asset, cited in third-party papers, used in adjacent academic systems.

---

## 10. Conclusion

The current foundation-model market produces remarkable technology and concentrates the upside. DeQuorum is built on the proposition that **the same technology can be produced in a way that distributes the upside to the people who make it work.**

The proposition rests on three claims, and the evidence reported here speaks to each unevenly.

1. **Layered retrieval over a swappable open base model is a viable serving architecture.** The routing and refusal mechanisms are demonstrated (§8.2, §8.4). Grounding's quality effect is conditional: marginal on facts the base model already knows, but large where it does not — a +0.69 gold-recall gain on invented facts (§8.3). The practical implication is that the network's value comes from knowledge outside the base model's training distribution, not from re-deriving what the base already contains. A direct quality comparison against closed retrieval products is the main piece of evidence still missing for this claim.

2. **Per-claim signed governance makes attribution and payouts computable — and is the system's correctness mechanism.** This is the strongest result: verification is cryptographic and reproducible (§8.5), credit is measurable and resists the standard manipulations (§8.6), and the same proof chain that lets a user audit an answer drives the payout ledger. Governance is also where correctness lives: the model adopts a grounded falsehood 88% of the time (§8.8), but vote-gated retrieval drives that to zero and reputation-weighted voting raises the sybil attacker's cost ~9×. The model supplies fluency; governance supplies truth — and both mechanisms are demonstrated.

3. **The contribution corpus can be distilled into the model with attribution intact, at a measured cost.** Demonstrated across the corpus on two open base models (§8.7): a contributor's fact provably enters the weights and is traceable to its author (attributable fraction up to 0.88). The transition is not free — distillation carries non-zero entanglement, a forgetting tax, and prompt memorization at the larger model — and the quality benefit at scale remains open.

The economic layer carries one unresolved result that scale has made concrete: the cheap value measure is at best **weakly** faithful. At the full benchmark scale the embedding-based marginal value correlates with judged answer quality only weakly and judge-sensitively (ρ ≈ 0.04–0.15 depending on the grader; §8.6) — too weak, as defined, to set fair payouts. Verifiable attribution and gaming-resistant *ranking* hold; converting a ranking into a faithful *valuation* is the central problem the economic model must still solve. The most promising route found here is structural rather than statistical: per-contributor adapter routing attributes credit at 100% accuracy on separated topics (§8.6), recasting the valuation problem as a routing-quality problem.

The case is therefore partial by design: the accountability and safety machinery — verifiable attribution, traceable distillation, and governance that converts a defenseless model into a defended system — is the part that is both novel and demonstrated, while the quality and economic-faithfulness claims are bounded by corpus size and remain the work ahead.

---

*DeQuorum is in active development. The codebase is open, the architectural decisions are documented, the contribution pipeline is wired. For technical documentation see [docs/architecture/](architecture/). For the product vision see [docs/PRODUCT.md](PRODUCT.md). To contribute, see the README at the repository root.*
