from __future__ import annotations

from collections.abc import Iterator

import pytest

from dequorum.chat.store import ROLE_NETWORK, ROLE_USER, ChatStore
from dequorum.core.errors import CompositionError
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import ContributionStore
from dequorum.routing.embedder import HashEmbedder
from dequorum.services import LedgerService
from dequorum.worker import (
    CloudTasksConfig,
    CloudTasksSettlementQueue,
    InlineSettlementQueue,
    SettlementJob,
    run_settlement_job,
)


def _approx(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


class _RelevanceModel:
    def complete(self, system: str, user: str) -> str:
        bullets = [ln[2:] for ln in system.splitlines() if ln.startswith("- ")]
        q = set(user.lower().split())
        kept = [b for b in bullets if set(b.lower().split()) & q]
        return " ".join(kept) if kept else "no grounding available"

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.complete(system, user)


class _KeywordJudgeModel:
    def __init__(self, keyword: str) -> None:
        self._kw = keyword

    def complete(self, system: str, user: str) -> str:
        return "10" if self._kw in user.lower().split("answer:", 1)[-1] else "0"

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.complete(system, user)


def test_settlement_job_round_trips_through_dict() -> None:
    job = SettlementJob(message_id="msg_x", revenue=2.5)
    assert SettlementJob.from_dict(job.to_dict()) == job


def test_run_settlement_job_settles_faithfully() -> None:
    query = "explain quasar entanglement spectroscopy"
    relevant = Contribution.create(
        contributor_id="alice",
        text="quasar entanglement spectroscopy reveals photon correlations",
        citations=(),
        signing_key=b"k",
    )
    cstore = ContributionStore()
    cstore.add(relevant)
    chat = ChatStore()
    sess = chat.create_session("dq:user-1", "t")
    chat.add_message(sess.session_id, ROLE_USER, query)
    msg = chat.add_message(
        sess.session_id,
        ROLE_NETWORK,
        "answer",
        response={
            "query": query,
            "retrieved_contribution_ids": [relevant.contribution_id],
        },
    )
    ledger = LedgerService(chat, cstore)
    settlement = run_settlement_job(
        SettlementJob(message_id=msg.message_id, revenue=1.0),
        ledger,
        model=_RelevanceModel(),
        embedder=HashEmbedder(512),
        judge_model=_KeywordJudgeModel("quasar"),
    )
    assert _approx(settlement.contributors["alice"], 0.40)
    assert _approx(settlement.total(), 1.0)
    assert ledger.get(msg.message_id) is not None  # persisted


def test_inline_queue_runs_the_job_synchronously() -> None:
    seen: list[SettlementJob] = []
    queue = InlineSettlementQueue(seen.append)
    job = SettlementJob(message_id="msg_y", revenue=1.0)
    queue.enqueue(job)
    assert seen == [job]  # ran before enqueue returned


def test_cloudtasks_queue_errors_clearly_without_the_dependency() -> None:
    # google-cloud-tasks is not a project dependency; the adapter must fail with a
    # clear, actionable message rather than a raw ImportError.
    queue = CloudTasksSettlementQueue(
        CloudTasksConfig(
            project="p", location="us-central1", queue="q", worker_url="https://w"
        )
    )
    with pytest.raises(CompositionError, match="google-cloud-tasks"):
        queue.enqueue(SettlementJob(message_id="m", revenue=1.0))
