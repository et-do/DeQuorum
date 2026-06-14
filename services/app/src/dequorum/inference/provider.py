"""Serving model provider selection.

One place that turns environment/config into a `BaseModel`, so every environment
makes an explicit, cheap-by-default choice:

  - `mock`   — no network, used by tests/CI ($0).
  - `ollama` — local self-hosted server; free, the default for dev and the
    "you can self-host" sovereignty path. Slower on small hardware.
  - `openai` — any OpenAI-compatible hosted endpoint (Groq / DeepInfra / Together /
    Fireworks / OpenRouter / vLLM). Fast and cheap-per-token, billed only on the
    calls actually routed to it — so it costs nothing in dev/test/benchmarks unless
    you deliberately point them at it; production opts in.

Keeping provider choice here (not hardcoded in the serving path) is also a protocol
seam: an integrator brings their own model by setting these knobs, nothing else.
"""

from __future__ import annotations

from dequorum.core.errors import CompositionError
from dequorum.inference.base_model import (
    BaseModel,
    MockBaseModel,
    OllamaBaseModel,
    OpenAICompatibleModel,
)

VALID_PROVIDERS = ("ollama", "openai")


def build_serving_model(
    *,
    use_mock: bool = False,
    provider: str = "ollama",
    model: str = "",
    host: str = "http://localhost:11434",
    base_url: str = "",
    api_key: str = "",
    num_predict: int = 512,
) -> BaseModel:
    """Construct the serving model for the active environment.

    `provider` selects the backend; the remaining args are backend-specific
    (`host` for ollama; `base_url`/`api_key`/`model` for openai-compatible).
    """
    if use_mock:
        return MockBaseModel()
    if provider == "ollama":
        return OllamaBaseModel(model=model, host=host, num_predict=num_predict)
    if provider == "openai":
        if not base_url or not model:
            raise CompositionError(
                "openai provider requires a base URL and model "
                "(set DEQUORUM_MODEL_BASE_URL and DEQUORUM_MODEL)"
            )
        return OpenAICompatibleModel(
            model=model,
            base_url=base_url,
            api_key=api_key,
            num_predict=num_predict,
        )
    raise CompositionError(
        f"unknown model provider {provider!r}; valid: {VALID_PROVIDERS}"
    )
