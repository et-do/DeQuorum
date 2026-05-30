"""Deterministic canonicalization and hashing for provenance."""

from __future__ import annotations

import json
from hashlib import blake2b
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Return a stable byte representation of `value` for hashing."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return encoded.encode()


def digest(payload: bytes, *, key: bytes = b"", size: int = 16) -> str:
    return blake2b(payload, key=key, digest_size=size).hexdigest()
