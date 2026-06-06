"""Base model registry: one source of truth for every supported base LLM.

Swapping the network's base model is a single config change: bump
DEFAULT_BASE_MODEL_ID to the new entry's id. The CLI, web app, and benchmark
all read from this registry; nothing else hardcodes a model tag.

Adding a new model = appending a `BaseModelProfile` to `_REGISTRY` with its
license, context window, instruct format, and recommended use case. Anything
the rest of the codebase needs to know about a model lives on the profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class License(StrEnum):
    """Licenses we consider truly-open vs. restricted, per docs/PRODUCT.md."""

    APACHE_2_0 = "Apache-2.0"
    MIT = "MIT"
    LLAMA_COMMUNITY = "Meta-Llama-Community"  # restricted (700M MAU + derivative trap)
    GEMMA_TERMS = "Gemma-Terms-of-Use"  # restricted (derivative trap)
    QWEN_CUSTOM = "Qwen-Custom"  # restricted on 72B+ only; Apache on 7B/14B/32B
    DEEPSEEK_CUSTOM = "DeepSeek-Custom"  # restricted (derivative trap)


# Licenses that satisfy DeQuorum's "no tech-giant restriction" purity rule.
# A swap to a non-OPEN license would compromise the Stage-2 path (fine-tune
# the base on contributor data). Surfacing the rule here makes that explicit.
OPEN_LICENSES: Final[frozenset[License]] = frozenset({License.APACHE_2_0, License.MIT})


class Domain(StrEnum):
    """What the model was trained or tuned for. Drives benchmark profile + UX hints."""

    GENERAL = "general"
    CODE = "code"
    MATH = "math"
    MULTIMODAL = "multimodal"


class InstructFormat(StrEnum):
    """The chat template a model expects. The Ollama API handles most of this
    transparently, but some places we need to know (e.g. prompt assembly for
    streaming, or providers other than Ollama)."""

    OPENAI_CHAT = "openai-chat"  # {role, content} array
    QWEN_CHATML = "qwen-chatml"
    LLAMA3 = "llama3"
    MISTRAL = "mistral"


@dataclass(frozen=True, slots=True)
class BaseModelProfile:
    """Everything the network needs to know about a candidate base model."""

    model_id: str  # internal stable id, e.g. "qwen2.5-coder-7b"
    display_name: str
    ollama_tag: str  # what to pass to Ollama, e.g. "qwen2.5-coder:7b"
    huggingface_id: str
    license: License
    parameter_count_billions: float
    context_window_tokens: int
    instruct_format: InstructFormat
    domain: Domain
    rationale: str  # one sentence: why this model is in the registry

    @property
    def is_open(self) -> bool:
        """True iff the model's license satisfies DeQuorum's openness rule."""
        return self.license in OPEN_LICENSES

    @property
    def retrieval_token_budget(self) -> int:
        """How many tokens of retrieved contributions to budget per query.

        We reserve roughly 60% of the context window for retrieved context and
        leave the rest for system prompt + user query + generated response.
        """
        return int(self.context_window_tokens * 0.6)


_REGISTRY: Final[tuple[BaseModelProfile, ...]] = (
    BaseModelProfile(
        model_id="qwen2.5-coder-3b",
        display_name="Qwen 2.5 Coder 3B",
        ollama_tag="qwen2.5-coder:3b",
        huggingface_id="Qwen/Qwen2.5-Coder-3B-Instruct",
        license=License.APACHE_2_0,
        parameter_count_billions=3.0,
        context_window_tokens=32_768,
        instruct_format=InstructFormat.QWEN_CHATML,
        domain=Domain.CODE,
        rationale=(
            "Half the size of Qwen Coder 7B. Tolerable on CPU (~25 tok/s) "
            "and snappy on any consumer GPU. Use as a dev / fast-mode "
            "fallback when the production-target model is GPU-constrained."
        ),
    ),
    BaseModelProfile(
        model_id="qwen2.5-coder-7b",
        display_name="Qwen 2.5 Coder 7B",
        ollama_tag="qwen2.5-coder:7b",
        huggingface_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        license=License.APACHE_2_0,
        parameter_count_billions=7.0,
        context_window_tokens=32_768,
        instruct_format=InstructFormat.QWEN_CHATML,
        domain=Domain.CODE,
        rationale=(
            "Strong on code, Apache-2.0, runs comfortably at Q4 on a 16 GB host. "
            "Current default while the network is seeded primarily with code content."
        ),
    ),
    BaseModelProfile(
        model_id="qwen2.5-7b-instruct",
        display_name="Qwen 2.5 7B Instruct",
        ollama_tag="qwen2.5:7b-instruct",
        huggingface_id="Qwen/Qwen2.5-7B-Instruct",
        license=License.APACHE_2_0,
        parameter_count_billions=7.0,
        context_window_tokens=32_768,
        instruct_format=InstructFormat.QWEN_CHATML,
        domain=Domain.GENERAL,
        rationale=(
            "Same license / size / context window as Qwen Coder, but generalist. "
            "Recommended target once the network has cross-domain contributions."
        ),
    ),
    BaseModelProfile(
        model_id="mistral-7b-instruct-v0.3",
        display_name="Mistral 7B Instruct v0.3",
        ollama_tag="mistral:7b-instruct",
        huggingface_id="mistralai/Mistral-7B-Instruct-v0.3",
        license=License.APACHE_2_0,
        parameter_count_billions=7.0,
        context_window_tokens=32_768,
        instruct_format=InstructFormat.MISTRAL,
        domain=Domain.GENERAL,
        rationale=(
            "Mature Apache-2.0 generalist baseline. Useful as a second opinion "
            "when measuring whether Qwen-family bias is affecting routing/quality."
        ),
    ),
    BaseModelProfile(
        model_id="phi-4",
        display_name="Phi-4 14B",
        ollama_tag="phi4:14b",
        huggingface_id="microsoft/phi-4",
        license=License.MIT,
        parameter_count_billions=14.0,
        context_window_tokens=16_384,
        instruct_format=InstructFormat.OPENAI_CHAT,
        domain=Domain.GENERAL,
        rationale=(
            "MIT-licensed reasoning specialist; ~2x the params of our 7B baseline. "
            "Pick this when reasoning quality matters more than host hardware budget."
        ),
    ),
    BaseModelProfile(
        model_id="mixtral-8x7b-instruct",
        display_name="Mixtral 8x7B Instruct v0.1",
        ollama_tag="mixtral:8x7b",
        huggingface_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        license=License.APACHE_2_0,
        parameter_count_billions=46.7,
        context_window_tokens=32_768,
        instruct_format=InstructFormat.MISTRAL,
        domain=Domain.GENERAL,
        rationale=(
            "MoE with ~12B active params at inference. Stronger quality than dense 7B "
            "at a higher (but still reasonable) host RAM bar (~30 GB at Q4)."
        ),
    ),
    BaseModelProfile(
        model_id="granite-3.1-8b-instruct",
        display_name="IBM Granite 3.1 8B Instruct",
        ollama_tag="granite3.1-dense:8b",
        huggingface_id="ibm-granite/granite-3.1-8b-instruct",
        license=License.APACHE_2_0,
        parameter_count_billions=8.0,
        context_window_tokens=128_000,
        instruct_format=InstructFormat.OPENAI_CHAT,
        domain=Domain.GENERAL,
        rationale=(
            "Apache-2.0, trained on permissively-licensed data only, 128k context. "
            "The largest retrieval budget of any 8B-class candidate."
        ),
    ),
)


BASE_MODEL_REGISTRY: Final[dict[str, BaseModelProfile]] = {
    p.model_id: p for p in _REGISTRY
}


DEFAULT_BASE_MODEL_ID: Final[str] = "qwen2.5-coder-7b"
"""The base model the CLI / web / benchmark use unless an override is passed.

