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


def test_signature_verifies_with_matching_public_key() -> None:
    from dequorum.core.crypto import public_key_for

    sig = Signature.sign(
        node_id="n", signing_key=b"secret", payload={"x": 1}, result="r"
    )
    assert sig.verify(public_key_for(b"secret")) is True
    assert sig.verify(public_key_for(b"other-secret")) is False


def test_tampered_signature_fails_verify() -> None:
    from dataclasses import replace

    from dequorum.core.crypto import public_key_for

    sig = Signature.sign(node_id="n", signing_key=b"secret", payload=1, result=2)
    pk = public_key_for(b"secret")
    assert sig.verify(pk) is True
    # Flipping any signed field invalidates the signature.
    assert replace(sig, output_hash="deadbeef").verify(pk) is False
    assert replace(sig, node_id="m").verify(pk) is False


def test_covers_detects_content_change() -> None:
    sig = Signature.sign(node_id="n", signing_key=b"k", payload={"x": 1}, result="r")
    assert sig.covers(payload={"x": 1}, result="r") is True
    assert sig.covers(payload={"x": 2}, result="r") is False
    assert sig.covers(payload={"x": 1}, result="r2") is False
