from __future__ import annotations

from ai_playground.embedder import HashEmbedder
from ai_playground.experts import Expert, ExpertRegistry
from ai_playground.router import EmbeddingRouter


def _expert(eid: str, prompt: str, tags: tuple[str, ...] = ()) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=eid.title(),
        specialty_tags=tags,
        system_prompt=prompt,
        signing_key=eid.encode(),
    )


def _registry(*experts: Expert) -> ExpertRegistry:
    r = ExpertRegistry()
    for e in experts:
        r.register(e)
    return r


def test_picks_semantically_relevant_expert() -> None:
    reg = _registry(
        _expert("py", "python typing generators yields returns annotations"),
        _expert("rs", "rust ownership borrow checker lifetimes"),
    )
    router = EmbeddingRouter(reg, HashEmbedder(dimension=256), min_score=0.0)
    result = router.route("python typing", top_k=1)
    assert len(result.selected) == 1
    assert result.selected[0].expert.expert_id == "py"


def test_routing_scores_are_attached() -> None:
    reg = _registry(
        _expert("py", "python typing generators"),
        _expert("rs", "rust ownership borrow"),
    )
    router = EmbeddingRouter(reg, HashEmbedder(dimension=128), min_score=0.0)
    result = router.route("python typing", top_k=2)
    for s in result.selected:
        assert isinstance(s.score, float)
    # py should outscore rs on a python query
    by_id = {s.expert.expert_id: s.score for s in result.selected}
    assert by_id["py"] > by_id["rs"]


def test_threshold_filter_drops_irrelevant_experts() -> None:
    reg = _registry(
        _expert("py", "python typing"),
        _expert("rs", "rust ownership"),
    )
    # Very high threshold → nothing passes
    router = EmbeddingRouter(reg, HashEmbedder(dimension=128), min_score=0.99)
    result = router.route("completely unrelated query about cooking pasta")
    assert result.selected == ()
    assert result.fallback_used is False


def test_empty_registry_returns_empty() -> None:
    router = EmbeddingRouter(ExpertRegistry(), HashEmbedder(dimension=32))
    result = router.route("anything")
    assert result.selected == ()


def test_method_label() -> None:
    router = EmbeddingRouter(
        _registry(_expert("a", "stuff")), HashEmbedder(dimension=32)
    )
    result = router.route("stuff", top_k=1)
    assert result.method == "embedding"


def test_rebuild_picks_up_new_experts() -> None:
    reg = ExpertRegistry()
    reg.register(_expert("a", "alpha topic"))
    router = EmbeddingRouter(reg, HashEmbedder(dimension=64), min_score=0.0)
    reg.register(_expert("b", "beta topic"))
    router.rebuild()
    result = router.route("alpha beta", top_k=2)
    assert {s.expert.expert_id for s in result.selected} == {"a", "b"}
