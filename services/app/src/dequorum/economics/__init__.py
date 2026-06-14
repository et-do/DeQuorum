"""Unit economics for the kickback model.

Answers the question the whitepaper's §5 leaves open: at what per-query
revenue does the network actually close — i.e. each role's revenue share
covers its real cost, and a positive remainder flows to contributors? The
model is deliberately simple and every assumption is an explicit input, so
it can be re-run with real numbers as they land.
"""

from __future__ import annotations

from dequorum.economics.costmodel import CostModel, RevenueSplit
from dequorum.economics.settlement import (
    Settlement,
    quality_factor_from_feedback,
    settle_query,
)

__all__ = [
    "CostModel",
    "RevenueSplit",
    "Settlement",
    "quality_factor_from_feedback",
    "settle_query",
]
