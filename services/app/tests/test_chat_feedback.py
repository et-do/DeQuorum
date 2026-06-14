from __future__ import annotations

import pytest

from dequorum.chat.store import ROLE_NETWORK, ROLE_USER, ChatStore


def _network_message(cs: ChatStore):
    session = cs.create_session("dq:user-1", "t")
    cs.add_message(session.session_id, ROLE_USER, "what runs HTTP/3?")
    msg = cs.add_message(
        session.session_id,
        ROLE_NETWORK,
        "QUIC over UDP.",
        response={"retrieved_contribution_ids": ["c1", "c2"]},
    )
    return session, msg


def test_set_and_get_feedback() -> None:
    with ChatStore() as cs:
        _s, m = _network_message(cs)
        fb = cs.set_feedback(m.message_id, "dq:user-1", 1, "helpful")
        assert fb.rating == 1 and fb.comment == "helpful"
        got = cs.get_feedback(m.message_id, "dq:user-1")
        assert got is not None and got.rating == 1 and got.comment == "helpful"


def test_feedback_upsert_changes_rating_keeps_created_at() -> None:
    with ChatStore() as cs:
        _s, m = _network_message(cs)
        a = cs.set_feedback(m.message_id, "dq:user-1", 1)
        b = cs.set_feedback(m.message_id, "dq:user-1", -1, "changed my mind")
        assert b.rating == -1 and b.comment == "changed my mind"
        assert b.created_at == a.created_at  # upsert preserves first-seen time
        assert b.updated_at >= a.updated_at
        # still one row for this (message, user)
        assert cs.feedback_summary(m.message_id) == {"net": -1, "count": 1}


def test_feedback_summary_aggregates_across_users() -> None:
    with ChatStore() as cs:
        _s, m = _network_message(cs)
        cs.set_feedback(m.message_id, "dq:u1", 1)
        cs.set_feedback(m.message_id, "dq:u2", 1)
        cs.set_feedback(m.message_id, "dq:u3", -1)
        assert cs.feedback_summary(m.message_id) == {"net": 1, "count": 3}


def test_invalid_rating_rejected() -> None:
    with ChatStore() as cs:
        _s, m = _network_message(cs)
        with pytest.raises(ValueError):
            cs.set_feedback(m.message_id, "dq:u1", 0)
