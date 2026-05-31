# DeQuorum — Product

> **Status:** v0.1 in development. Single-machine simulation with 5 seed experts and 25 seed contributions; working trace UI; embedding-routed pipeline with peer-review queue. No external users yet. Targeting first external testers in ~3 months. Codebase / Python package: `dequorum`.

## 1. What this system is

**The first crowdsourced, user-owned, kickback-paying AI for the masses.**

DeQuorum is what you get when you build a ChatGPT or Gemini that's **owned by its users instead of by a tech giant**. Anyone — individual or organization, credentialed or not — can submit signed factual claims about anything they know. Other users vote on whether each claim is correct. The voting outcome (not credentials, not the platform operator) decides what the AI is allowed to draw on. When someone asks a question, the network routes it to relevant approved knowledge, generates an answer using only that knowledge, and signs every step of the reasoning chain so the answer is verifiable end-to-end. **Every time your knowledge shapes an answer, you get paid.**

The thesis: today, three tech giants own the AI infrastructure, the training data (often scraped from the rest of us), and all the profits. DeQuorum puts those three things back into users' hands — **you contribute the knowledge, you verify each other's claims, you host the compute, and you take the revenue share.** The platform operator is a coordinator, not a kingmaker.

One-liners we like, pick your favorite:
- *"ChatGPT, but you own it and you get paid."*
- *"Wikipedia × Stack Overflow × an LLM that pays its sources, run on Mastodon-style federated infrastructure."*
- *"Democratizing AI: contribution, training, serving, inference, and revenue, all crowdsourced."*

The name **DeQuorum** = decentralized + quorum (the voting body that decides what's accepted).

## 2. The problem we're solving

Existing AI knowledge systems have three structural problems:

| Problem | DeQuorum's answer |
| ------- | ----------------- |
| **Sources are unknowable.** You can't tell where ChatGPT/Copilot learned what it told you. | Every answer ships with a signed chain of contributors, each independently verifiable. |
| **Hallucination is common.** Models confidently state wrong things. | Only peer-approved contributions can shape answers. When no qualified expert is available, the system refuses rather than guesses. |
| **Knowledge contributors get extracted from, not paid.** | Every query credits each contributor whose knowledge shaped the answer. Real money (Stripe ACH) when revenue allows. |

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

## 7. What we refuse to do

DeQuorum is, deliberately, a direct alternative to ChatGPT, Gemini, Claude, and Copilot — the goal is to be everything those products are, except owned by users instead of by tech giants. These are the practices of the incumbents that we won't replicate:

- **We won't hide our sources.** Every answer ships with a signed, independently verifiable chain showing exactly which contributors shaped it. No "trust me, I'm an AI."
- **We won't hallucinate to fill the gap.** When no qualified expert has spoken on a topic, the system says so plainly instead of confabulating. Refusal-over-guessing is a feature, not a limitation.
- **We won't extract value from contributors without paying them back.** Every cent of revenue is split by attribution: contributors, reviewers, compute hosts, operator, treasury. The default split gives the largest slice (50%) to the people whose knowledge made the answer possible.
- **We won't centralize ownership.** The code is open source, anyone can self-host, and federation across instances is built in from v1.0. No single operator (including us) can pull the rug.
- **We won't gate participation behind credentials.** Anyone can submit; voting decides. Credentials are reputation signals, never permission slips.
- **We won't make decisions in a back room.** Truth is decided by the voting body, with public audit trails on every vote.
- **We won't speculate on tokens to fund ourselves.** Kickbacks are real money (Stripe ACH, eventually). If a token model ever ships, it's a utility within the network, not a fundraising mechanism.
- **We won't pretend the v0.1 demo defines the product.** The seed content happens to be OSS code knowledge because that's what existed when we built the demo. The architecture is fully content-agnostic — medical knowledge, history, cooking, scientific literature, all welcome from day one.

What we *do* concede (for now, not forever):

- We don't train our own base model yet — we use Qwen 2.5 Coder 7B (Apache 2.0). Differentiated training comes in years 2–3 once aggregated approved contributions justify it.
- We're not a contributor lottery. Top contributors can earn meaningful recurring income; no one gets rich on a single contribution.

## 8. Differentiation

| Compared to | What's the same | What's different |
| ----------- | --------------- | ---------------- |
| **ChatGPT / Copilot** | Conversational AI for knowledge questions | Verifiable source chain; refuses rather than hallucinates; contributors are paid |
| **Wikipedia** | Anyone-can-contribute, peer-voted knowledge | Atomic facts vs. articles; AI synthesizes answers; contributors paid |
| **Stack Overflow** | Knowledge from domain practitioners | Fresh AI-synthesized answers vs. historical Q&A archive; pay-per-cite |
| **Bittensor** | Decentralized AI with incentives | Not a blockchain; not generic compute marketplace; attribution math is part of inference, not validator opinion polls |
| **Petals** | Decentralized inference | Many small specialized adapters, not one big model split across peers; inference fast on a single node |
| **Hivemind** | Distributed AI infrastructure | Not collaborative base-model training; modular per-contributor adapters; preserves per-contributor attribution |

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