Swap procedure: change this to the new model_id, ensure that model_id exists
in BASE_MODEL_REGISTRY, and re-run the benchmark (`dequorum benchmark`) to
compare before/after. No other code change should be required.
"""


def default_profile() -> BaseModelProfile:
    return BASE_MODEL_REGISTRY[DEFAULT_BASE_MODEL_ID]


def get_profile(model_id: str) -> BaseModelProfile:
    """Resolve a model_id to its profile. Raises KeyError if not registered."""
    if model_id not in BASE_MODEL_REGISTRY:
        raise KeyError(
            f"unknown model_id {model_id!r}; "
            f"registered ids: {sorted(BASE_MODEL_REGISTRY)}"
        )
    return BASE_MODEL_REGISTRY[model_id]


def resolve_ollama_tag(model_id_or_tag: str) -> str:
    """Accept either a model_id or a raw Ollama tag; return the Ollama tag.

    This lets CLI args like `--model qwen2.5-coder-7b` (registered id) and
    `--model llama3:70b-custom` (unregistered raw tag) both work.
    """
    if model_id_or_tag in BASE_MODEL_REGISTRY:
        return BASE_MODEL_REGISTRY[model_id_or_tag].ollama_tag
    return model_id_or_tag


def open_profiles() -> list[BaseModelProfile]:
    """Profiles whose license clears DeQuorum's purity rule (Apache 2.0 / MIT)."""
    return [p for p in BASE_MODEL_REGISTRY.values() if p.is_open]
