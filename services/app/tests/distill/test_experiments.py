from __future__ import annotations

from dequorum.distill.experiments import (
    attributable_fraction,
    entanglement_score,
    forgetting_tax,
    knowledge_gain,
)


def test_attributable_fraction() -> None:
    # learned 0->1; removing own contributor takes it back to 0 → fully owned
    assert attributable_fraction(base=0.0, with_all=1.0, without_own=0.0) == 1.0
    # removing own contributor changes nothing → not attributable to it
    assert attributable_fraction(base=0.0, with_all=1.0, without_own=1.0) == 0.0
    # never learned → 0 by definition
    assert attributable_fraction(base=0.5, with_all=0.5, without_own=0.0) == 0.0


def test_entanglement_clean_diagonal_is_zero() -> None:
    # removing contributor i zeroes fact i and leaves others untouched
    all_recall = [1.0, 1.0, 1.0]
    minus = [
        [0.0, 1.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 0.0],
    ]
    assert entanglement_score(all_recall, minus) == 0.0


def test_entanglement_detects_off_diagonal_disturbance() -> None:
    all_recall = [1.0, 1.0]
    # removing contributor 0 also wrecks fact 1 → entangled
    minus = [
        [0.0, 0.0],
        [1.0, 0.0],
    ]
    assert entanglement_score(all_recall, minus) > 0.0


def test_gain_and_forgetting() -> None:
    assert abs(knowledge_gain([0.0, 0.0], [1.0, 0.5]) - 0.75) < 1e-9
    assert abs(forgetting_tax([1.0, 1.0], [0.8, 1.0]) - (-0.1)) < 1e-9
