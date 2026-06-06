# dequorum

**A crowdsourced, verifiable, contributor-owned foundational AI.** Contributors publish signed factual claims under a curated category taxonomy; a public peer-review system votes them in or out; an LLM answers queries grounded in approved knowledge while preserving an end-to-end signed proof chain server-side; per-query micro-payments flow back to contributors, reviewers, and compute hosts.

This is the codebase for the v0.1 MVP. License: **Apache 2.0**. See [docs/PRODUCT.md](docs/PRODUCT.md) for the product spec and [docs/WHITEPAPER.md](docs/WHITEPAPER.md) for the architectural thesis.

## Open source, top to bottom

DeQuorum is open source under Apache 2.0, and the production stack runs on open-license dependencies end-to-end:

| Layer | Component | License |
| --- | --- | --- |
| **Base LLMs** | Qwen 2.5 (default), Mistral 7B, Phi-4, Granite 3.1, Llama 3 family — all gated by [`docs/architecture/model-swap.md`](docs/architecture/model-swap.md)'s openness rule | Apache 2.0 / MIT |
| **Inference** | [Ollama](https://ollama.com/) — local-first, GPU-aware model server | MIT |
| **App / API** | [FastAPI](https://fastapi.tiangolo.com/), [uvicorn](https://www.uvicorn.org/), [psycopg 3](https://www.psycopg.org/), [SQLAlchemy](https://www.sqlalchemy.org/), [Alembic](https://alembic.sqlalchemy.org/) | MIT / BSD / LGPL |
| **Retrieval** | [sentence-transformers](https://www.sbert.net/) + [Hugging Face Transformers](https://huggingface.co/docs/transformers) (MiniLM by default) | Apache 2.0 |
| **Database** | [PostgreSQL 16](https://www.postgresql.org/) with the standard ANN extensions on the upgrade path | PostgreSQL License |
| **Frontend** | [React 19](https://react.dev/), [Vite 6](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/), [TanStack Router / Query](https://tanstack.com/), [Tailwind 4](https://tailwindcss.com/) | MIT |
| **Proxy** | [Caddy](https://caddyserver.com/) | Apache 2.0 |

The one not-yet-OSS dependency is **Firebase Auth**, used because it solves email + social signin without owning the credential surface ourselves. It's wrapped behind a small `dequorum.auth` module so swapping to an OSS provider (Supabase Auth, Auth.js, Ory Kratos, our own) is a one-file change. The plan is to make this swap before any external launch.

The base-model registry enforces an explicit license check — see [`services/app/src/dequorum/inference/models.py`](services/app/src/dequorum/inference/models.py) and the `OPEN_LICENSES` set. No model can be made the default unless it's openly licensed.

## Repo layout

The repo is organized as a **multi-service compose stack**. Each service has its own directory, Dockerfile, and README. Cloud targets:

| Local service | Production target |
| --- | --- |
| `services/app` (FastAPI orchestrator) | Google Cloud Run |
| `services/db` (Postgres 16) | Google Cloud SQL |
| `services/ollama` (LLM inference) | Cloud Run with GPU or dedicated VM |
| `services/frontend` (Vite + React) | Firebase Hosting |
| `services/auth` (Firebase Auth Emulator) | Firebase Auth (swappable) |
| `services/proxy` (Caddy) | Not needed in prod — Firebase + Cloud Run handle routing & TLS |

```
ai-playground/
├── services/
│   ├── app/             # FastAPI JSON API + CLI — the DeQuorum orchestrator
│   │   ├── src/dequorum/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── db/              # Postgres 16 — owns the canonical schema (data-model.dbml + data-model.md)
│   ├── ollama/          # Local LLM inference (image pinned in compose.yml)
│   ├── frontend/        # Vite + React + Tailwind SPA
│   ├── proxy/           # Caddy reverse proxy (local-only)
│   └── auth/            # Firebase Auth (emulator locally, real Firebase in prod)
├── compose.yml          # local orchestration
├── docs/
│   ├── PRODUCT.md           # product spec — what, who, scope, pricing, compute economics
│   ├── WHITEPAPER.md        # architectural thesis (mirrored at services/frontend/src/content/whitepaper.ts)
│   ├── architecture/        # internal design docs (DB schema lives in services/db/)
│   │   ├── retrieval-and-scaling.md
│   │   ├── contribution-governance.md
│   │   ├── contributor-intake.md
│   │   ├── gpu-and-throughput.md
│   │   ├── model-swap.md
│   │   └── services-roadmap.md
│   ├── benchmarks/          # benchmark reports (output of `dequorum benchmark`)
│   └── research/            # literature reviews
└── .devcontainer/       # VS Code dev container
```

## Local dev (compose)

```bash
docker compose up                  # whole stack
docker compose up app db ollama    # backend only
```

Then open:
- http://localhost — full stack via the Caddy proxy (SPA + API)
- http://localhost:8000 — direct app (JSON API)
- http://localhost:5173 — direct Vite dev server (SPA only)
- http://localhost:11434 — direct Ollama API
- http://localhost:4000 — Firebase emulator UI
- http://localhost:5432 — Postgres

First-time only: Ollama pulls the configured base model on first start (~5 GB, takes 5–10 min). The model weights persist in a named volume across restarts.

## Local dev (uv, no docker)

The app service still runs comfortably outside compose:

```bash
cd services/app
uv sync --extra dev

# List the seed category taxonomy + seed contributions
uv run dequorum categories
uv run dequorum list-contributions

# Start the web UI (mock model — fast, deterministic, no Ollama needed)
uv run dequorum serve --mock
uv run dequorum serve

# Sign up as a new contributor (signs the user agreement)
uv run dequorum signup --name "Jane Doe" --email "jane@example.com"

# Submit a new contribution (pending review by default)
uv run dequorum submit \
    --contributor <id-from-list-contributors> \
    --category programming/python/typing \
    --text "..." --cite https://...

# Update an existing approved claim (creates v2 of its lineage)
uv run dequorum update --contributor <id> --lineage lin:abc... \
    --text "..." --cite https://...

# Vote on a pending contribution
uv run dequorum vote --contributor <id> --contribution <id-prefix> --score 1

# List + browse
uv run dequorum review
uv run dequorum list-contributors

# Quality reality check (mock = fast; real Qwen = ~20-40 min on CPU)
uv run dequorum benchmark --mock --output docs/benchmarks/mock.md
uv run dequorum benchmark             --output docs/benchmarks/report.md

# Fast routing-only benchmark (no Ollama; scales to N=100s in seconds)
uv run dequorum routebench --output docs/benchmarks/routebench.md

# Tests + lint
uv run pytest
uv run ruff check src tests
```

## Swapping the base LLM

One constant in [`services/app/src/dequorum/inference/models.py`](services/app/src/dequorum/inference/models.py). Full procedure documented in [`docs/architecture/model-swap.md`](docs/architecture/model-swap.md). Don't forget to update the matching `OLLAMA_BOOTSTRAP_MODEL` in [`compose.yml`](compose.yml).

## Quality benchmark

The `benchmark` subcommand runs every question through three conditions side-by-side:

- **A) Vanilla baseline** — bare base model with a generic system prompt
- **B) DeQuorum full** — route → retrieve approved contributions → category-grounded answer + signed contribution chain
- **C) DeQuorum no-retrieval** — router + category persona only, contributions skipped (isolates the lift of retrieval)

The result is a Markdown report you read and judge. The point isn't an automated number — it's an honest comparison that tells you whether the contribution layer is actually adding value vs. an unmodified LLM. Run it whenever you make material changes to routing, retrieval, or the base model.

Reports go to [`docs/benchmarks/`](docs/benchmarks/).
