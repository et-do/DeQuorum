"""Peer review: cast votes, tally results, transition contribution status."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dequorum.core.errors import CompositionError
from dequorum.knowledge.status import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from dequorum.knowledge.store import ContributionStore
from dequorum.review.vote import Vote

APPROVAL_THRESHOLD: Final[int] = 2
REJECTION_THRESHOLD: Final[int] = -2


@dataclass(frozen=True, slots=True)
class ReviewOutcome:
    contribution_id: str
    tally: float  # tier-weighted net score (see ContributionStore.vote_tally)
    previous_status: str
    new_status: str
    changed: bool


class ReviewService:
    """Coordinates voting + status transitions over a ContributionStore.

    A contribution is approved when net vote score >= APPROVAL_THRESHOLD and
    rejected at <= REJECTION_THRESHOLD. Self-voting (voter_id == contributor_id)
    is disallowed.
    """

    def __init__(self, store: ContributionStore) -> None:
        self._store = store

    def cast_vote(
        self,
        *,
        contribution_id: str,
        voter_id: str,
        score: int,
        signing_key: bytes | None = None,
    ) -> ReviewOutcome:
        contribution = self._store.get(contribution_id)
        if contribution is None:
            raise CompositionError(f"unknown contribution: {contribution_id!r}")
        if contribution.contributor_id == voter_id:
            raise CompositionError(
                f"self-voting forbidden: {voter_id!r} is the contributor"
            )

        # Without a registered key the voter signs with a stub derived
        # from their id — sufficient for the dev path; real signups
        # supply their own ed25519 key.
        key = signing_key if signing_key is not None else voter_id.encode()
        vote = Vote.create(
            contribution_id=contribution_id,
            voter_id=voter_id,
            score=score,
            signing_key=key,
        )
        self._store.add_vote(vote)
        return self._evaluate(contribution_id)

    def _evaluate(self, contribution_id: str) -> ReviewOutcome:
        previous = self._store.get_status(contribution_id) or STATUS_PENDING
        tally = self._store.vote_tally(contribution_id)
        new = self._status_for_tally(tally, previous)
        if new != previous:
            self._store.set_status(contribution_id, new)
        return ReviewOutcome(
            contribution_id=contribution_id,
            tally=tally,
            previous_status=previous,
            new_status=new,
            changed=new != previous,
        )

    @staticmethod
    def _status_for_tally(tally: float, current: str) -> str:
        if tally >= APPROVAL_THRESHOLD:
            return STATUS_APPROVED
        if tally <= REJECTION_THRESHOLD:
            return STATUS_REJECTED
        # No threshold crossed: leave terminal states alone, otherwise pending.
        if current in (STATUS_APPROVED, STATUS_REJECTED):
            return current
        return STATUS_PENDING
