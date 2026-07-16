"""LedgerService: the payout / attribution audit boundary.

The services-roadmap calls for carving `ledger` out of `app` before public launch
so the money path has its own audit boundary and deploy cadence. This is that
boundary as an in-process facade: a single object that owns settlement + the payout
journal, and nothing else. A standalone `ledger` FastAPI service would wrap these
methods in transport verbatim — the contract is already here.

The facade hides which stores back the settlement and which functions compute the
split (`economics.ledger`); callers settle and read journals against a stable API.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from dequorum.economics.ledger import settle_message, settle_message_reliance

if TYPE_CHECKING:
    from dequorum.chat.store import ChatStore, SettlementRecord
    from dequorum.economics.costmodel import RevenueSplit
    from dequorum.economics.settlement import Settlement
    from dequorum.inference.base_model import BaseModel
    from dequorum.knowledge.store import ContributionStore
    from dequorum.routing.embedder import Embedder


class LedgerService:
    """Settle answers and read the payout journal.

    Constructed with the two stores it spans; an integrator (or a future standalone
    service) supplies its own. Settlement is idempotent per message, so re-settling
    overwrites the journal row.
    """

    def __init__(
        self,
        chat_store: ChatStore,
        contribution_store: ContributionStore,
    ) -> None:
        self._chat = chat_store
        self._contributions = contribution_store

    def settle(
        self,
        message_id: str,
        revenue: float,
        *,
        split: RevenueSplit | None = None,
        credit_weights: Mapping[str, float] | None = None,
    ) -> Settlement:
        """Settle one answer and persist its payout. `credit_weights` injects the
        reliance-grounded per-contribution shares; omit for the equal-split default."""
        settlement, _ = settle_message(
            chat_store=self._chat,
            contribution_store=self._contributions,
            message_id=message_id,
            revenue=revenue,
            split=split,
            credit_weights=credit_weights,
        )
        return settlement

    def settle_reliance(
        self,
        message_id: str,
        revenue: float,
        *,
        model: BaseModel,
        embedder: Embedder,
        judge_model: BaseModel | None = None,
        split: RevenueSplit | None = None,
    ) -> Settlement:
        """Settle with reliance-grounded marginal credit (§8.6) — the off-hot-path
        production path. Computes the weights via a reference-free judge, then
        settles. See `economics.ledger.settle_message_reliance`."""
        settlement, _ = settle_message_reliance(
            chat_store=self._chat,
            contribution_store=self._contributions,
            message_id=message_id,
            revenue=revenue,
            model=model,
            embedder=embedder,
            judge_model=judge_model,
            split=split,
        )
        return settlement

    def get(self, message_id: str) -> SettlementRecord | None:
        """The persisted payout for one answer, or None if unsettled."""
        return self._chat.get_settlement(message_id)

    def journal(self, session_id: str) -> list[SettlementRecord]:
        """The payout journal for a session, oldest-first."""
        return self._chat.list_settlements(session_id)
