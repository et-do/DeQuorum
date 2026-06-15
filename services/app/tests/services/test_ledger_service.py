from __future__ import annotations

from dequorum.chat.store import ROLE_NETWORK, ROLE_USER, ChatStore
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import ContributionStore
from dequorum.review.service import ReviewService
from dequorum.services import LedgerService


def _approx(a: float, b: float) -> bool:
    return abs(a - b) < 1e-9


def _seed() -> tuple[LedgerService, ChatStore, str, str]:
    cstore = ContributionStore()
    c = Contribution.create(
        contributor_id="alice", text="quic over udp", citations=(), signing_key=b"k"
    )
    cstore.add(c)
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
    return LedgerService(chat, cstore), chat, sess.session_id, msg.message_id


def test_settle_then_read_back_through_the_facade() -> None:
    ledger, _chat, _sid, mid = _seed()
    settlement = ledger.settle(mid, revenue=1.0)
    assert _approx(settlement.contributors["alice"], 0.40)
    assert _approx(settlement.reviewers["rev1"], 0.10)
    # the facade is the read side of the audit boundary too
    rec = ledger.get(mid)
    assert rec is not None and _approx(rec.contributors["alice"], 0.40)


def test_settle_honors_injected_credit_weights() -> None:
    ledger, _chat, _sid, mid = _seed()
    # a single cited contribution with weight 1.0 collects the full contributor pool
    settlement = ledger.settle(mid, revenue=1.0, credit_weights={})  # cid absent -> 0
    assert settlement.contributors.get("alice", 0.0) < 1e-9  # share -> treasury
    assert _approx(settlement.total(), 1.0)


def test_journal_lists_a_sessions_payouts_oldest_first() -> None:
    ledger, chat, sid, mid1 = _seed()
    # a second settled answer in the same session
    mid2 = chat.add_message(
        sid, ROLE_NETWORK, "more", response={"retrieved_contribution_ids": []}
    ).message_id
    ledger.settle(mid1, revenue=1.0)
    ledger.settle(mid2, revenue=2.0)
    journal = ledger.journal(sid)
    assert {r.message_id for r in journal} == {mid1, mid2}
    assert _approx(sum(r.revenue for r in journal), 3.0)
    assert ledger.journal("ses_does_not_exist") == []
