# ai-playground

Open-source crowdsourced AI network for verified OSS / code knowledge. Domain experts contribute signed facts; a public peer-review system validates them; an LLM with hot-swap expert adapters answers queries by routing to relevant experts; per-query micro-payments flow back to the contributing experts, reviewers, and compute providers.

This is the codebase for the v0.1 MVP. License: **Apache 2.0**.

## Invariants

Everything in this repo is tested against four invariants:

1. **Bit-exact reproducibility** — same input ⇒ same output (and same failure), every time.
2. **Full provenance** — every output carries a signed chain of which contributors produced it.
3. **Explicit failure** — missing data raises `CompositionError`; the system never fabricates.
4. **Compositional locality** — adding an unrelated contributor never silently changes existing outputs.

Property tests for these live under [tests/invariants/](tests/invariants/).

## Layout

```
ai_playground/
  core/               # Signature, ProofObject, AttributionLedger, errors, hashing
  experts.py          # Expert dataclass + ExpertRegistry
  router.py           # KeywordRouter — picks experts per query
  base_model.py       # Ollama HTTP client + deterministic MockBaseModel
  pipeline.py         # End-to-end query: route → invoke experts → combine → credit ledger
  seed_experts.py     # Five hand-written OSS / code expert personas
  cli.py              # `ai_playground query | list-experts | demo`
  category/           # Categorical composition primitives (carried over from earlier scaffolding)
  graph/              # Signed knowledge-graph routing
  expert_network/     # Toy 3-node deterministic pipeline (carried over)
tests/
  test_*.py + per-module subdirs + invariants/
archive/              # Shelved HDC research code (Experiment 1)
research/             # Literature reviews + experiment specs
```

## Dev container

The dev container ships with **Ollama** pre-installed and runs `ollama serve` automatically on container start. Model weights persist in a named volume (`*-ollama`) so rebuilds don't lose them.

First time only, pull the base model:

```bash
ollama pull qwen2.5-coder:7b   # ~5 GB, takes 5-10 min depending on connection
```

After that, the model stays cached across container rebuilds.

## Run

```bash
uv sync --extra dev

# Run the toy deterministic pipeline (no LLM needed)
uv run ai_playground demo --symptom fatigue --age 14

# List the seed experts
uv run ai_playground list-experts

# Ask a real question with the mock model (deterministic, no Ollama needed)
uv run ai_playground query "how do I type a generator function in python?" --mock

# Ask with the real Qwen 2.5 Coder model (requires `ollama pull` first)
uv run ai_playground query "how do I type a generator function in python?"

# Full test suite
uv run pytest
```
