from __future__ import annotations

import pytest

from dequorum.category.composition import Morphism, compose
from dequorum.core.errors import MissingData
from dequorum.core.node import Node


class _Add(Node):
    def __init__(self, node_id: str, n: int) -> None:
        super().__init__(node_id=node_id, signing_key=node_id.encode())
        self.n = n

    def _answer(self, payload: int) -> int:
        return payload + self.n


class _Halt(Node):
    def __init__(self) -> None:
        super().__init__(node_id="halt", signing_key=b"halt")

    def _answer(self, payload: int) -> int:
        raise MissingData("halt always fails")


def test_compose_chains_morphisms_left_to_right() -> None:
    proof = compose(
        0,
        Morphism(_Add("a", 1)),
        Morphism(_Add("b", 2)),
        Morphism(_Add("c", 3)),
    )
    assert proof.output == 6
    assert proof.node_ids == ("a", "b", "c")


def test_compose_chain_length_matches_morphism_count() -> None:
    proof = compose(0, Morphism(_Add("a", 1)), Morphism(_Add("b", 2)))
    assert len(proof.chain) == 2


def test_compose_propagates_missing_data() -> None:
    with pytest.raises(MissingData):
        compose(0, Morphism(_Add("a", 1)), Morphism(_Halt()))


def test_compose_requires_at_least_one_morphism() -> None:
    with pytest.raises(ValueError):
        compose(0)
