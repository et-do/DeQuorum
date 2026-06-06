from __future__ import annotations

from dequorum.knowledge.contribution import Contribution


def _make(text: str = "asyncio.create_task schedules onto a loop") -> Contribution:
    return Contribution.create(
        contributor_id="python-async",
        text=text,
        citations=("https://docs.python.org/3/library/asyncio-task.html",),
        signing_key=b"async-key",
    )


def test_create_is_deterministic() -> None:
    a = _make()
    b = _make()
    assert a == b
    assert a.contribution_id == b.contribution_id


def test_different_text_yields_different_id() -> None:
    a = _make("text one")
    b = _make("text two")
    assert a.contribution_id != b.contribution_id


def test_signature_carries_contributor_id() -> None:
    c = _make()
    assert c.signature.node_id == "python-async"


def test_signature_changes_with_key() -> None:
    a = Contribution.create(
        contributor_id="e",
        text="x",
        citations=(),
        signing_key=b"k1",
    )
    b = Contribution.create(
        contributor_id="e",
        text="x",
        citations=(),
        signing_key=b"k2",
    )
    assert a.contribution_id == b.contribution_id
    assert a.signature.digest != b.signature.digest


def test_verify_succeeds_with_contributor_public_key() -> None:
    from dequorum.core.crypto import public_key_for

    c = _make()
    assert c.verify(public_key_for(b"async-key")) is True
    assert c.verify(public_key_for(b"someone-else")) is False


def test_verify_fails_when_content_tampered() -> None:
    from dataclasses import replace

    from dequorum.core.crypto import public_key_for

    c = _make()
    pk = public_key_for(b"async-key")
    # Editing the stored text after signing breaks content integrity, so
    # verification fails even though the signature itself is untouched.
    assert replace(c, text="a malicious rewrite").verify(pk) is False
