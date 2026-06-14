from __future__ import annotations

import pytest

from dequorum.chat.store import ROLE_NETWORK, ROLE_USER, ChatStore
from dequorum.core.errors import CompositionError
from dequorum.economics.ledger import settle_message
from dequorum.knowledge.contribution import Contribution
from dequorum.knowledge.store import ContributionStore
from dequorum.review.service import ReviewService


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
