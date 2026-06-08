"""Pure helpers for the sovereignty-feasibility distillation experiments.

The compute-heavy training/generation lives in `poc.py` and is driven from the
CLI; the analysis primitives here are import-light and unit-tested.

Vocabulary (per fact j, all measured as gold-fact recall):
  base[j]        — recall from the bare base model (no adapter)
  all[j]         — recall after training on the full corpus
  minus[i][j]    — recall after training with contributor i's examples removed

From these:
  - per-fact attribution: how much of fact j's learned presence is owed to its
    own contributor (diagonal i==j), via leave-one-contributor-out.
  - entanglement: how much removing contributor i disturbs *other* facts
    (off-diagonal i!=j). High entanglement means knowledge is not cleanly
    attributable to a single contributor — the result that would undermine
    certifiable ownership.
"""

from __future__ import annotations


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def attributable_fraction(*, base: float, with_all: float, without_own: float) -> float:
    """Share of a fact's learned presence traceable to its own contributor.

    (with_all - without_own) / (with_all - base), clamped to [0, 1]; 0 when the
    fact was not learned at all (no gain over base)."""
    learned = with_all - base
    if learned <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, (with_all - without_own) / learned))


def entanglement_score(
    all_recall: list[float], minus_recall: list[list[float]]
) -> float:
    """Mean absolute disturbance to *other* facts when a contributor is removed.

    `minus_recall[i][j]` is recall of fact j after removing contributor i.
    Averages |minus_recall[i][j] - all_recall[j]| over all i != j. ~0 means
    removing one contributor leaves the others' knowledge intact (clean
    attribution); larger means cross-contributor entanglement."""
    n = len(all_recall)
    diffs = [
        abs(minus_recall[i][j] - all_recall[j])
        for i in range(n)
        for j in range(n)
        if i != j
    ]
    return _mean(diffs)


def knowledge_gain(base_recall: list[float], all_recall: list[float]) -> float:
    """Mean recall lift from training the corpus into the weights."""
    return _mean(all_recall) - _mean(base_recall)


def forgetting_tax(control_base: list[float], control_after: list[float]) -> float:
    """Change in recall on a held-out control set (knowledge the base already
    had) after training on the corpus. Negative = the model forgot."""
    return _mean(control_after) - _mean(control_base)
