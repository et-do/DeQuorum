# dequorum

**Intelligence-on-demand, built and owned by the people who use it.** Domain experts contribute signed factual claims; a public peer-review system votes them in or out; an LLM answers queries by routing to relevant approved knowledge and signing every step of the proof chain end-to-end; per-query micro-payments flow back to contributors, reviewers, and compute hosts.

This is the codebase for the v0.1 MVP. License: **Apache 2.0**. See [docs/PRODUCT.md](docs/PRODUCT.md) for the full product spec.

## Repo layout

The repo is organized as a **multi-service compose stack**. Each service has its own directory, Dockerfile, and README. Cloud targets:

| Local service | Production target |
| --- | --- |
| `services/app` (FastAPI orchestrator) | Google Cloud Run |
| `services/db` (Postgres 16) | Google Cloud SQL |
| `services/ollama` (LLM inference) | Cloud Run with GPU or dedicated VM |
| `services/frontend` (Vite + React) | Firebase Hosting |
| `services/auth` (Firebase Auth Emulator) | Firebase Auth |
| `services/proxy` (Caddy) | Not needed in prod — Firebase + Cloud Run handle routing & TLS |

```
ai-playground/
├── services/
│   ├── app/             # FastAPI + Jinja2 + CLI — the DeQuorum orchestrator
│   │   ├── src/dequorum/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── db/              # Postgres 16
│   ├── ollama/          # Local LLM inference
│   ├── frontend/        # Vite + React + Tailwind SPA stub
│   ├── proxy/           # Caddy reverse proxy (local-only)
│   └── auth/            # Firebase Auth (emulator locally, real Firebase in prod)
├── compose.yml          # local orchestration
├── docs/
│   ├── PRODUCT.md           # product spec — what, who, scope, pricing, compute economics
│   ├── architecture/        # internal design docs
│   │   ├── data-model.dbml      # canonical schema (render at dbdiagram.io)
│   │   ├── contributor-intake.md
│   │   └── model-swap.md
│   ├── benchmarks/          # benchmark reports (output of `dequorum benchmark`)
│   └── research/            # literature reviews
├── archive/             # Shelved Path-R research code
└── .devcontainer/       # VS Code dev container
```

## Local dev (compose)

```bash
docker compose up                  # whole stack
docker compose up app db ollama    # backend only
```

Then open:
- http://localhost — full stack via the Caddy proxy (SPA + API)
- http://localhost:8000 — direct app (Jinja UI + JSON API)
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

# List seed experts and seed contributions
uv run dequorum list-experts
uv run dequorum list-contributions

# Ask a question (mock model — fast, deterministic, no Ollama needed)
uv run dequorum query "how do I type a generator function?" --mock

# Ask with the real default base model (configured in inference/models.py)
uv run dequorum query "how do I type a generator function?"

# Start the web UI
uv run dequorum serve --mock
uv run dequorum serve

# Sign up as a new contributor (signs the user agreement)
uv run dequorum signup --name "Jane Doe" --email "jane@example.com"

# Submit a new contribution (pending review by default)
uv run dequorum submit --as python-typing --text "..." --cite https://...

# Update an existing approved claim (creates v2 of its lineage)
uv run dequorum update --as python-typing --lineage lin:abc... --text "..." --cite ...

# Vote on a pending contribution
uv run dequorum vote --as python-async --contribution <id-prefix> --score 1

# List + browse
uv run dequorum review
uv run dequorum categories
uv run dequorum list-contributors

# Quality reality check (mock = fast; real Qwen = ~20-40 min on CPU)
uv run dequorum benchmark --mock --output docs/benchmarks/mock.md
uv run dequorum benchmark             --output docs/benchmarks/report.md

# Tests + lint
uv run pytest
uv run ruff check src tests
```

## Swapping the base LLM

One constant in [`services/app/src/dequorum/inference/models.py`](services/app/src/dequorum/inference/models.py). Full procedure documented in [`docs/architecture/model-swap.md`](docs/architecture/model-swap.md). Don't forget to update the matching `OLLAMA_BOOTSTRAP_MODEL` in [`compose.yml`](compose.yml).

## Quality benchmark

The `benchmark` subcommand runs every question through three conditions side-by-side:

- **A) Vanilla baseline** — bare base model with a generic system prompt
- **B) DeQuorum full** — route → retrieve approved contributions → expert + signed chain
- **C) DeQuorum no-retrieval** — router + expert prompt only, contributions skipped

The result is a Markdown report you read and judge. The point isn't an automated number — it's an honest comparison that tells you whether the contribution layer is actually adding value vs. an unmodified LLM. Run it whenever you make material changes to routing, retrieval, composition, or the base model.

Reports go to [`docs/benchmarks/`](docs/benchmarks/).
