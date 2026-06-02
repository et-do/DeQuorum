from __future__ import annotations

import pytest

from dequorum.core.errors import MissingData
from dequorum.core.node import Node, Signature


class _Lookup(Node):
    def __init__(self, data: dict[str, str]) -> None:
        super().__init__(node_id="lookup", signing_key=b"k")
        self.data = data

    def _answer(self, payload: str) -> str:
        if payload not in self.data:
            raise MissingData(payload)
        return self.data[payload]


def test_signature_is_deterministic() -> None:
    sig_a = Signature.sign(node_id="n", signing_key=b"k", payload={"x": 1}, result="r")
    sig_b = Signature.sign(node_id="n", signing_key=b"k", payload={"x": 1}, result="r")
    assert sig_a == sig_b


def test_signature_changes_with_key() -> None:
    sig_a = Signature.sign(node_id="n", signing_key=b"k1", payload=1, result=2)
    sig_b = Signature.sign(node_id="n", signing_key=b"k2", payload=1, result=2)
    assert sig_a.digest != sig_b.digest


def test_node_query_returns_signed_result() -> None:
    node = _Lookup({"a": "alpha"})
    result = node.query("a")
    assert result.value == "alpha"
    assert result.signature.node_id == "lookup"
    assert result.signature.digest


def test_missing_data_raises() -> None:
    node = _Lookup({"a": "alpha"})
    with pytest.raises(MissingData):
        node.query("z")
