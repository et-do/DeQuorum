# ai-playground

Research sandbox for novel AI architectures that are **deterministic, attributable, and explicitly-failing** at small scale. The goal is to test whether a non-statistical reasoning substrate — built on signed knowledge nodes whose contributions to every answer are mathematically traceable — can produce useful inference without LLM-style guessing.

## Invariants

Everything in this repo is tested against four invariants:

1. **Bit-exact reproducibility** — same input ⇒ same output (and same failure), every time.
2. **Full provenance** — every output carries a signed chain of which nodes contributed.
3. **Explicit failure** — missing data raises `CompositionError`; the system never fabricates.
4. **Compositional locality** — adding an unrelated node never silently changes existing outputs.

Property tests for these live under [tests/invariants/](tests/invariants/).

## Layout

```
ai_playground/
  core/             # Node ABC, Signature, ProofObject, AttributionLedger, errors
  vsa/              # Bipolar hyperdimensional vectors (bind/bundle/unbind)
  category/         # Morphism wrapper + compose() that emits ProofObjects
  graph/            # KnowledgeGraph: deterministic routing as proof-of-source
  expert_network/   # Toy 3-node pipeline (chemical → pharma → legal) wiring it all together
  cli.py            # `ai_playground demo` entry point
tests/
  core/  vsa/  category/  graph/  expert_network/  invariants/
```

## Run

```bash
uv sync --extra experimental --extra dev
uv run ai_playground demo --symptom fatigue --age 14
uv run pytest
```
