from __future__ import annotations

from dequorum.core import crypto


def test_keypair_roundtrip() -> None:
    sk = crypto.generate_signing_key()
    pk = crypto.public_key_for(sk)
    assert len(sk) == 32
    assert len(pk) == 32
    msg = b"the message"
    sig = crypto.sign(sk, msg)
    assert len(sig) == 64
    assert crypto.verify(pk, msg, sig) is True


def test_verify_rejects_tampered_message() -> None:
    sk = crypto.generate_signing_key()
    pk = crypto.public_key_for(sk)
    sig = crypto.sign(sk, b"original")
    assert crypto.verify(pk, b"tampered", sig) is False


def test_verify_rejects_wrong_key() -> None:
    sig = crypto.sign(b"material-a", b"msg")
    assert crypto.verify(crypto.public_key_for(b"material-b"), b"msg", sig) is False


def test_signing_is_deterministic() -> None:
    # Ed25519 (RFC 8032) is deterministic, and our material→seed fold is too,
    # so the same material + message always yields the same signature/key.
    assert crypto.sign(b"m", b"msg") == crypto.sign(b"m", b"msg")
    assert crypto.public_key_for(b"m") == crypto.public_key_for(b"m")


def test_arbitrary_length_material_works() -> None:
    # Callers pass short literals, slug-derived bytes, or 32-byte secrets;
    # all are folded to a valid seed and produce a usable keypair.
    for material in (b"k", b"async-key", b"x" * 1, b"y" * 100):
        pk = crypto.public_key_for(material)
        sig = crypto.sign(material, b"hello")
        assert crypto.verify(pk, b"hello", sig) is True


def test_verify_never_raises_on_garbage() -> None:
    assert crypto.verify(b"not-a-key", b"msg", b"not-a-sig") is False
