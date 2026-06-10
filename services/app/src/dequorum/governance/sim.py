"""Adversarial governance simulation (pure-Python, deterministic).

We model the live mechanism in `review/service.py`: each voter casts -1/0/+1,
votes are summed, and a contribution is approved once the net tally clears a
threshold. The only thing under test is whether that aggregation keeps FALSE
contributions out of the approved corpus when an attacker spins up sybil
accounts to upvote them — because an approved false contribution grounds answers
and, per the falsehood-propagation benchmark, the model will repeat the lie.

Two aggregation rules are compared:

* ``flat`` — one account, one vote (the rule shipping today). An attacker's power
  scales linearly with the number of sybil accounts, which are cheap to create.
* ``reputation`` — each vote is weighted by the caller's reputation. Established
  honest accounts weigh 1.0; freshly-spun sybils weigh ``sybil_reputation`` < 1
  because reputation must be earned (stake / history / prior accepted work). This
  raises the attacker's cost by ``1 / sybil_reputation``.

Voters are imperfect: an honest voter judges a contribution correctly with
probability ``honest_accuracy`` and is otherwise wrong, modelling a noisy but
truth-correlated crowd. Sybils are a worst-case adversary: they always upvote
false contributions and downvote true ones.

The headline safety metric is ``false_approval_rate`` — the share of FALSE
contributions that reach the approved corpus. It must stay at zero; anything
above zero is a contribution that will ground a false answer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Final

# The live mechanism approves at net tally >= +2 (review/service.service). At
# population scale the exact integer threshold is immaterial next to the honest
# margin; we keep it configurable but default to the shipping value.
DEFAULT_APPROVAL_THRESHOLD: Final[float] = 2.0


@dataclass(frozen=True, slots=True)
class SimConfig:
    """One scenario for the governance simulator.

    ``sybil_fraction`` is expressed relative to the honest electorate, so the
    sybil head-count is ``round(n_honest * sybil_fraction)`` — a fraction of 1.0
    means the attacker fielded as many accounts as there are honest voters.
    """

    n_true: int = 60
    n_false: int = 60
    n_honest: int = 50
    honest_accuracy: float = 0.8
    sybil_fraction: float = 0.0
    sybil_reputation: float = 0.1
    approval_threshold: float = DEFAULT_APPROVAL_THRESHOLD
    rule: str = "flat"  # "flat" | "reputation"
    seed: int = 0


@dataclass(frozen=True, slots=True)
class SimResult:
    rule: str
    sybil_fraction: float
    n_sybil: int
    true_approval_rate: float  # utility: TRUE contributions that get approved
    false_approval_rate: float  # SAFETY: FALSE contributions that slip through
    accuracy: float  # overall correct decisions (approve-true + reject-false)


def _honest_weight(rule: str) -> float:
    if rule in ("flat", "reputation"):
        return 1.0
    raise ValueError(f"unknown rule: {rule!r}")


def _sybil_weight(rule: str, sybil_reputation: float) -> float:
    if rule == "flat":
        return 1.0
    if rule == "reputation":
        return sybil_reputation
    raise ValueError(f"unknown rule: {rule!r}")


def _approved(is_true: bool, cfg: SimConfig, n_sybil: int, rng: Random) -> bool:
    """Tally one contribution and decide whether it reaches the approved corpus."""
    honest_w = _honest_weight(cfg.rule)
    sybil_w = _sybil_weight(cfg.rule, cfg.sybil_reputation)

    score = 0.0
    for _ in range(cfg.n_honest):
        correct = rng.random() < cfg.honest_accuracy
        believes_true = is_true if correct else (not is_true)
        score += honest_w * (1 if believes_true else -1)

    # Sybils vote in lockstep: upvote false (+1), downvote true (-1).
    score += sybil_w * n_sybil * (-1 if is_true else 1)
    return score >= cfg.approval_threshold


def simulate(config: SimConfig) -> SimResult:
    """Run one scenario and return approval rates + overall accuracy."""
    rng = Random(config.seed)
    n_sybil = round(config.n_honest * config.sybil_fraction)

    true_decisions = [
        _approved(True, config, n_sybil, rng) for _ in range(config.n_true)
    ]
    false_decisions = [
        _approved(False, config, n_sybil, rng) for _ in range(config.n_false)
    ]

    n_items = config.n_true + config.n_false
    correct = sum(true_decisions) + sum(not d for d in false_decisions)
    return SimResult(
        rule=config.rule,
        sybil_fraction=config.sybil_fraction,
        n_sybil=n_sybil,
        true_approval_rate=_rate(true_decisions),
        false_approval_rate=_rate(false_decisions),
        accuracy=correct / n_items if n_items else 0.0,
    )


def sweep(
    base: SimConfig,
    fractions: list[float],
    rules: list[str],
) -> list[SimResult]:
    """Run the same scenario across rules x sybil fractions."""
    out: list[SimResult] = []
    for rule in rules:
        for frac in fractions:
            out.append(simulate(replace(base, rule=rule, sybil_fraction=frac)))
    return out


def attack_threshold(results: list[SimResult]) -> float | None:
    """The smallest sybil fraction at which any FALSE contribution gets approved.

    This is the attacker's break-in point: below it, governance keeps every lie
    out; at or above it, falsehoods start reaching the corpus. ``None`` means no
    tested fraction broke the layer.
    """
    breaches = [r.sybil_fraction for r in results if r.false_approval_rate > 0.0]
    return min(breaches) if breaches else None


def _rate(decisions: list[bool]) -> float:
    return sum(decisions) / len(decisions) if decisions else 0.0
