from __future__ import annotations

import pytest

from dequorum.inference.models import (
    BASE_MODEL_REGISTRY,
    DEFAULT_BASE_MODEL_ID,
    OPEN_LICENSES,
    Domain,
    License,
    default_profile,
    get_profile,
    open_profiles,
    resolve_ollama_tag,
)


def test_default_model_id_is_registered() -> None:
    assert DEFAULT_BASE_MODEL_ID in BASE_MODEL_REGISTRY


def test_default_model_is_open_licensed() -> None:
    # If this ever fails, we're shipping a default that violates DeQuorum's
    # license-purity rule (see docs/PRODUCT.md "Principles" + the open_licenses set).
    assert default_profile().is_open


def test_default_profile_returns_default_model_id() -> None:
    assert default_profile().model_id == DEFAULT_BASE_MODEL_ID


def test_every_registered_profile_has_consistent_id() -> None:
    for key, profile in BASE_MODEL_REGISTRY.items():
        assert key == profile.model_id


def test_open_profiles_only_returns_open_licenses() -> None:
    profiles = open_profiles()
    assert profiles, "expected at least one open-license model in the registry"
    for p in profiles:
        assert p.license in OPEN_LICENSES


def test_get_profile_raises_on_unknown_id() -> None:
    with pytest.raises(KeyError, match="unknown model_id"):
        get_profile("definitely-not-a-real-model")


def test_get_profile_returns_correct_profile() -> None:
    p = get_profile(DEFAULT_BASE_MODEL_ID)
    assert p.model_id == DEFAULT_BASE_MODEL_ID


def test_resolve_ollama_tag_accepts_registered_id() -> None:
    expected = default_profile().ollama_tag
    assert resolve_ollama_tag(DEFAULT_BASE_MODEL_ID) == expected


def test_resolve_ollama_tag_passes_through_raw_tags() -> None:
    # Anything not in the registry is treated as a raw Ollama tag — escape hatch.
    assert resolve_ollama_tag("llama3:70b-custom") == "llama3:70b-custom"


def test_every_profile_has_positive_context_window() -> None:
    for p in BASE_MODEL_REGISTRY.values():
        assert p.context_window_tokens > 0


def test_retrieval_budget_is_fraction_of_context() -> None:
    for p in BASE_MODEL_REGISTRY.values():
        assert 0 < p.retrieval_token_budget < p.context_window_tokens


def test_swap_default_takes_effect_in_ollama_base_model() -> None:
    """OllamaBaseModel with empty `model` should resolve to whatever the current
    DEFAULT_BASE_MODEL_ID is. This is the property that makes a registry swap
    work without code changes."""
    from dequorum.inference.base_model import OllamaBaseModel

    bm = OllamaBaseModel()
    assert bm._resolved_tag() == default_profile().ollama_tag


def test_swap_via_registered_id_resolves_to_that_tag() -> None:
    from dequorum.inference.base_model import OllamaBaseModel

    bm = OllamaBaseModel(model="mistral-7b-instruct-v0.3")
    assert bm._resolved_tag() == get_profile("mistral-7b-instruct-v0.3").ollama_tag


def test_registry_includes_multiple_domains_so_swap_choice_is_meaningful() -> None:
    domains = {p.domain for p in BASE_MODEL_REGISTRY.values()}
    assert Domain.CODE in domains
    assert Domain.GENERAL in domains


def test_registry_includes_at_least_one_non_qwen_alternative() -> None:
    # If we ever end up with a registry that's all-Qwen, the swap mechanism
    # exists in theory but offers no real options. Guard against drift.
    families = {p.model_id.split("-")[0] for p in BASE_MODEL_REGISTRY.values()}
    assert len(families) >= 2


def test_license_enum_string_values_match_brand_names() -> None:
    # If we serialize license to JSON these strings show up in API responses.
    assert License.APACHE_2_0.value == "Apache-2.0"
    assert License.MIT.value == "MIT"
