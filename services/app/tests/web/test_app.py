"""Tests for the JSON-only DeQuorum API.

The UI lives in services/frontend; this app emits no HTML. Each test
asserts on JSON response shape, not on markup. Routes are mounted under
`/v1/*` and are reached via the Caddy proxy at `/api/v1/*` in production.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from dequorum.web.app import configure_app, create_app


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
        composition="pick_best",
    )
    _seed_if_empty()
    return TestClient(create_app())


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


def test_list_experts(client: TestClient) -> None:
    r = client.get("/v1/experts")
    assert r.status_code == 200
    experts = r.json()
    assert any(e["expert_id"] == "python-typing" for e in experts)
    # Shape: each expert has the documented fields.
    sample = experts[0]
    assert {"expert_id", "display_name", "specialty_tags", "prompt_digest"} <= set(
        sample
    )


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
    fact_text = (
        "Brand new typing fact: PEP 698 introduced typing.override "
        "as a decorator for enforcing override intent."
    )
    r = client.post(
        "/v1/contributions",
        json={
            "expert_id": "python-typing",
            "text": fact_text,
            "citations": ["https://peps.python.org/pep-0698/"],
        },
    )
    assert r.status_code == 201, r.text
    contribution_id = r.json()["contribution_id"]

    # It appears in the review queue.
    r = client.get("/v1/review")
    assert any(c["contribution_id"] == contribution_id for c in r.json())

    # Two distinct non-contributor experts vote +1 each.
    for voter in ("python-async", "python-packaging"):
        v = client.post(
            f"/v1/contributions/{contribution_id}/votes",
            json={"voter_id": voter, "score": 1},
        )
        assert v.status_code == 201, v.text

    # Now approved.
    r = client.get(f"/v1/contributions/{contribution_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved"
    assert body["tally"] == 2


def test_self_voting_returns_400(client: TestClient) -> None:
    fact_text = (
        "Self-vote test claim: Rust's borrow checker prevents aliasing "
        "between mutable references at compile time."
    )
    r = client.post(
        "/v1/contributions",
        json={
            "expert_id": "rust-ownership",
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
        json={"voter_id": "rust-ownership", "score": 1},
    )
    assert v.status_code == 400


def test_unknown_voter_returns_400(client: TestClient) -> None:
    bad = client.post(
        "/v1/contributions/nonexistent/votes",
        json={"voter_id": "no-such-expert", "score": 1},
    )
    assert bad.status_code == 400


def test_list_categories(client: TestClient) -> None:
    r = client.get("/v1/categories")
    assert r.status_code == 200
    cats = r.json()
    assert any(c["category_id"] == "uncategorized" for c in cats)


def test_list_contributors(client: TestClient) -> None:
    r = client.get("/v1/contributors")
    assert r.status_code == 200
    assert len(r.json()) > 0


def test_create_contributor_signup_flow(client: TestClient) -> None:
    r = client.post(
        "/v1/contributors",
        json={"display_name": "Test User", "email": "test@example.com"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["display_name"] == "Test User"
    assert body["has_email"] is True
    assert body["tier_name"] == "EMAIL_VERIFIED"
    assert "private_key_hex" in body


def test_create_contributor_requires_display_name(client: TestClient) -> None:
    r = client.post("/v1/contributors", json={})
    assert r.status_code == 400


def test_query_with_mock_model(client: TestClient) -> None:
    r = client.post("/v1/queries", json={"text": "python typing generator"})
    assert r.status_code == 200
    body = r.json()
    assert "final_answer" in body
    assert "routing" in body
    assert "experts" in body
    assert "ledger" in body


def test_agreement(client: TestClient) -> None:
    r = client.get("/v1/agreement")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert "text" in body
    assert any(t["name"] == "ANONYMOUS" for t in body["tiers"])
