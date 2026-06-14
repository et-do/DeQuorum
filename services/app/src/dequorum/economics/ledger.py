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

Credit policy (v1): equal split across the cited contributions. This is the slot
where the *faithful* measure plugs in — the quality-grounded marginal (whitepaper
§8.6) or routing-by-construction — by replacing how `credits` is built; nothing
downstream changes.
"""

from __future__ import annotations

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
    from dequorum.knowledge.store import ContributionStore


def settle_message(
    *,
    chat_store: ChatStore,
    contribution_store: ContributionStore,
    message_id: str,
    revenue: float,
    split: RevenueSplit | None = None,
) -> tuple[Settlement, SettlementRecord]:
    """Settle a single network answer and persist the payout. Returns the computed
    `Settlement` and the stored `SettlementRecord`."""
    msg = chat_store.get_message(message_id)
    if msg is None:
        raise CompositionError(f"unknown message: {message_id!r}")
    if msg.role != ROLE_NETWORK:
        raise CompositionError("only network answers can be settled")

    grounding_ids: list[str] = []
    if msg.response:
        grounding_ids = list(msg.response.get("retrieved_contribution_ids") or [])

    # v1 credit policy: equal weight across cited contributions. distribute_pool
    # aggregates per contributor, so a contributor cited twice earns twice.
    credits: list[ContributionCredit] = []
    reviewers: set[str] = set()
    k = len(grounding_ids)
    for cid in grounding_ids:
        contrib = contribution_store.get(cid)
        if contrib is None:
            continue  # cited contribution no longer present -> its share -> treasury
        weight = 1.0 / k
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
