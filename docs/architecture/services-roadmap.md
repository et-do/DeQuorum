# Services roadmap

Synthesis from the parallel infrastructure review (2026-06-02).

## 1. Current decomposition: keep as-is

The six existing services are right-sized for v0.2:

| Service | Why it's its own service |
| --- | --- |
| `app` | Stateless FastAPI; needs to scale on request volume |
| `db` | Stateful Postgres; different lifecycle, manual scaling |
| `ollama` | GPU workload, long cold starts, different deploy target |
| `frontend` | Static SPA; different runtime (CDN) |
| `auth` | Thin facade over Firebase Auth; isolates SDK churn |
| `proxy` | Local-only routing; **must not** be promoted to prod |

**Verdict:** not over-split; not under-split. Each service has a distinct scaling axis and deploy target.

One internal smell: `app` currently does signing, voting, lineage, retrieval, routing, dedup, *and* the ledger in a single process. Acceptable for POC; **carve out `ledger` as its own service before public launch** so the payout audit boundary is clean.

## 2. Services to add (sequenced)

### Add for v0.2

| Service / capability | What | Why |
| --- | --- | --- |
| **`worker` (Cloud Run service) + Cloud Tasks queue** | Async work: embedding recompute, batched payouts, document extraction | `app` blocking on these on Cloud Run = max-instance + per-request billing pain. **Prefer Cloud Tasks** since we're already on GCP. ARQ + Redis is the FastAPI-native alternative if we go multi-cloud. |
| **GCS bucket + signed-URL helper in `app`** | Object storage for submissions, document uploads, future LoRA weights | Not a new container; just a bucket and a helper module |
| **OpenTelemetry SDK in `app` → Cloud Trace** | Distributed tracing | Debugging routing/vote bugs without traces is misery once we have >1 contributor |

### Add before public launch

| Service | What | Why |
| --- | --- | --- |
| **`ledger`** | Split out of `app`. FastAPI service with its own Cloud SQL schema for append-only payout journals | Once real money flows, payout ledger needs its own audit boundary and deploy cadence |
| **Redis (Memorystore)** | Cache hot query/answer pairs + sessions | Reuse the Redis from ARQ if we went that route |

### Defer

| Service | When |
| --- | --- |
| **Distributed-inference orchestrator** | Only when contributor LoRA nodes actually exist. Then build it in Go (see [language choices](#5-language-choices)) |
| **Webhook / federation receiver** | Only if we federate (v1.0+) |
| **Dedicated vector DB** | Stay on pgvector until >10M vectors. It beats Pinecone/Weaviate on latency + ops simplicity at our scale and filters by `primary_category_id`, `approved_at`, `tenant_id` in one SQL round-trip |

## 3. Production gotchas to plan for

- **Cloud Run cold starts.** Set `min-instances=1` on `app` once we have users (else 2-5s of Python boot on first request). For `ollama` on Cloud Run GPU, cold starts run **11-35s** even for small models. Consider keeping `ollama` on the AMD-host gaming PC behind a tunnel for v0.2 and only moving to Cloud Run GPU at launch.
- **Postgres connection pooling.** Cloud Run autoscaling × stock `asyncpg` pool = `max_connections` exhaustion fast. **Enable Cloud SQL built-in PgBouncer** (now GA on Postgres 16). Watch out: prepared statements, advisory locks, and session vars break under transaction pooling — audit usage before flipping.
- **Firebase Hosting pricing.** Free tier: **360 MB/day egress**, then $0.15/GB. Put Cloudflare in front once traffic is real, or move SPA to GCS + Cloud CDN.
- **Ollama on Cloud Run GPU.** GA in 2025 but no uptime SLA on shared GPU tiers; per-second GPU billing adds up fast at `min-instances>=1`; model weights must be baked into the image or loaded from GCS at startup.

## 4. Pre-commit + CI summary

Already landed in this turn:

| File | Adds |
| --- | --- |
| `.pre-commit-config.yaml` | gitleaks (secrets), hadolint (Dockerfiles), shellcheck, yamllint, typos (spell-check), Biome (TS/React), validate-pyproject, expanded `pre-commit-hooks` checks |
| `.github/workflows/ci-python.yml` | uv-based pytest + ruff on changes to `services/app/` |
| `.github/workflows/ci-frontend.yml` | tsc + vite build on changes to `services/frontend/` |
| `.github/workflows/docker-build.yml` | Build (no push) every service Dockerfile, matrix, GHA layer cache. Plus `compose config --quiet` to validate `compose.yml` |
| `.github/workflows/codeql.yml` | CodeQL v4 on Python + TS (free, no token) |
| `.github/workflows/pr-labeler.yml` + `.github/labeler.yml` | Auto-label PRs by changed path |
| `.github/workflows/stale.yml` | Close idle issues / PRs after 60+14 days |
| `.github/dependabot.yml` | Weekly bumps for uv, npm, docker (all 7 Dockerfiles), GitHub Actions |

Deliberately skipped (need auth tokens): Codecov/SonarCloud, deploy workflows, Docker registry pushes, release publishing, Slack/Discord notifications.

## 5. Language choices

**Default verdict: keep Python.** Add Go for exactly one future service. Skip Rust unless we measure ourselves into a corner.

| Service / capability | Language | Why |
| --- | --- | --- |
| `app`, `worker`, `ledger`, federation receiver, metrics aggregator | **Python** | I/O-bound glue. Ecosystem (sentence-transformers, Ollama clients, SQLAlchemy, Jinja2, FastAPI) is a bigger asset than Go's CPU edge. |
| **Distributed-inference orchestrator** (when built) | **Go (Gin or Fiber)** | Fan-out streaming over many long-lived connections is exactly where the GIL converts a 2× language gap into a 10× throughput cliff. Cold starts: Go ~45ms vs Python FastAPI ~325ms-1s. Static typing catches real bugs in routing/peer-health logic that mypy lets through. |
| Cryptographic verification | **Stay Python** | `cryptography` (libsodium-backed) does Ed25519 verify in ~30-50µs ≈ 20k-30k/sec single-threaded. Real bottleneck will be Postgres writes, not crypto. |

Polyglot cost matters for a solo dev. A second language pays off when a service has a fundamentally different **runtime shape** (long-lived streaming) — not when it's merely faster. Inference orchestrator qualifies; nothing else does yet. Share types via OpenAPI generated from FastAPI → Go client via `oapi-codegen`.

## 6. Where this synthesis came from

Parallel workflow ran 2026-06-02 with four research agents:
- Services audit (Cloud Run / Cloud SQL / Firebase 2025-era patterns)
- Pre-commit hooks (token-free, fast)
- GitHub Actions workflows (token-free)
- Language choice analysis (cold starts, GIL, ecosystem)

Full reports saved in the workflow transcript directory under
`~/.claude/projects/-workspaces-ai-playground/`. Sources cited inline in
each report.
