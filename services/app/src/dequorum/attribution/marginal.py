"""Leave-one-out marginal attribution for a grounded answer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from dequorum.inference.base_model import BaseModel
from dequorum.inference.pipeline import _augment_system_prompt
from dequorum.retrieval import ScoredContribution
from dequorum.routing.embedder import Embedder, cosine_sim


@dataclass(frozen=True, slots=True)
class ContributionCredit:
    """One contribution's measured share of an answer's value."""

    contribution_id: str
    contributor_id: str
    retrieval_score: float
    # Causal marginal value in [0, ~1]: how much the answer's resemblance to
    # this contribution's content drops when it is removed from the context.
    marginal_value: float
    # marginal_value normalized across the answer's contributions; sums to 1.
    credit_weight: float


def _cos(vec, other) -> float:
    """Cosine similarity between two 1-D embedding vectors."""
    return float(cosine_sim(vec, other[None, :])[0])


def measure_attribution(
    *,
    query: str,
    persona_prompt: str,
    retrieved: Sequence[ScoredContribution],
    model: BaseModel,
    embedder: Embedder,
) -> list[ContributionCredit]:
    """Measure each retrieved contribution's causal contribution to the answer.

    Method (leave-one-out ablation):
      1. Generate the answer with the full retrieved set.
      2. For each contribution d, regenerate with d removed.
      3. d's marginal value = max(0, sim(answer_full, d) - sim(answer_minus_d, d)):
         how much content that resembles d is present *because d was there*.
         A contribution whose information is also carried by a duplicate or a
         sibling contribution shows ~0 marginal value — which is exactly the
         gaming-resistance the flat-credit ledger lacks.
      4. Normalize marginal values into credit weights that sum to 1.

    Cost is (k + 1) generations for k contributions; intended for the
    benchmark / offline credit computation, not the hot chat path.
    """
    contribs = [sc.contribution for sc in retrieved]
    if not contribs:
        return []

    full_answer = model.complete(
        system=_augment_system_prompt(persona_prompt, tuple(contribs)),
        user=query,
    )
    full_emb = embedder.embed([full_answer])[0]
    contrib_embs = embedder.embed([c.text for c in contribs])

    marginals: list[float] = []
    for i, _ in enumerate(retrieved):
        others = tuple(c for j, c in enumerate(contribs) if j != i)
        ablated_answer = model.complete(
            system=_augment_system_prompt(persona_prompt, others),
            user=query,
        )
        ablated_emb = embedder.embed([ablated_answer])[0]
        c_emb = contrib_embs[i]
        with_sim = _cos(full_emb, c_emb)
        without_sim = _cos(ablated_emb, c_emb)
        marginals.append(max(0.0, with_sim - without_sim))

    total = sum(marginals)
    n = len(marginals)
    credits: list[ContributionCredit] = []
    for sc, value in zip(retrieved, marginals, strict=True):
        weight = (value / total) if total > 0 else 1.0 / n
        credits.append(
            ContributionCredit(
                contribution_id=sc.contribution.contribution_id,
                contributor_id=sc.contribution.contributor_id,
                retrieval_score=sc.score,
                marginal_value=value,
                credit_weight=weight,
            )
        )
    return credits


def distribute_pool(
    credits: Sequence[ContributionCredit], pool: float
) -> dict[str, float]:
    """Split a revenue `pool` across contributors by measured credit weight.

    Aggregates by contributor (a contributor cited twice in one answer gets
    the sum of their weights). This is the payout primitive the economic
    layer (§5) computes over — value-weighted, not per-citation flat.
    """
    payouts: dict[str, float] = {}
    for c in credits:
        payouts[c.contributor_id] = payouts.get(c.contributor_id, 0.0) + (
            c.credit_weight * pool
        )
    return payouts
