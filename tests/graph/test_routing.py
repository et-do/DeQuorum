from __future__ import annotations

import pytest

from dequorum.core.errors import CompositionError
from dequorum.graph.routing import KnowledgeGraph


def _stocked() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_fact("a", "rel", "b", source_node_id="src1", signing_key=b"k1")
    g.add_fact("b", "rel", "c", source_node_id="src2", signing_key=b"k2")
    g.add_fact("c", "rel", "d", source_node_id="src3", signing_key=b"k3")
    return g


def test_route_returns_proof_with_per_edge_signature() -> None:
    g = _stocked()
    proof = g.route("a", "d")
    assert proof.output == "d"
    assert proof.node_ids == ("src1", "src2", "src3")


def test_route_raises_when_no_path() -> None:
    g = _stocked()
    g.add_fact("x", "rel", "y", source_node_id="iso", signing_key=b"ki")
    with pytest.raises(CompositionError):
        g.route("a", "y")


def test_route_raises_for_unknown_node() -> None:
    g = _stocked()
    with pytest.raises(CompositionError):
        g.route("a", "zzz")
