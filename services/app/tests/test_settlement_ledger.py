from __future__ import annotations

from collections.abc import Iterator

import pytest

from dequorum.chat.store import ROLE_NETWORK, ROLE_USER, ChatStore
from dequorum.core.errors import CompositionError
from dequorum.economics.ledger import (
    marginal_credit_weights,
    settle_message,
    settle_message_faithful,
)
from dequorum.eval import KeywordRecallJudge
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import ContributionStore
from dequorum.review.service import ReviewService
from dequorum.routing.embedder import HashEmbedder


def _approx(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def _setup() -> tuple[ContributionStore, ChatStore, Contribution, str]:
    cstore = ContributionStore()
    c = Contribution.create(
        contributor_id="alice", text="quic over udp", citations=(), signing_key=b"k"
    )
    cstore.add(c)
    # rev1 upvotes alice's contribution -> becomes a reviewer for it
    ReviewService(cstore).cast_vote(
        contribution_id=c.contribution_id, voter_id="rev1", score=1
    )
    chat = ChatStore()
    sess = chat.create_session("dq:user-1", "t")
    chat.add_message(sess.session_id, ROLE_USER, "what runs http3?")
    msg = chat.add_message(
        sess.session_id,
        ROLE_NETWORK,
        "QUIC over UDP",
        response={"retrieved_contribution_ids": [c.contribution_id]},
    )
    return cstore, chat, c, msg.message_id


def test_settle_message_pays_contributor_reviewer_and_persists() -> None:
    cstore, chat, _c, mid = _setup()
    settlement, _record = settle_message(
        chat_store=chat, contribution_store=cstore, message_id=mid, revenue=1.0
    )
    # default split: contributor 0.40, reviewer 0.10, host 0.25, operator 0.15
    assert _approx(settlement.contributors["alice"], 0.40)  # sole cited contribution
    assert _approx(settlement.reviewers["rev1"], 0.10)  # sole upvoter
    assert _approx(settlement.host, 0.25) and _approx(settlement.operator, 0.15)
    assert _approx(settlement.total(), 1.0)
    # persisted to the ledger, readable back
    got = chat.get_settlement(mid)
    assert got is not None
    assert _approx(got.contributors["alice"], 0.40)
    assert _approx(got.reviewers["rev1"], 0.10)


def test_settle_message_quality_gate_withholds_on_downvote() -> None:
    cstore, chat, _c, mid = _setup()
    chat.set_feedback(mid, "dq:user-1", -1)  # answer rated unhelpful
    settlement, _ = settle_message(
        chat_store=chat, contribution_store=cstore, message_id=mid, revenue=1.0
    )
    assert settlement.contributors.get("alice", 0.0) == 0.0  # bad answer pays nothing
    assert _approx(settlement.total(), 1.0)  # withheld share conserved into treasury


def test_settle_message_pays_by_injected_faithful_weights() -> None:
    """The faithful measure plugs into the credit_weights slot: payouts follow the
    injected per-contribution weights, not an equal split."""
    cstore = ContributionStore()
    a = Contribution.create(
        contributor_id="alice", text="quic over udp", citations=(), signing_key=b"k"
    )
    b = Contribution.create(
        contributor_id="bob", text="tls 1.3 handshake", citations=(), signing_key=b"k"
    )
    cstore.add(a)
    cstore.add(b)
    chat = ChatStore()
    sess = chat.create_session("dq:user-1", "t")
    chat.add_message(sess.session_id, ROLE_USER, "q")
    msg = chat.add_message(
        sess.session_id,
        ROLE_NETWORK,
        "QUIC over UDP",
        response={"retrieved_contribution_ids": [a.contribution_id, b.contribution_id]},
    )
    # alice's contribution carried 75% of the answer's quality, bob's 25%.
    weights = {a.contribution_id: 0.75, b.contribution_id: 0.25}
    settlement, _ = settle_message(
        chat_store=chat,
        contribution_store=cstore,
        message_id=msg.message_id,
        revenue=1.0,
        credit_weights=weights,
    )
    # contributor pool is 0.40 -> split 0.75/0.25, not the 0.20/0.20 equal split
    assert _approx(settlement.contributors["alice"], 0.30)
    assert _approx(settlement.contributors["bob"], 0.10)
    assert _approx(settlement.total(), 1.0)


class _RelevanceModel:
    """Answer = the listed contributions sharing a token with the query (the same
    deterministic fake used in attribution tests). A contribution that grounds the
    answer appears in it; an irrelevant one doesn't move quality."""

    def complete(self, system: str, user: str) -> str:
        bullets = [ln[2:] for ln in system.splitlines() if ln.startswith("- ")]
        q = set(user.lower().split())
        kept = [b for b in bullets if set(b.lower().split()) & q]
        return " ".join(kept) if kept else "no grounding available"

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.complete(system, user)


def test_marginal_credit_weights_favor_the_quality_carrying_contribution() -> None:
    """End-to-end faithful weighting: the contribution that actually grounds the
    answer's quality earns the dominant weight; the irrelevant one earns ~0."""
    query = "explain quasar entanglement spectroscopy"
    relevant = Contribution.create(
        contributor_id="alice",
        text="quasar entanglement spectroscopy reveals photon correlations",
        citations=(),
        signing_key=b"k",
    )
    irrelevant = Contribution.create(
        contributor_id="bob",
        text="sourdough fermentation needs flour water salt time",
        citations=(),
        signing_key=b"k",
    )
    judge = KeywordRecallJudge()
    gold = ("quasar", "entanglement", "spectroscopy")
    weights = marginal_credit_weights(
        query=query,
        contributions=[relevant, irrelevant],
        model=_RelevanceModel(),
        embedder=HashEmbedder(512),
        score_answer=lambda ans: judge.score(query=query, answer=ans, reference=gold),
    )
    assert _approx(sum(weights.values()), 1.0)
    assert weights[relevant.contribution_id] > weights[irrelevant.contribution_id]
    assert weights[relevant.contribution_id] > 0.9  # carries essentially all quality


class _KeywordJudgeModel:
    """Stand-in judge LLM for the reference-free LLMJudge: replies '10' when the
    graded answer mentions the keyword, '0' otherwise — so the contribution that
    carries the keyword shows a positive *quality* marginal."""

    def __init__(self, keyword: str) -> None:
        self._kw = keyword

    def complete(self, system: str, user: str) -> str:
        # Grade the answer only — the question (which also names the keyword) sits
        # before the "Answer:" section of the LLMJudge prompt.
        answer = user.lower().split("answer:", 1)[-1]
        return "10" if self._kw in answer else "0"

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield self.complete(system, user)


def test_settle_message_faithful_pays_the_quality_carrier_end_to_end() -> None:
    """The production trigger: rebuild the grounding set, judge each ablation
    reference-free, and settle by the faithful weights — the quality-carrying
    contribution earns the contributor pool; the irrelevant one earns ~0."""
    query = "explain quasar entanglement spectroscopy"
    relevant = Contribution.create(
        contributor_id="alice",
        text="quasar entanglement spectroscopy reveals photon correlations",
        citations=(),
        signing_key=b"k",
    )
    irrelevant = Contribution.create(
        contributor_id="bob",
        text="sourdough fermentation needs flour water salt time",
        citations=(),
        signing_key=b"k",
    )
    cstore = ContributionStore()
    cstore.add(relevant)
    cstore.add(irrelevant)
    chat = ChatStore()
    sess = chat.create_session("dq:user-1", "t")
    chat.add_message(sess.session_id, ROLE_USER, query)
    msg = chat.add_message(
        sess.session_id,
        ROLE_NETWORK,
        "quasar entanglement spectroscopy reveals photon correlations",
        response={
            "query": query,
            "retrieved_contribution_ids": [
                relevant.contribution_id,
                irrelevant.contribution_id,
            ],
        },
    )
    settlement, record = settle_message_faithful(
        chat_store=chat,
        contribution_store=cstore,
        message_id=msg.message_id,
        revenue=1.0,
        model=_RelevanceModel(),
        embedder=HashEmbedder(512),
        judge_model=_KeywordJudgeModel("quasar"),
    )
    assert _approx(settlement.contributors["alice"], 0.40)  # carries all the quality
    assert settlement.contributors.get("bob", 0.0) < 1e-9  # irrelevant -> ~0
    assert _approx(settlement.total(), 1.0)
    assert record.contributors["alice"] > 0.0  # persisted


def test_settle_message_rejects_non_network_message() -> None:
    chat = ChatStore()
    sess = chat.create_session("dq:user-1", "t")
    umsg = chat.add_message(sess.session_id, ROLE_USER, "hi")
    with pytest.raises(CompositionError):
        settle_message(
            chat_store=chat,
            contribution_store=ContributionStore(),
            message_id=umsg.message_id,
            revenue=1.0,
        )
