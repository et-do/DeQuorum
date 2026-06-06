# services/app

The DeQuorum orchestrator: **JSON-only FastAPI API + CLI**, backed by the
same Python package (`src/dequorum/`). All UI lives in
[`services/frontend`](../frontend/) (React); this service emits no HTML.

## API surface

| Path | Verb | Purpose |
| --- | --- | --- |
| `/v1/healthz` | GET | Liveness |
| `/v1/meta` | GET | App config snapshot |
| `/v1/inference/diag` | GET | Ollama model load + TTFT timing |
| `/v1/inference/warmup` | POST | Pre-warm Ollama (called by the chat route on mount) |
| `/v1/agreement` | GET | Current agreement + Tier ladder |
| `/v1/contributions` | GET | List + filter (`status`, `contributor`, `category`, `q`) |
| `/v1/contributions` | POST | Submit a signed contribution (authed) |
| `/v1/contributions/{id}` | GET | Detail + votes |
| `/v1/contributions/{id}/votes` | POST | Cast a signed vote (authed) |
| `/v1/contributions/{id}/comments` | GET / POST | Thread comments on a contribution |
| `/v1/comments/{id}` | DELETE | Soft-redact a comment |
| `/v1/review` | GET | Pending queue |
| `/v1/review/stream` | GET | SSE: real-time queue updates |
| `/v1/contributors` | GET | List signed-up contributors |
| `/v1/contributors/{id}` | GET | Profile + their contributions |
| `/v1/categories` | GET | Taxonomy (hierarchical, parent-child via slash paths) |
| `/v1/lineages/{id}` | GET | Version history of one claim lineage |
| `/v1/chat/sessions` | GET / POST | List / create chat sessions |
| `/v1/chat/sessions/{id}` | GET / DELETE / PATCH | Get / delete / rename one session |
| `/v1/chat/sessions/{id}/stream` | POST | NDJSON-streamed chat completion (the only query path) |

Routes are mounted at `/v1/*`; Caddy strips `/api` before forwarding, so
external clients hit `/api/v1/...`. Auto-generated OpenAPI lives at
http://localhost:8000/docs.

For project-level docs (architecture, product spec, deployment), see the
[repo root README](../../README.md) and [`docs/`](../../docs/).

## Run locally (uv)

```bash
uv sync --extra dev
uv run dequorum serve --mock
uv run dequorum categories
uv run pytest
```

## Run in compose

This service is one of several in the [root `compose.yml`](../../compose.yml):

```bash
docker compose up app
```

The app reads its config from environment variables (see `compose.yml`).

## Layout

```
services/app/
├── pyproject.toml      # Python package + dev deps
├── src/dequorum/       # the package itself
│   ├── core/           # signing, ledger, errors, hashing
│   ├── knowledge/      # contributions + Postgres store + lineage
│   ├── db/             # psycopg3 pool + Alembic migrations
│   ├── identity/       # contributors + tier ladder + agreements
│   ├── taxonomy/       # curated category tree
│   ├── intake/         # submission pipeline (schema + dedup)
│   ├── comments/       # signed discussion threads on contributions
│   ├── chat/           # chat sessions + messages
│   ├── retrieval/      # BM25 over category partitions
│   ├── routing/        # keyword + embedding routers over routable categories
│   ├── inference/      # base model abstraction + model registry + pipeline
│   ├── review/         # votes + review service
│   ├── benchmark/      # quality reality-check harness
│   ├── web/            # FastAPI JSON API
│   └── cli.py          # the `dequorum` entrypoint
└── tests/              # mirrors the package structure
```
