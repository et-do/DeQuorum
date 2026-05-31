"""Errors that enforce the explicit-failure invariant (no hallucination)."""

from __future__ import annotations


class CompositionError(Exception):
    """Raised when an architecture cannot compose a verifiable answer."""


class MissingData(CompositionError):  # noqa: N818
    """Raised by a node when it has no entry for the requested payload."""
