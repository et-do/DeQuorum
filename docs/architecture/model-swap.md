# Base model swap procedure

Source of truth: [`src/dequorum/inference/models.py`](../../src/dequorum/inference/models.py).

## TL;DR

Change one constant, re-pull on Ollama, re-run the benchmark.

```python
# src/dequorum/inference/models.py
DEFAULT_BASE_MODEL_ID: Final[str] = "qwen2.5-7b-instruct"  # was "qwen2.5-coder-7b"
```

```bash
ollama pull qwen2.5:7b-instruct                # whatever the new profile's ollama_tag is
uv run dequorum benchmark --output docs/benchmarks/qwen-general-vs-coder.md
```

That's the whole swap. No CLI flag changes. No web app changes. No test changes.

## Why this works

Every place in the codebase that used to hardcode `"qwen2.5-coder:7b"` now reads
from a single `BASE_MODEL_REGISTRY` instead:

| Layer | What used to be hardcoded | Now reads from |
| --- | --- | --- |
| `OllamaBaseModel.complete()` | the `model` field | `resolve_ollama_tag(self.model or DEFAULT_BASE_MODEL_ID)` |
| `cli.py` query / benchmark `--model` | default string `"qwen2.5-coder:7b"` | `None` → falls through to the registry default |
| `web/app.py` `AppConfig.ollama_model` | default string | empty → resolved at request time |
| `benchmark.runner` `model_label` | the `--model` arg directly | `resolve_ollama_tag()` of the active model |

The `model` field on every layer accepts **either**:
- a registered model_id (`"qwen2.5-coder-7b"`), which we look up in the registry
- a raw Ollama tag (`"llama3:70b-custom"`), which we pass through unchanged

So a swap can be a registry pick OR an escape-hatch raw tag, your choice.

## Adding a new model to the registry

```python
BaseModelProfile(
    model_id="phi-4",                 # internal stable id (kebab-case)
    display_name="Phi-4 14B",
    ollama_tag="phi4:14b",            # the literal arg to `ollama run`
    huggingface_id="microsoft/phi-4", # for adapter / fine-tune references
    license=License.MIT,
    parameter_count_billions=14.0,
    context_window_tokens=16_384,
    instruct_format=InstructFormat.OPENAI_CHAT,
    domain=Domain.GENERAL,
    rationale="One sentence explaining why this model is worth including.",
)
```

## License purity rule

Only `License.APACHE_2_0` and `License.MIT` count as truly open. Models with
"community license" trapdoors (Meta Llama, Gemma, DeepSeek, Qwen 72B+) carry
training-derivative restrictions that would block DeQuorum's Stage-2 path
(fine-tuning the base on contributor data). They can live in the registry as
documented alternatives, but the swap default must always satisfy
`profile.is_open is True` — there's a test that enforces this.

## When you should swap

| Trigger | Recommended target |
| --- | --- |
| Network seed content is mostly code (today) | `qwen2.5-coder-7b` (current default) |
| Network seed content is cross-domain | `qwen2.5-7b-instruct` or `mistral-7b-instruct-v0.3` |
| Reasoning quality is the bottleneck and host RAM allows | `phi-4` (MIT, 14B) or `mixtral-8x7b-instruct` (Apache, MoE) |
| Long-context retrieval is the bottleneck | `granite-3.1-8b-instruct` (128k context) |
| You want a non-Qwen-family second opinion | `mistral-7b-instruct-v0.3` |

## Tests covering this behavior

[`tests/inference/test_models.py`](../../tests/inference/test_models.py) enforces:
- the default is registered
- the default is open-licensed
- the registry has >=2 model families (no single-vendor lock-in)
- both Code and General domains are represented
- the swap mechanism actually works at every layer (registry lookup, raw passthrough, `OllamaBaseModel` resolution)

Run the suite after any registry edit:

```bash
uv run pytest tests/inference
```
