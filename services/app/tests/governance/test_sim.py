from __future__ import annotations

from dataclasses import replace

from dequorum.governance import SimConfig, attack_threshold, simulate, sweep


def test_no_sybils_classifies_correctly() -> None:
    """With an honest crowd and no attacker, no false contribution is approved
    and almost every true one is — the layer works when unattacked."""
    r = simulate(SimConfig(seed=0))
    assert r.false_approval_rate == 0.0
    assert r.true_approval_rate > 0.9
    assert r.accuracy > 0.9


def test_flat_voting_collapses_under_sybils() -> None:
    """One-account-one-vote is linear in sybils: enough of them push every lie
    through and reject every truth."""
    r = simulate(SimConfig(seed=0, rule="flat", sybil_fraction=1.0))
    assert r.false_approval_rate == 1.0
    assert r.true_approval_rate == 0.0


def test_reputation_resists_more_sybils_than_flat() -> None:
    """At the same sybil head-count where flat fully fails, reputation weighting
    still keeps false contributions out."""
    flat = simulate(SimConfig(seed=0, rule="flat", sybil_fraction=1.0))
    rep = simulate(SimConfig(seed=0, rule="reputation", sybil_fraction=1.0))
    assert flat.false_approval_rate > rep.false_approval_rate
    assert rep.false_approval_rate == 0.0


def test_attack_threshold_multiplier_matches_inverse_sybil_weight() -> None:
    """The break-in point (first false approval) should scale ~1/sybil_weight:
    halving a sybil's vote weight roughly doubles the accounts needed."""
    base = SimConfig(seed=0, sybil_reputation=0.1)
    fine = [round(0.05 * i, 2) for i in range(0, 101)]  # 0.0 .. 5.0
    results = sweep(base, fine, ["flat", "reputation"])
    flat_t = attack_threshold([r for r in results if r.rule == "flat"])
    rep_t = attack_threshold([r for r in results if r.rule == "reputation"])
    assert flat_t is not None and rep_t is not None
    assert rep_t > flat_t
    multiplier = rep_t / flat_t
    # ~1/0.1 = 10; allow slack for the discrete crowd / sweep granularity.
    assert 6.0 <= multiplier <= 14.0


def test_attack_threshold_none_when_unbroken() -> None:
    """If no tested fraction admits a falsehood, the break-in point is None."""
    results = [simulate(SimConfig(seed=0, sybil_fraction=f)) for f in (0.0, 0.1, 0.2)]
    assert attack_threshold(results) is None


def test_simulation_is_deterministic_for_a_seed() -> None:
    cfg = SimConfig(seed=7, rule="flat", sybil_fraction=0.5)
    assert simulate(cfg) == simulate(replace(cfg))


def test_unknown_rule_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        simulate(SimConfig(seed=0, rule="bogus", sybil_fraction=0.5))
