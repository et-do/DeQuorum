# Cost model — DeQuorum at 1000 users

Back-of-the-envelope estimate of what running DeQuorum costs and what flows
through the marketplace. All numbers are directional, not budget — they stop
being right beyond ~2× the assumed load. Revisit when any assumption changes.

## Architecture this assumes

- **Orchestration layer** on GCP: FastAPI on Cloud Run, Postgres on Cloud SQL,
  Firebase Auth, GCS for contribution storage.
- **Inference layer** on community-hosted nodes (Ollama or compatible), paid
  per-token out of end-user revenue.
- **Embedding compute** runs either on the Cloud Run instance (cheap, CPU) or
  pushed to community nodes (free to platform). Cost section assumes the
  former since it's the more predictable path.
- **No GCP-hosted GPU fallback.** If no community node responds, the platform
  errors or queues — it does not silently spin up a Cloud Run GPU. See
  §"Where the economics break" for why.

## User mix and load assumptions

1000 total participants, split:

| Role | Count | Activity assumed |
| --- | --- | --- |
| End users | 800 | 20 queries/day each |
| Contributors | 150 | 1 submission/week, avg 100 KB |
| Node hosters | 50 | Pool serves all queries; ~10k/month each |

Derived monthly totals:

- **~500k queries/month** end-to-end
- **~250M output tokens/month** (assuming 500 tokens/response avg)
- **~25M embedding tokens/month** (50 tokens/query × 500k)
- **~600 contributions/month**, ~60 MB new, ~720 MB cumulative after year 1

## Platform infrastructure cost (what you pay GCP)

Orchestration only. Inference is paid through the marketplace, not here.

| Component | Monthly | Notes |
| --- | --- | --- |
| Cloud Run (FastAPI app) | ~$50 | 500k req × ~200ms CPU + 1 min-instance warm to dodge cold starts |
| Cloud SQL (Postgres) | ~$50 | `db-g1-small`, 10 GB SSD, daily backups. Drop to ~$20 with shared-core early. |
| Firebase Auth | $0 | Free under 50k MAU |
| GCS (contribution docs) | <$1 | Year-1 cumulative ~720 MB |
| Egress | <$1 | ~1 GB/month at $0.12/GB |
| Cloud Logging + monitoring | ~$10 | Free tier covers most, buffer for growth |
| Embedding compute | ~$5 | On-instance sentence-transformers (CPU). $25–30 if outsourced to Voyage/Cohere; $0 if pushed to community nodes |
| **Total** | **~$120/month** | |

**Headline: <$150/month for 1000 users on the orchestration side.**
Scales sublinearly — 10k users is ~$600/month, not $1,200.

## Marketplace money flow

Inference cost is paid to nodes from user revenue, not from your bank account.
Pricing model used for this estimate: $10/month/end-user.

| Flow | Monthly | Per-unit math |
| --- | --- | --- |
| End-user revenue | ~$8,000 | 800 paying × $10 |
| Paid to node hosters | ~$2,500 | $10 / 1M output tokens × 250M tokens |
| Paid to contributors | ~$800 | $1.30 per accepted contribution × 600 |
| Platform retains | ~$4,500 | Covers GCP, dev time, growth, chargeback buffer |

## Per-role economics

### End user (consumer)

- Pays: **$10/month** → ~600 queries → **~$0.017/query**
- Comparison: ChatGPT Plus $20/mo, Claude Pro $20/mo. Competitive only if the
  voting / category-coverage quality story actually differentiates — otherwise users churn
  to the incumbent at 2× price.

### Contributor

- Earns: **~$1.30 per accepted submission**
- Casual (~4 accepted/month): **~$5/month** — coffee money
- Active (50+ accepted/month): **$50–100/month** — meaningful side income
- Long-tail: contributions keep paying as long as they're cited by queries.
  Quality submissions compound; spam decays.
- Frame this as a side-revenue stream tied to quality, not a job.

### Node hoster

- Earns: **~$50/month average** (50 hosters splitting the $2,500 pool)
- Costs:
  - Consumer GPU (RX 7900 XTX, RTX 4090) at 350 W under load
  - 24/7 at $0.12/kWh × 100% utilization = **~$30/month electricity**
  - Realistic ~30% utilization = **~$10/month electricity**
- GPU amortization: $1,500 / 36 months = **~$42/month**
- **Net: roughly break even on hardware, ~$40/month pocket money**
- **This is the fragile leg of the economy** — if crypto mining or competing
  compute markets pay more, hosters leave. Kickback rate has to track market
  compute prices, not stay fixed.

## Sensitivity — what if usage isn't average?

| Scenario | Queries/mo | Platform infra | Inference payout |
| --- | --- | --- | --- |
| Light (5 q/day/user) | 120k | ~$80 | ~$600 |
| Average (this doc) | 500k | ~$120 | ~$2,500 |
| Heavy (50 q/day/user) | 1.2M | ~$200 | ~$6,000 |

Cloud SQL is the floor — it's mostly fixed cost. Cloud Run scales linearly
with traffic. Inference payouts scale linearly with token volume.

## Where the economics break

Listed in roughly the order I'd worry about them.

1. **Quality doesn't justify $10/month.** If voted-quality doesn't deliver
   something the frontier APIs don't, end users churn. Without end-user
   revenue, there's nothing to pay nodes or contributors. The whole stack
   is downstream of this.
2. **Any GCP-hosted GPU fallback.** A single Cloud Run GPU instance is
   ~$1.50/hr running = $1,000+/month. Even 10% fallback at 250M tokens
   would burn the entire platform retention. Architect so this is never
   automatic — error or queue instead.
3. **Sybil attacks on voting.** If reputation can be cheaply fabricated,
   vote-decides-truth becomes vote-decides-spam, and quality collapses. Need
   staking or proof-of-work-equivalent before scaling past a few hundred users.
4. **Contribution spam.** Cap submission sizes (text only, kilobytes not
   megabytes) and rate-limit per-contributor. Otherwise GCS climbs fast and
   review queue chokes.
5. **Node hoster flight.** If the kickback rate is fixed while electricity or
   GPU resale prices spike, hosters disappear and end users get errors. Need
   a dynamic kickback formula tied to market compute rates.

## Revisit triggers

Update this doc when any of these change:

- Pricing model (the $10/user assumption is load-bearing for everything below it)
- Average response length (250M tokens/month is derived from 500 tokens × 500k queries)
- Embedding deployment choice (on-instance vs. hosted API vs. community-node)
- Cloud SQL tier (the $50 floor moves if you graduate to a real instance class)
- Role split (changing 800/150/50 changes every number in the marketplace section)

## TL;DR

- **Your monthly GCP bill at 1000 users: ~$120.** Trivial.
- **Marketplace economy:** ~$8k in, ~$3.3k out to participants, ~$4.5k retained.
- **Single biggest cost risk:** any GCP-hosted GPU fallback. Architect to make
  it impossible, not just discouraged.
