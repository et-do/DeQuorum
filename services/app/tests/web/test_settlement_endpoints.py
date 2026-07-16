"""Operator settlement endpoints: trigger -> queue -> ledger -> read.

The queue is overridden with an inline equal-split runner so these stay fast and
deterministic (no model / embedder load) while still exercising the full endpoint ->
LedgerService -> persistence -> read path. Faithful settlement itself is covered in
tests/worker and tests/test_settlement_ledger.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from dequorum.auth import AuthenticatedUser, require_user
from dequorum.chat.store import ROLE_NETWORK, ROLE_USER
from dequorum.db import open_chat_store, open_contribution_store
from dequorum.knowledge.contribution import Contribution
from dequorum.services import LedgerService
from dequorum.web.app import configure_app, create_app, settlement_queue
from dequorum.worker import InlineSettlementQueue, SettlementJob

TEST_USER = AuthenticatedUser(
    uid="dq:user-1", email="t@example.com", display_name="T", email_verified=True
)
OPERATOR_KEY = "test-operator-key"


def _equal_split_runner(job: SettlementJob) -> None:
    with open_chat_store() as chat, open_contribution_store() as contributions:
        LedgerService(chat, contributions).settle(job.message_id, job.revenue)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    test_url = os.environ.get(
        "DEQUORUM_TEST_DATABASE_URL",
        "postgresql://dequorum_app:dev-only-not-for-prod@db:5432/dequorum_test",
    )
    configure_app(database_url=test_url, use_mock=True, router="keyword", min_score=1.0)
    monkeypatch.setenv("DEQUORUM_OPERATOR_API_KEY", OPERATOR_KEY)
    app = create_app()
    app.dependency_overrides[require_user] = lambda: TEST_USER
    app.dependency_overrides[settlement_queue] = lambda: InlineSettlementQueue(
        _equal_split_runner
    )
    return TestClient(app)


def _seed_answer() -> str:
    """A contribution + a session whose network answer grounds it. Returns the
    network message_id."""
    with open_contribution_store() as cstore:
        c = Contribution.create(
            contributor_id="alice", text="quic over udp", citations=(), signing_key=b"k"
        )
        cstore.add(c)
        cid = c.contribution_id
    with open_chat_store() as chat:
        sess = chat.create_session("dq:user-1", "t")
        chat.add_message(sess.session_id, ROLE_USER, "what runs http3?")
        msg = chat.add_message(
            sess.session_id,
            ROLE_NETWORK,
            "QUIC over UDP",
            response={"query": "what runs http3?", "retrieved_contribution_ids": [cid]},
        )
        return msg.message_id


def test_trigger_settles_and_is_readable(client: TestClient) -> None:
    mid = _seed_answer()
    op = {"X-Operator-Key": OPERATOR_KEY}
    resp = client.post(f"/v1/settlements/{mid}", json={"revenue": 1.0}, headers=op)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    # inline queue settled before the response; the payout is in the body + readable
    assert body["settlement"]["contributors"]["alice"] == pytest.approx(0.40)

    got = client.get(f"/v1/settlements/{mid}", headers=op)
    assert got.status_code == 200
    assert got.json()["contributors"]["alice"] == pytest.approx(0.40)


def test_worker_endpoint_processes_a_job(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    # Stub the heavy reliance-grounded path (in tests/worker) so this test asserts the
    # endpoint wiring — job parse, guard, settle, persist, response — not the model.
    import dequorum.web.app as appmod

    monkeypatch.setattr(appmod, "_process_settlement_job", _equal_split_runner)
    mid = _seed_answer()
    op = {"X-Operator-Key": OPERATOR_KEY}
    resp = client.post(
        "/v1/worker/settle", json={"message_id": mid, "revenue": 1.0}, headers=op
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "settled"
    assert client.get(f"/v1/settlements/{mid}", headers=op).status_code == 200


def test_worker_endpoint_rejects_a_malformed_job(client: TestClient) -> None:
    resp = client.post(
        "/v1/worker/settle",
        json={"revenue": 1.0},
        headers={"X-Operator-Key": OPERATOR_KEY},
    )
    assert resp.status_code == 400


def test_operator_guard_rejects_bad_and_missing_keys(client: TestClient) -> None:
    mid = _seed_answer()
    assert client.post(f"/v1/settlements/{mid}").status_code == 401  # no key
    assert (
        client.post(
            f"/v1/settlements/{mid}", headers={"X-Operator-Key": "wrong"}
        ).status_code
        == 401
    )


def test_operator_endpoints_disabled_without_a_configured_key(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.delenv("DEQUORUM_OPERATOR_API_KEY", raising=False)
    mid = _seed_answer()
    resp = client.post(f"/v1/settlements/{mid}", headers={"X-Operator-Key": "anything"})
    assert resp.status_code == 503  # safe default: settlement off until configured
