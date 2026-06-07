"""Shapley-value attribution — the principled fix for leave-one-out's blind
spot.

LOO under-credits genuinely-valuable-but-redundant content: if two
contributions carry the same fact, removing either one alone changes
nothing, so both look worthless. The Shapley value instead averages a
contribution's marginal contribution over *all orderings* of the set, so
redundant siblings fairly **split** the credit for their shared value
rather than each scoring zero — while a pure duplicate still cannot inflate
a contributor's total beyond the value of the information itself.

The coalition value v(S) is the quality (judge score) of the answer
generated from contribution subset S. Exact for small sets (≤ exact_max_n,
2^n cached evaluations); Monte-Carlo permutation sampling above that.
"""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Callable, Sequence

from dequorum.attribution.marginal import ContributionCredit
from dequorum.inference.base_model import BaseModel
from dequorum.inference.pipeline import _augment_system_prompt
from dequorum.retrieval import ScoredContribution


def shapley_attribution(
    *,
    query: str,
    persona_prompt: str,
    retrieved: Sequence[ScoredContribution],
    model: BaseModel,
    score_answer: Callable[[str], float],
    exact_max_n: int = 6,
    n_permutations: int = 64,
    seed: int = 0,
) -> list[ContributionCredit]:
    """Shapley credit per contribution. `score_answer` maps a generated
    answer to a scalar quality in [0, 1] (e.g. a judge vs gold facts).
    The returned `marginal_value` holds the Shapley estimate; `credit_weight`
    normalizes the non-negative part to a share of 1."""
    contribs = [sc.contribution for sc in retrieved]
    n = len(contribs)
    if n == 0:
        return []

    ids = [c.contribution_id for c in contribs]
    cache: dict[frozenset[str], float] = {}

    def value(subset_idx: tuple[int, ...]) -> float:
        key = frozenset(ids[i] for i in subset_idx)
        if key not in cache:
            subset = tuple(contribs[i] for i in subset_idx)
            answer = model.complete(
                system=_augment_system_prompt(persona_prompt, subset), user=query
            )
            cache[key] = score_answer(answer)
        return cache[key]

    phi = [0.0] * n
    if n <= exact_max_n:
        for i in range(n):
            rest = [j for j in range(n) if j != i]
            for r in range(len(rest) + 1):
                for combo in itertools.combinations(rest, r):
                    weight = (
                        math.factorial(len(combo))
                        * math.factorial(n - len(combo) - 1)
                        / math.factorial(n)
                    )
                    phi[i] += weight * (value((*combo, i)) - value(combo))
    else:
        rng = random.Random(seed)
        order = list(range(n))
        for _ in range(n_permutations):
            rng.shuffle(order)
            prefix: tuple[int, ...] = ()
            prev = value(prefix)
            for idx in order:
                cur = value((*prefix, idx))
                phi[idx] += (cur - prev) / n_permutations
                prefix = (*prefix, idx)
                prev = cur

    positive = [max(0.0, v) for v in phi]
    total = sum(positive)
    credits: list[ContributionCredit] = []
    for sc, raw, pos in zip(retrieved, phi, positive, strict=True):
        weight = (pos / total) if total > 0 else 1.0 / n
        credits.append(
            ContributionCredit(
                contribution_id=sc.contribution.contribution_id,
                contributor_id=sc.contribution.contributor_id,
                retrieval_score=sc.score,
                marginal_value=raw,
                credit_weight=weight,
            )
        )
    return credits
