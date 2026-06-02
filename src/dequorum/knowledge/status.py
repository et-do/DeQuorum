"""Contribution lifecycle status.

Kept in its own module so `review` and `knowledge` can both import the constants
without forming an import cycle.
"""

from __future__ import annotations

from typing import Final

STATUS_PENDING: Final[str] = "pending"
STATUS_APPROVED: Final[str] = "approved"
STATUS_REJECTED: Final[str] = "rejected"
STATUS_SUPERSEDED: Final[str] = "superseded"

VALID_STATUSES: Final[frozenset[str]] = frozenset(
    {STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_SUPERSEDED}
)
