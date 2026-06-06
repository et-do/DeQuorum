"""Ed25519 signing primitives.

DeQuorum's accountability claim — "every answer ships with a proof chain
anyone can verify with only public keys, no trust in the operator's
storage" — requires asymmetric signatures. This module is the single place
that knows how to turn key material into a keypair, sign a message, and
verify a signature against a public key.

Key material vs. seed. Callers pass a `signing_key: bytes` of arbitrary
length (random 32-byte secrets in production, short literals in tests,
slug-derived bytes in dev seeds). We deterministically fold any material
into the 32-byte seed Ed25519 requires via BLAKE2b, so the same material
always yields the same keypair. `public_key_for(material)` and
`sign(material, ...)` apply the identical fold, so a public key derived
from material verifies signatures produced from that material.
"""

from __future__ import annotations

from hashlib import blake2b

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

_SEED_SIZE = 32


def _seed(material: bytes) -> bytes:
    """Fold arbitrary key material into the 32-byte Ed25519 seed."""
    return blake2b(material, digest_size=_SEED_SIZE).digest()


def _private_key(material: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_seed(material))


def generate_signing_key() -> bytes:
    """Return fresh 32 bytes of random signing-key material."""
    # The raw seed of a freshly generated key is itself good random
    # material; callers treat the return value as their private key.
    return Ed25519PrivateKey.generate().private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )


def public_key_for(signing_key: bytes) -> bytes:
    """Derive the 32-byte Ed25519 public (verification) key from material."""
    return (
        _private_key(signing_key)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
    )


def sign(signing_key: bytes, message: bytes) -> bytes:
    """Produce a 64-byte Ed25519 signature over `message`."""
    return _private_key(signing_key).sign(message)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """True iff `signature` is a valid Ed25519 signature over `message`
    under `public_key`. Never raises — a malformed key/signature is just
    an unverified result."""
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False
