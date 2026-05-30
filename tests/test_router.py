from __future__ import annotations

import pytest

from ai_playground.experts import Expert, ExpertRegistry
from ai_playground.router import KeywordRouter


def _expert(eid: str, tags: tuple[str, ...]) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=eid,
        specialty_tags=tags,
        system_prompt=f"prompt-{eid}",
        signing_key=eid.encode(),
    )


def _registry(*experts: Expert) -> ExpertRegistry:
    r = ExpertRegistry()
    for e in experts:
        r.register(e)
    return r


def test_routes_to_matching_expert() -> None:
    reg = _registry(
        _expert("py", ("python", "typing")),
        _expert("rs", ("rust", "ownership")),
    )
    result = KeywordRouter(reg).route("how do I add types to a python function?")
    assert result.fallback_used is False
    assert tuple(e.expert_id for e in result.selected) == ("py",)
    assert "python" in result.matched_tags


def test_ranks_by_overlap_count() -> None:
    reg = _registry(
        _expert("a", ("python",)),
        _expert("b", ("python", "typing", "annotations")),
    )
    result = KeywordRouter(reg).route("python typing annotations", top_k=2)
    assert tuple(e.expert_id for e in result.selected) == ("b", "a")


def test_top_k_limits_results() -> None:
    reg = _registry(
        _expert("a", ("python",)),
        _expert("b", ("python",)),
        _expert("c", ("python",)),
    )
    result = KeywordRouter(reg).route("python", top_k=2)
    assert len(result.selected) == 2


def test_fallback_to_all_when_no_match() -> None:
    reg = _registry(
        _expert("a", ("python",)),
        _expert("b", ("rust",)),
    )
    router = KeywordRouter(reg, fallback_to_all=True)
    result = router.route("explain quantum chromodynamics", top_k=3)
    assert result.fallback_used is True
    assert len(result.selected) == 2


def test_no_fallback_returns_empty() -> None:
    reg = _registry(_expert("a", ("python",)))
    result = KeywordRouter(reg, fallback_to_all=False).route("zzz", top_k=3)
    assert result.fallback_used is False
    assert result.selected == ()


def test_top_k_must_be_positive() -> None:
    reg = _registry(_expert("a", ("python",)))
    with pytest.raises(ValueError):
        KeywordRouter(reg).route("python", top_k=0)
