# DeQuorum — Product

> **Status:** v0.1 in development. Single-machine simulation with 5 seed experts and 25 seed contributions; working trace UI; embedding-routed pipeline with peer-review queue. No external users yet. Targeting first external testers in ~3 months. Codebase / Python package: `dequorum`.

## 1. What this system is

**Intelligence-on-demand, built and owned by the people who use it.**

Foundational LLMs have made on-demand intelligence genuinely useful — ask a question, get an answer. DeQuorum brings that same kind of capability to everyone at a democratic level: **anyone can contribute knowledge, anyone can vote on what's true, anyone can host the compute, and anyone can earn from the network's revenue.** When you ask a question, the network routes it to the relevant verified knowledge, generates an answer signed end-to-end so you can trace exactly where every claim came from, and pays everyone whose work made the answer possible.

The thesis: the most powerful AI today is built by a small handful of organizations. The knowledge often comes from all of us. The revenue rarely does. DeQuorum is an attempt to put **all of it** — contribution, training, serving, inference, revenue — into the hands of the humans who actually do the work. You contribute, you verify, you own a slice, and you share in what gets paid.

One-liners we like, pick your favorite:
- *"Intelligence-on-demand, owned and paid for by all of us."* 🌍
- *"Wikipedia × Stack Overflow × an LLM that pays its sources, federated like Mastodon."*
- *"Democratizing every layer of AI: contribution, training, serving, inference, and revenue."*

The name **DeQuorum** = decentralized + quorum (the voting body that decides what the network believes).

## 2. The gap we're trying to fill

Today's AI knowledge systems are remarkable, but three things are missing from the public versions of them. DeQuorum exists to fill those gaps:

| What's missing | What DeQuorum adds |
| --------------- | ------------------ |
| **Verifiable sources.** It's hard to tell where any given answer's claims came from. | Every answer ships with a signed chain of contributors, each independently verifiable. |
| **Honesty about limits.** Today's models often answer confidently even when they shouldn't. | Only peer-approved knowledge can shape answers. When no qualified expert has weighed in, the system says so plainly instead of guessing. |
| **Shared upside for the people whose knowledge made it work.** | Every query credits each contributor whose knowledge shaped the answer. Real money flows back (Stripe ACH when revenue allows). |

## 3. What it hopes to achieve at scale

### v1.0 (12–18 months)

- 1,000+ active contributors across many domains, with no domain lock-in
- 100K+ users per week asking real questions
- Cumulative micro-payments to active contributors are meaningful — order of $100–$1,000/year for moderate contributors, $5–10K/year for top contributors
- The network produces verifiably-better answers than vanilla ChatGPT on any topic where contributors have invested
- A credible default answer for "where do I go when I actually need to trust the AI's reasoning?"

### v2.0 (years 2–3)

- Multiple independent instances federate, like Mastodon servers, with cross-instance query routing
- The network fine-tunes its own base model on aggregate peer-approved contributions
- Governance shifts from founder-controlled to community-elected
- W3C Verifiable Credentials integrated for optional credential signals on contributions/voters

## 4. Who it's for

The same person can wear multiple hats over time.

| Role | What they get | What they contribute |
| ---- | ------------- | -------------------- |
| **Contributor** (individual or organization) | Recognition with citations + recurring micro-payments + clean attribution trail | Signed factual claims in any domain, with citations and an attestation that the content is theirs or public-domain |
| **Reviewer** | Smaller micro-payments + visible domain reputation | Votes (approve / reject / abstain) on submitted contributions |
| **Compute Host** | Per-query payments | A machine running an expert node (LoRA adapter + base model + serving stack) |
| **Developer** | Reputation in the project; eventually paid for accepted contributions | Reviews the system's internals — code, routing logic, attribution math, security — not content |
| **End User** | Verifiable, citable answers; no "trust me" required | Queries (paid per-query at v1.0) + optional feedback |
| **Instance Operator** | Influence over their instance's policies; reputation for running a clean network | Infrastructure: orchestrator, voting service, ledger, moderation |

Two populations who can all contribute knowledge:

