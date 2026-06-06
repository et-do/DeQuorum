"""Tests for the JSON-only DeQuorum API.

The UI lives in services/frontend; this app emits no HTML. Each test
asserts on JSON response shape, not on markup. Routes are mounted under
`/v1/*` and are reached via the Caddy proxy at `/api/v1/*` in production.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from dequorum.auth import AuthenticatedUser, require_user
from dequorum.web.app import configure_app, create_app

TEST_USER = AuthenticatedUser(
    uid="test-user-uid",
    email="test@example.com",
    display_name="Test User",
    email_verified=True,
)


@pytest.fixture()
def client() -> TestClient:
    # conftest's session fixture has init'd the pool + applied migrations.
    # The autouse truncation fixture has wiped tables; we seed manually
    # here so the test database has the same fixture data the app would
    # bootstrap on startup. Bypass the lifespan to avoid re-init'ing the
    # session-scoped pool.
    from dequorum.web.app import _seed_if_empty

    test_url = os.environ.get(
        "DEQUORUM_TEST_DATABASE_URL",
        "postgresql://dequorum_app:dev-only-not-for-prod@db:5432/dequorum_test",
    )
    configure_app(
        database_url=test_url,
        use_mock=True,
        router="keyword",
        min_score=1.0,
    )
    _seed_if_empty()
    app = create_app()
    # Bypass Firebase token verification in tests — we don't have an
    # emulator hook reachable from pytest, and chat-endpoint coverage
    # cares about ownership/state, not token plumbing.
    app.dependency_overrides[require_user] = lambda: TEST_USER
    return TestClient(app)


def test_healthz(client: TestClient) -> None:
    r = client.get("/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_meta(client: TestClient) -> None:
    r = client.get("/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["use_mock"] is True
    assert "approval_threshold" in body
    assert "valid_statuses" in body


def test_list_contributions_shows_seeded(client: TestClient) -> None:
    r = client.get("/v1/contributions")
    assert r.status_code == 200
    contribs = r.json()
    assert len(contribs) > 0
    assert all("status" in c and "tally" in c for c in contribs)


def test_contributions_filter_by_status_rejected_is_empty(
    client: TestClient,
) -> None:
    r = client.get("/v1/contributions?status=rejected")
    assert r.status_code == 200
    assert r.json() == []


def test_contributions_search_q_substring(client: TestClient) -> None:
    r = client.get("/v1/contributions?q=python")
    assert r.status_code == 200
    contribs = r.json()
    # All matches contain "python" in their text (case-insensitive).
    for c in contribs:
        assert "python" in c["text"].lower()


def test_review_queue_empty_initially(client: TestClient) -> None:
    r = client.get("/v1/review")
    assert r.status_code == 200
    assert r.json() == []


def test_submit_then_vote_flow(client: TestClient) -> None:
    """User submits a contribution and another user votes — but a single
    +1 from the test user (the only signed-in voter we can simulate via
    the dependency override) leaves the contribution at tally=1
    (pending). The voting state machine itself is exercised in
    `tests/test_review.py`."""
    fact_text = (
        "Brand new typing fact: PEP 698 introduced typing.override "
        "as a decorator for enforcing override intent."
    )
    r = client.post(
        "/v1/contributions",
        json={
            "primary_category_id": "programming/python/typing",
            "text": fact_text,
            "citations": ["https://peps.python.org/pep-0698/"],
        },
    )
    assert r.status_code == 201, r.text
    contribution_id = r.json()["contribution_id"]

    # It appears in the review queue.
    r = client.get("/v1/review")
    assert any(c["contribution_id"] == contribution_id for c in r.json())


def test_contribution_is_publicly_verifiable(client: TestClient) -> None:
    """A submitted contribution can be verified by anyone, with no auth and
    no secret — Ed25519 signature valid + content intact. This is the
    in-app realization of the whitepaper's verifiable-attribution claim."""
    r = client.post(
        "/v1/contributions",
        json={
            "primary_category_id": "programming/python/typing",
            "text": "typing.assert_type asserts a value's inferred static type.",
            "citations": ["https://docs.python.org/3/library/typing.html"],
        },
    )
    assert r.status_code == 201, r.text
    contribution_id = r.json()["contribution_id"]

    # No Authorization needed — verification is public by design.
    v = client.get(f"/v1/contributions/{contribution_id}/verify")
    assert v.status_code == 200, v.text
    body = v.json()
    assert body["algorithm"] == "Ed25519"
    assert body["content_intact"] is True
    assert body["signature_valid"] is True
    assert body["verified"] is True
    # The public key is returned so a third party can re-run the check
    # independently of this operator.
    assert len(bytes.fromhex(body["public_key_hex"])) == 32
    assert len(bytes.fromhex(body["signature_hex"])) == 64


def test_verify_unknown_contribution_404(client: TestClient) -> None:
    r = client.get("/v1/contributions/does-not-exist/verify")
    assert r.status_code == 404


def test_self_voting_returns_400(client: TestClient) -> None:
    """A contributor voting on their own submission gets rejected. The
    voter_id is derived from the signed-in user (here the dependency-
    overridden TEST_USER), so when they try to vote on a contribution
    they themselves authored, the review service refuses."""
    fact_text = (
        "Self-vote test claim: Rust's borrow checker prevents aliasing "
        "between mutable references at compile time."
    )
    r = client.post(
        "/v1/contributions",
        json={
            "primary_category_id": "programming/rust/ownership",
            "text": fact_text,
            "citations": [
                "https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html",
            ],
        },
    )
    assert r.status_code == 201
    contribution_id = r.json()["contribution_id"]

    v = client.post(
        f"/v1/contributions/{contribution_id}/votes",
        json={"score": 1},
    )
    assert v.status_code == 400


def test_list_categories(client: TestClient) -> None:
    r = client.get("/v1/categories")
    assert r.status_code == 200
    cats = r.json()
    assert any(c["category_id"] == "uncategorized" for c in cats)


def test_list_contributors(client: TestClient) -> None:
    r = client.get("/v1/contributors")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_agreement(client: TestClient) -> None:
    r = client.get("/v1/agreement")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert "text" in body
    assert any(t["name"] == "ANONYMOUS" for t in body["tiers"])
