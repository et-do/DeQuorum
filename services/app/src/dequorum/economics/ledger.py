"""Settlement orchestration: settle one answer end-to-end.

This wires the proven pieces into a running payout (build-direction.md item 6).
Given a settled answer it:

  1. reads the answer's **grounding set** (the contributions on the message's proof
     chain) and turns it into per-contribution `credit_weight`s,
  2. collects the **reviewers** who upvoted those grounding contributions,
  3. reads the **feedback** on the answer as a quality factor,
  4. computes the split via `economics.settlement.settle_query`, and
  5. persists it as a `SettlementRecord` (the payout ledger).

Distinct from `core.ledger.AttributionLedger` (an in-memory per-node token tally);
this is the persistent, money-facing settlement of a query.

Credit policy: `settle_message` defaults to an equal split across the cited
contributions, but accepts injected `credit_weights` — this is the slot where the
*faithful* measure plugs in. `marginal_credit_weights` computes those weights with
the quality-grounded marginal (whitepaper §8.6, faithful 0.89 vs resemblance 0.50):
it ablates each contribution and weights by the *judge* marginal (the quality drop
when it's removed), not embedding resemblance. Settlement itself is unchanged — it
just consumes the weights. Routing-by-construction would feed the same slot.

The faithful computation is leave-one-out — (k+1) generations + judge calls per
answer — so it runs at settlement time (batch / off the chat hot path), and needs a
`score_answer` quality judge to supply the signal.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING

from dequorum.attribution.marginal import ContributionCredit
from dequorum.chat.store import ROLE_NETWORK
from dequorum.core.errors import CompositionError
from dequorum.economics.settlement import (
    Settlement,
    quality_factor_from_feedback,
    settle_query,
)

if TYPE_CHECKING:
    from dequorum.chat.store import ChatStore, SettlementRecord
    from dequorum.economics.costmodel import RevenueSplit
    from dequorum.inference.base_model import BaseModel
    from dequorum.knowledge.contribution import Contribution
    from dequorum.knowledge.store import ContributionStore
    from dequorum.routing.embedder import Embedder

DEFAULT_PERSONA = (
    "You are a precise assistant. Answer the question from the references."
)


def settle_message(
    *,
    chat_store: ChatStore,
    contribution_store: ContributionStore,
    message_id: str,
    revenue: float,
    split: RevenueSplit | None = None,
    credit_weights: Mapping[str, float] | None = None,
) -> tuple[Settlement, SettlementRecord]:
    """Settle a single network answer and persist the payout. Returns the computed
    `Settlement` and the stored `SettlementRecord`.

    `credit_weights` maps contribution_id -> share of the contributor pool. When
    omitted, the contributors are paid by an equal split across the cited set (v1).
    Pass the output of `marginal_credit_weights` here for the faithful,
    quality-grounded payout. A cited contribution absent from a supplied map gets
    zero (its share flows to treasury via `settle_query`)."""
    msg = chat_store.get_message(message_id)
    if msg is None:
        raise CompositionError(f"unknown message: {message_id!r}")
    if msg.role != ROLE_NETWORK:
        raise CompositionError("only network answers can be settled")

    grounding_ids: list[str] = []
    if msg.response:
        grounding_ids = list(msg.response.get("retrieved_contribution_ids") or [])

    # Credit per cited contribution: the injected faithful weight if provided, else
    # an equal split. distribute_pool aggregates per contributor, so a contributor
    # cited twice earns the sum of those weights.
    credits: list[ContributionCredit] = []
    reviewers: set[str] = set()
    k = len(grounding_ids)
    for cid in grounding_ids:
        contrib = contribution_store.get(cid)
        if contrib is None:
            continue  # cited contribution no longer present -> its share -> treasury
        weight = credit_weights.get(cid, 0.0) if credit_weights is not None else 1.0 / k
        credits.append(
            ContributionCredit(
                contribution_id=cid,
                contributor_id=contrib.contributor_id,
                retrieval_score=0.0,
                marginal_value=weight,
                credit_weight=weight,
            )
        )
        # Reviewers = those who upvoted a grounding contribution (not its author).
        for vote in contribution_store.votes_for(cid):
            if vote.score > 0 and vote.voter_id != contrib.contributor_id:
                reviewers.add(vote.voter_id)

    summary = chat_store.feedback_summary(message_id)
    quality = quality_factor_from_feedback(summary["net"], summary["count"])

    settlement = settle_query(
        revenue=revenue,
        credits=credits,
        reviewer_ids=sorted(reviewers),
        split=split,
        quality_factor=quality,
    )
    record = chat_store.record_settlement(
        message_id,
        msg.session_id,
        revenue=settlement.revenue,
        quality_factor=settlement.quality_factor,
        contributors=settlement.contributors,
        reviewers=settlement.reviewers,
        host=settlement.host,
        operator=settlement.operator,
        treasury=settlement.treasury,
    )
    return settlement, record


def marginal_credit_weights(
    *,
    query: str,
    contributions: Sequence[Contribution],
    model: BaseModel,
    embedder: Embedder,
    score_answer: Callable[[str], float],
    persona_prompt: str = DEFAULT_PERSONA,
) -> dict[str, float]:
    """Compute the *faithful* per-contribution credit weights for one answer, ready
    to hand to `settle_message(credit_weights=...)`.

    This is the whitepaper §8.6 measure: leave-one-out ablation weighted by the
    drop in answer *quality* (the `score_answer` judge), normalized to sum to 1.
    Resemblance-based weighting is a coin-flip in the contested regime (0.50);
    quality-grounded is faithful (0.89) — so we read `judge_marginal`, not
    `credit_weight`. Negative marginals (a contribution that *hurt*) clamp to 0.

    Cost is (k+1) generations + judge calls; intended for batch settlement, not the
    chat hot path. Returns {} for an empty grounding set; falls back to an equal
    split if no contribution shows a positive quality marginal (the answer was good,
    but the credit is indistinguishable)."""
    contribs = list(contributions)
    if not contribs:
        return {}

    from dequorum.attribution.marginal import measure_attribution
    from dequorum.retrieval import ScoredContribution

    retrieved = [ScoredContribution(contribution=c, score=0.0) for c in contribs]
    credits = measure_attribution(
        query=query,
        persona_prompt=persona_prompt,
        retrieved=retrieved,
        model=model,
        embedder=embedder,
        score_answer=score_answer,
    )
    raw = [max(0.0, c.judge_marginal or 0.0) for c in credits]
    total = sum(raw)
    if total <= 0.0:
        equal = 1.0 / len(credits)
        return {c.contribution_id: equal for c in credits}
    return {c.contribution_id: r / total for c, r in zip(credits, raw, strict=True)}