- **Credentialed** (Dr. So-and-so, MIT, Reuters, professional body)
- **Uncredentialed but knowledgeable** (the senior dev who's been writing Python for 20 years; the retired teacher who knows the Civil War)

The voting system absorbs the difference. Credentials are visible signals; they're never a gate to submitting.

## 5. Truth model — voting decides, with defenses

The deciding factor for whether a claim is accepted is **the network's voting outcome**, not credentials, not the operator's call, not any single authority. This is the Wikipedia bet, applied to AI knowledge.

Voting only works at scale if the voting system itself has defenses. These are required components, not optional:

- **Reputation-weighted voting** — voters who historically voted with eventual consensus get more weight than fresh accounts. Stops a flood of new accounts from drowning experienced reviewers.
- **Sybil resistance** — stops one person from creating 100 fake accounts. Options: phone/email verification, social proof, stake-to-vote, or attached verifiable credentials.
- **Undo / appeal log** — rejected contributions can be re-submitted with rebuttal; votes themselves can be challenged.
- **Audit trail visibility** — every vote signed, every voter's history visible. Coordinated brigading is detectable in retrospect, even if not always in the moment.

These defenses are **required before public launch**. They are not credentialing — credentialed users still earn or lose reputation the same way as uncredentialed ones.

## 6. Pricing & kickbacks

### Revenue model mix (v1.0)

- **Freemium subscription** — consumer default: ~10 free queries/day, $15/month for unlimited
- **B2B / enterprise tier** — $20/seat/month for companies wanting auditable AI as part of their tooling
- **Sponsored verticals** — companies pay to sponsor a domain (e.g. AWS sponsors cloud-infrastructure experts). Disclosure mandatory: *"This domain is sponsored by X. Funding does not influence peer review outcomes."*
- **Donation pool** — bootstraps unfunded domains; early contributors in fresh verticals get paid from the pool until that vertical self-sustains

No real crypto for v0.1. Stripe ACH for payouts. Crypto considered later as an option (not a requirement).

### How kickbacks split per query

Gross revenue from each query is split by attribution:

| Recipient | Share | Reasoning |
| --------- | ----- | --------- |
| Contributors whose facts were cited in the answer | **50%** | They are the knowledge. Largest slice by design. |
| Reviewers who approved those contributions | **10%** | Quality control matters and should be paid. |
| Compute hosts that served the inference | **25%** | They paid for the GPU and bandwidth. |
| Instance operator | **10%** | Infrastructure, moderation, on-call. |
| Network treasury | **5%** | R&D, reserves, governance, sponsored-vertical seed funding. |

Tunable as we learn. The principle: contributors get the largest single slice.

## 7. Principles we won't compromise on

These are the design choices we hold as load-bearing — the things that make DeQuorum a genuinely user-owned alternative to centrally-controlled AI rather than just another shell on top of one. Everything else is up for negotiation as the network grows.

- **Transparent by default.** Every answer ships with a signed, independently verifiable chain showing exactly which contributors shaped it. No "trust me" answers.
- **Honest about limits.** When no qualified knowledge has been contributed on a topic, the system says so plainly instead of guessing. Refusal-over-hallucination is a feature.
- **Contributors get paid.** Every cent of revenue is split by attribution — and the largest single slice (50%) goes to the people whose knowledge made the answer possible.
- **Open and forkable.** Apache 2.0 code. Anyone can self-host or fork. Federation across instances is part of the v1.0 design, not a v2 add-on. No single operator (including us) can pull the rug.
- **Open participation.** Anyone can submit knowledge; the voting body decides what's accepted. Credentials are reputation signals, not permission slips.
- **Transparent governance.** Every vote is signed and every voter's history is auditable. Decisions about what the network believes happen in the open.
- **Real money, not speculation.** Kickbacks flow as actual currency (Stripe ACH, eventually). If a token model ever ships, it'll be a utility within the network, never a fundraising vehicle.
- **Domain-flexible from day one.** The architecture treats every topic the same — software, science, cooking, history, medicine, anything. The v0.1 seed content is OSS code only because that's what existed when we built the demo, not because the system is for coders.

Two things we openly compromise on for v0.1 (for now, not forever):

- We don't train our own base model yet — we use Qwen 2.5 Coder 7B (Apache 2.0). A network-trained differentiated base comes in years 2–3 once aggregated approved contributions justify it.
- We're not a get-rich-quick scheme. Top contributors can earn meaningful recurring income, but no one gets rich on a single contribution.

## 8. Where we sit in the landscape

Lots of great work exists in this space; here's where DeQuorum fits relative to neighbors we admire and learn from.

| Neighbor | What's shared | What DeQuorum brings additionally |
| -------- | ------------- | --------------------------------- |
| Foundational chat assistants (ChatGPT, Gemini, Claude, Copilot, etc.) | Conversational intelligence-on-demand | Verifiable source chain on every answer, refusal-over-guessing, user ownership, revenue back to contributors |
| Wikipedia | Anyone-can-contribute, peer-voted knowledge | Atomic facts that an AI can compose into fresh answers; contributors paid per cite |
| Stack Overflow | Knowledge from domain practitioners | AI-synthesized current answers (not just historical Q&A archive); pay-per-cite model |
| Bittensor | Decentralized AI with built-in incentives | Per-source attribution is part of the inference itself, not a validator opinion poll; no blockchain dependency |
| Petals | Decentralized inference | Many small specialized adapters (one expert per node) instead of one big model split across peers; fast on a single machine |
| Hivemind | Distributed AI infrastructure | Modular per-contributor adapters that preserve attribution end-to-end, instead of collaborative base-model training that blends gradients |

## 9. Regulatory & liability posture

**Regulatory load is low for most cases, with specific exceptions.**

- **Copyright / IP** — covered by user attestation at submission ("this content is mine or public-domain"). DMCA safe harbor pattern, same as YouTube/Reddit/Twitter.
- **Defamation** — US Section 230 covers most cases; less clear outside US. Standard platform terms.
- **Medical / financial / legal advice** — the EU AI Act classifies these as high-risk regardless of user attestations. Emerging US state laws too. **For v1.0, regulated-advice verticals need domain-specific guardrails before launch** (or explicit "for informational purposes only" framing with refusal patterns).
- **CSAM / illegal content** — must be actively moderated regardless of attestations. Standard trust-and-safety obligation.

**Liability is architecturally minimized.** Our system happens to have the strongest possible legal defense:

- Every answer cites verifiable sources, signed by their contributors who attested to ownership.
- The network refuses to answer rather than guessing.
- The proof chain makes "the AI made it up" impossible to claim.

Compare to *Moffatt v. Air Canada* (2024) where Air Canada was held liable for hallucinated chatbot output — that case is much harder to win against a system that cites everything and refuses unverified claims.

**Liability risk is real but architecturally minimized.** It is not zero, and the legal landscape around AI output is actively evolving.

## 10. Open questions we haven't answered yet

Honest about what's undecided:

- **Legal entity.** LLC? Public-benefit corp? Nonprofit foundation? Affects governance, fundraising, IP defaults.
- **Sybil resistance specifics.** Phone/email? Social proof? Stake-to-vote? Credential attachment? Pick one before public launch.
- **Cross-domain reasoning quality.** When a question genuinely needs knowledge from multiple domains, does our composition strategy hold up? Empirical question, unanswered.
- **Routing quality past ~1000 experts.** Embedding routing works well at small scale. Graceful degradation vs. catastrophic failure is untested.
- **Reputation algorithm.** How does the reputation-weighted voting actually compute weights? Linear? Logarithmic? Decay-with-time? Real design work.
- **Moderation appeals process.** When a contribution is rejected or a contributor is sanctioned, what's the appeal flow?

## 11. License & distribution

- **Code license:** Apache 2.0 (matches base model, includes patent grant, AI/ML community standard).
- **Base model:** Qwen 2.5 Coder 7B, Apache 2.0, hash-pinned. Reasoning is borrowed; the differentiated layer is signed peer-approved knowledge on top.
- **Distribution model:** official hosted instance (DeQuorum.org or similar) + fully open code. Anyone can self-host or fork. Federation between instances is a v1.0 design constraint, not a v2 bolt-on.

## 12. Glossary

Shared vocabulary the codebase already uses:

- **Expert** — a signed persona that contributes knowledge in a domain. Backed by a system prompt today; backed by a LoRA adapter in Week 4+.
- **Contribution** — a signed factual claim attached to an expert, with citations and an attestation.
- **Vote** — a signed +1/0/-1 from one user on one contribution. One slot per (contribution, voter); re-voting overwrites.
- **Routing** — picking which experts should answer a given query (embedding-based by default; keyword as deterministic baseline).
- **Retrieval** — pulling the most relevant *approved* contributions for each routed expert.
- **Composition** — combining N expert answers into a final response (`pick_best` is the default; `concat` is also available).
- **Proof chain** — the ordered list of signatures (contributions + expert answers) that produced the final response.
- **Ledger** — the running record of who's owed how much.
- **Instance** — one deployment of the DeQuorum orchestrator. Analogous to a Mastodon server.
- **Reputation** — accumulated weight a voter has earned by voting with eventual consensus. Per-domain.
