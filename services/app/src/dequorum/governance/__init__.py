"""Governance: stress-test the vote aggregation that gates which contributions
ground answers.

The falsehood-propagation benchmark shows the model adopts whatever a grounded
contribution asserts — true or false. Correctness therefore rests entirely on
governance keeping false contributions out of the approved corpus. This package
simulates that layer under sybil attack so the whitepaper can state how much
abuse it withstands, rather than assuming it works.
"""

from dequorum.governance.sim import (
    SimConfig,
    SimResult,
    attack_threshold,
    simulate,
    sweep,
)

__all__ = [
    "SimConfig",
    "SimResult",
    "attack_threshold",
    "simulate",
    "sweep",
]
