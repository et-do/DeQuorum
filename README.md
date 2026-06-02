# dequorum

**Intelligence-on-demand, built and owned by the people who use it.** Domain experts contribute signed factual claims; a public peer-review system votes them in or out; an LLM answers queries by routing to relevant approved knowledge and signing every step of the proof chain end-to-end; per-query micro-payments flow back to contributors, reviewers, and compute hosts.

This is the codebase for the v0.1 MVP. License: **Apache 2.0**. See [docs/PRODUCT.md](docs/PRODUCT.md) for the full product spec.

## Layout

```
src/dequorum/
  core/         # Signature, ProofObject, AttributionLedger, errors, hashing
  knowledge/    # Contribution + ContributionStore (SQLite) + status + seed data
  experts/      # Expert + ExpertRegistry + seed personas
  retrieval/    # BM25 retrieval over approved contributions
  routing/      # KeywordRouter + EmbeddingRouter + shared types + Embedder
  review/       # Vote + ReviewService (tally + status transitions)
  inference/    # BaseModel adapter + composition strategies + Pipeline
  web/          # FastAPI + Jinja2 + Tailwind CDN UI
  benchmark/    # Quality reality-check harness
  cli.py
tests/          # mirrors the package structure
archive/        # Shelved Path-R research code (HDC, deterministic toy)
docs/
  PRODUCT.md           # product spec — what, who, scope, pricing, compute economics
  architecture/        # internal design docs (data model, contributor intake, etc.)
    data-model.dbml    # canonical schema (render at dbdiagram.io)
  benchmarks/          # benchmark reports (output of `dequorum benchmark`)
  research/            # literature reviews + shelved experiment specs
```

## Dev container

Ships with **Ollama** pre-installed; `ollama serve` starts automatically. Model weights persist in a named volume (`*-ollama`) so rebuilds don't lose them.

First time only:

```bash
ollama pull qwen2.5-coder:7b   # ~5 GB, takes 5-10 min
```

## Run

```bash
uv sync --extra dev

# List seed experts and seed contributions
uv run dequorum list-experts
uv run dequorum list-contributions

# Ask a question (mock model — fast, deterministic, no Ollama needed)
uv run dequorum query "how do I type a generator function?" --mock

# Ask with real Qwen 2.5 Coder via Ollama
uv run dequorum query "how do I type a generator function?"

# Start the web UI (forwarded to localhost:8000 in devcontainers)
uv run dequorum serve --mock         # mock model, fast
uv run dequorum serve                 # real Qwen

# Submit a new contribution (will start in 'pending' status)
uv run dequorum submit --as python-typing --text "..." --cite https://...

# Vote on a pending contribution (need 2 distinct +1 votes to approve)
uv run dequorum vote --as python-async --contribution <id-prefix> --score 1

# Review queue
uv run dequorum review

# Run the quality reality check (15 questions x 3 conditions; mock = fast)
uv run dequorum benchmark --mock --output report.md
uv run dequorum benchmark --output report.md   # real Qwen, ~20-40 min on CPU

# Tests + lint
uv run pytest
uv run ruff check src tests
```

## Quality benchmark

The `benchmark` subcommand runs every question through three conditions side-by-side:

- **A) Vanilla baseline** — bare Qwen with a generic system prompt
- **B) DeQuorum full** — route → retrieve approved contributions → expert + signed chain
- **C) DeQuorum no-retrieval** — router + expert prompt only, contributions skipped

The result is a Markdown report you read and judge. The point isn't an automated number — it's an honest comparison that tells you whether the contribution layer is actually adding value vs. an unmodified LLM. Run it whenever you make material changes to routing, retrieval, or composition.
