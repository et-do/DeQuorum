# services/app

The DeQuorum orchestrator: FastAPI HTTP API + Jinja2 web UI + CLI, all backed
by the same Python package (`src/dequorum/`).

For project-level docs (architecture, product spec, deployment), see the
[repo root README](../../README.md) and [`docs/`](../../docs/).

## Run locally (uv)

```bash
uv sync --extra dev
uv run dequorum query "..." --mock
uv run dequorum serve --mock
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
│   ├── knowledge/      # contributions + SQLite store + lineage
│   ├── identity/       # contributors + tier ladder + agreements
│   ├── taxonomy/       # curated category tree
│   ├── intake/         # submission pipeline (schema + dedup)
│   ├── experts/        # expert personas + seeds
│   ├── retrieval/      # BM25
│   ├── routing/        # keyword + embedding routers
│   ├── inference/      # base model abstraction + model registry + pipeline
│   ├── review/         # votes + review service
│   ├── benchmark/      # quality reality-check harness
│   ├── web/            # FastAPI + Jinja2 + Tailwind UI
│   └── cli.py          # the `dequorum` entrypoint
└── tests/              # mirrors the package structure
```
