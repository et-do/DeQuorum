# Model serving: providers, latency, and cost

`model-swap.md` covers *which* base model the network uses (its identity, license,
context window). This doc covers *how* that model is served — the runtime/provider —
and what it costs in each environment. The two are orthogonal: you pick an open
model in the registry, then choose where to run it.

## The key insight

The ~1-minute latency of local Ollama is a **self-hosting artifact, not a tax on
open models.** The same open weights (Qwen, Mistral, OLMo) served by a hosted
provider (Groq, DeepInfra, Together, Fireworks, OpenRouter, or your own vLLM) return
in **well under a second** at **$0.02–0.10/M input tokens (8B) to $0.40–0.90/M
(70B)**. So we keep open models *and* get fast, cheap inference — by making the
provider a config choice, not a hardcode.

## Providers

The serving model is selected by `dequorum.inference.provider.build_serving_model`
(used by the web app's `_model()`), from these backends:

| Provider | When | Cost |
| --- | --- | --- |
| `mock` (`MockBaseModel`) | tests / CI — deterministic, no network | $0 |
| `ollama` (`OllamaBaseModel`) | **default**; local dev + the "you can self-host" sovereignty path; GPU benchmarks (Colab) | $0 (your hardware) |
| `openai` (`OpenAICompatibleModel`) | production, or opt-in fast dev — any OpenAI-compatible endpoint | pay-per-token |

`OpenAICompatibleModel` speaks the standard `/chat/completions` wire format, so one
client works across Groq / DeepInfra / Together / Fireworks / OpenRouter / vLLM /
Ollama's own `/v1`. Switching providers is a `base_url` + `api_key` + `model` change.

## Configuration

Environment variables read by `AppConfig`:

| Variable | Meaning | Default |
| --- | --- | --- |
| `DEQUORUM_MODEL_PROVIDER` | `ollama` or `openai` | `ollama` |
| `DEQUORUM_OLLAMA_HOST` | Ollama server URL (ollama provider) | `http://localhost:11434` |
| `DEQUORUM_OLLAMA_MODEL` | model id/tag to pin (ollama provider) | registry default |
| `DEQUORUM_MODEL_BASE_URL` | endpoint (openai provider), e.g. `https://api.groq.com/openai/v1` | — |
| `DEQUORUM_MODEL_API_KEY` | provider key (openai provider) | — |
| `DEQUORUM_MODEL` | model tag at the provider, e.g. `llama-3.3-70b-versatile` | — |

Example — production on a fast hosted open model:

```sh
DEQUORUM_MODEL_PROVIDER=openai
DEQUORUM_MODEL_BASE_URL=https://api.groq.com/openai/v1
DEQUORUM_MODEL_API_KEY=gsk_...
DEQUORUM_MODEL=qwen-2.5-32b   # an openly-licensed model at the provider
```

## What it costs, by environment

- **Tests / CI:** $0 — `mock` provider, no calls.
- **GPU benchmarks:** $0 — Ollama on Colab's free GPU.
- **Local dev:** $0 by default (Ollama). Only costs money if *you* set the `openai`
  provider for faster dev — and then only pennies (dev volume is tiny).
- **Production:** pay-per-token, billed only on real query traffic.

In short: a hosted provider costs money **only on the calls you route to it**. Dev,
tests, and benchmarks stay free unless you deliberately opt in.

## Two rules the operator must honor

1. **Open license still applies.** The hosted model must be openly licensed
   (Apache-2.0 / MIT — Qwen, Mistral, OLMo, …), same purity rule as the registry
   (`OPEN_LICENSES` in `inference/models.py`). A hosted Llama/Gemma/closed model
   breaks the Stage-2 distillation path (their licenses forbid training other models)
   and the sovereignty thesis. The provider client can't license-check an arbitrary
   remote tag, so this is an operator responsibility, documented here.
2. **Closed models are serving-only.** If a *user* supplies their own key for a
   closed model (GPT/Claude) for speed/quality, that is allowed for **serving the
   answer only**. Closed-model output must **never** enter the contribution corpus or
   any distillation — their terms forbid using outputs to build competing models, and
   it would poison the open corpus. BYO-key answers are ephemeral; the corpus and
   training stay on open models. (BYO-key plumbing is a follow-on; the provider
   abstraction is the foundation it will use.)

## Relationship to other docs

- [model-swap.md](model-swap.md) — choosing *which* model (identity, license, registry).
- [build-direction.md](build-direction.md) — why model choice is a commodity and the
  value lives in the governance/attribution/payout layer.
- [cost-model.md](cost-model.md) — per-query unit economics.
