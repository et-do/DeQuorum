"""Invariant 4: adding an unrelated node never silently changes existing outputs."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from dequorum.graph.routing import KnowledgeGraph


def _two_step_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_fact("a", "rel", "b", source_node_id="src1", signing_key=b"k1")
    g.add_fact("b", "rel", "c", source_node_id="src2", signing_key=b"k2")
    return g


@given(
    extra_src=st.text(min_size=1, max_size=8),
    extra_subject=st.text(min_size=1, max_size=8),
    extra_object=st.text(min_size=1, max_size=8),
)
def test_unrelated_edge_does_not_alter_existing_route(
    extra_src: str, extra_subject: str, extra_object: str
) -> None:
    if extra_subject in {"a", "b", "c"} or extra_object in {"a", "b", "c"}:
        return
    if extra_subject == extra_object:
        return

    base = _two_step_graph().route("a", "c")

    augmented = _two_step_graph()
    augmented.add_fact(
        extra_subject,
        "rel",
        extra_object,
        source_node_id=extra_src,
        signing_key=extra_src.encode(),
    )
    after = augmented.route("a", "c")

    assert base.chain == after.chain
    assert base.output == after.output


def test_appending_morphism_only_extends_chain() -> None:
    from dequorum.category.composition import Morphism, compose
    from dequorum.core.node import Node

    class _Inc(Node):
        def __init__(self, node_id: str) -> None:
            super().__init__(node_id=node_id, signing_key=node_id.encode())

        def _answer(self, payload: int) -> int:
            return payload + 1

    p_short = compose(0, Morphism(_Inc("a")), Morphism(_Inc("b")))
    p_long = compose(0, Morphism(_Inc("a")), Morphism(_Inc("b")), Morphism(_Inc("c")))

    assert p_long.chain[: len(p_short.chain)] == p_short.chain
