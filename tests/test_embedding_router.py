from __future__ import annotations

from dequorum.experts import Expert, ExpertRegistry
from dequorum.routing import EmbeddingRouter, KeywordRouter
from dequorum.routing.embedder import HashEmbedder


def _expert(
    eid: str,
    prompt: str,
    tags: tuple[str, ...] = (),
    example_questions: tuple[str, ...] = (),
) -> Expert:
    return Expert(
        expert_id=eid,
        display_name=eid.title(),
        specialty_tags=tags,
        system_prompt=prompt,
        signing_key=eid.encode(),
        example_questions=example_questions,
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


# --- fallback router behavior ---


def test_fallback_kicks_in_when_no_expert_clears_threshold() -> None:
    reg = _registry(
        _expert("py", "python typing things", tags=("python", "typing")),
    )
    embedder = HashEmbedder(dimension=128)
    # Threshold so high no embedding score will clear it
    fallback = KeywordRouter(reg, fallback_to_all=False, min_score=1.0)
    router = EmbeddingRouter(reg, embedder, min_score=0.99, fallback=fallback)

    # Query has a tag match → keyword fallback fires
    result = router.route("python annotations")
    assert result.fallback_used is True
    assert result.method == "embedding+keyword"
    assert len(result.selected) == 1
    assert result.selected[0].expert.expert_id == "py"


def test_fallback_does_not_fire_when_embedding_succeeds() -> None:
    reg = _registry(
        _expert("py", "python typing things", tags=("python", "typing")),
    )
    embedder = HashEmbedder(dimension=128)
    fallback = KeywordRouter(reg, fallback_to_all=False, min_score=1.0)
    router = EmbeddingRouter(reg, embedder, min_score=0.0, fallback=fallback)

    result = router.route("python typing")
    assert result.fallback_used is False
    assert result.method == "embedding"


def test_no_fallback_means_empty_selection_on_threshold_miss() -> None:
    reg = _registry(_expert("py", "python"))
    router = EmbeddingRouter(
        reg, HashEmbedder(dimension=128), min_score=0.99, fallback=None
    )
    result = router.route("unrelated query about cooking pasta")
    assert result.selected == ()
    assert result.fallback_used is False


# --- example_questions in profile ---


def test_example_questions_influence_routing_score() -> None:
    reg = _registry(
        _expert(
            "py-async",
            "python concurrency things",
            tags=("python", "async"),
            example_questions=(
                "How does asyncio.create_task differ from awaiting directly?",
                "When should I use trio's nursery instead of asyncio?",
            ),
        ),
        _expert(
            "py-typing",
            "python typing things",
            tags=("python", "typing"),
            example_questions=("How do I type a generator function?",),
        ),
    )
    router = EmbeddingRouter(reg, HashEmbedder(dimension=256), min_score=0.0)
    # Query closely matches one of py-async's example questions
    result = router.route("Should I use trio's nursery or asyncio?", top_k=2)
    # py-async should score higher because the example question phrasing matches
    by_id = {s.expert.expert_id: s.score for s in result.selected}
    assert by_id["py-async"] > by_id["py-typing"]
