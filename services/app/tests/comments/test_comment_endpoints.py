"""HTTP-layer tests for the comment endpoints.

Reuses the same `client` fixture pattern as `tests/web/test_app.py`
so all auth, seeding, and DB plumbing is handled identically.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from dequorum.auth import AuthenticatedUser, require_user
from dequorum.web.app import configure_app, create_app

_TEST_USER = AuthenticatedUser(
    uid="comment-user-uid",
    email="commenter@example.com",
    display_name="Test Commenter",
    email_verified=True,
)


@pytest.fixture()
def client() -> TestClient:
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
    app = create_app()
    app.dependency_overrides[require_user] = lambda: _TEST_USER
    return TestClient(app)


def _any_contribution_id(client: TestClient) -> str:
    contribs = client.get("/v1/contributions").json()
    assert contribs, "seed should have produced at least one contribution"
    return contribs[0]["contribution_id"]


def test_list_comments_404_for_missing_contribution(client: TestClient) -> None:
    r = client.get("/v1/contributions/does-not-exist/comments")
    assert r.status_code == 404


def test_list_comments_starts_empty(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.get(f"/v1/contributions/{cid}/comments")
    assert r.status_code == 200
    assert r.json() == []


def test_create_comment_round_trip(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.post(
        f"/v1/contributions/{cid}/comments",
        json={"body": "Useful clarification on the edge case."},
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["comment_id"].startswith("dq:c:")
    assert created["body"] == "Useful clarification on the edge case."
    assert created["parent_comment_id"] is None
    assert created["redacted_at"] is None
    assert created["signature"]["digest"]

    listed = client.get(f"/v1/contributions/{cid}/comments").json()
    assert len(listed) == 1
    assert listed[0]["comment_id"] == created["comment_id"]


def test_empty_body_rejected(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.post(
        f"/v1/contributions/{cid}/comments",
        json={"body": "   \n  "},
    )
    assert r.status_code == 400


def test_oversize_body_rejected(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.post(
        f"/v1/contributions/{cid}/comments",
        json={"body": "x" * 10_001},
    )
    assert r.status_code == 400


def test_threaded_reply(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    root = client.post(
        f"/v1/contributions/{cid}/comments", json={"body": "root"}
    ).json()
    reply = client.post(
        f"/v1/contributions/{cid}/comments",
        json={"body": "reply", "parent_comment_id": root["comment_id"]},
    ).json()
    listed = client.get(f"/v1/contributions/{cid}/comments").json()
    assert {c["comment_id"] for c in listed} == {
        root["comment_id"],
        reply["comment_id"],
    }
    assert reply["parent_comment_id"] == root["comment_id"]


def test_parent_must_belong_to_same_contribution(client: TestClient) -> None:
    contribs = client.get("/v1/contributions").json()
    assert len(contribs) >= 2
    cid_a, cid_b = contribs[0]["contribution_id"], contribs[1]["contribution_id"]
    root = client.post(
        f"/v1/contributions/{cid_a}/comments", json={"body": "on A"}
    ).json()
    r = client.post(
        f"/v1/contributions/{cid_b}/comments",
        json={"body": "should fail", "parent_comment_id": root["comment_id"]},
    )
    assert r.status_code == 400


def test_redact_own_comment_hides_body(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    created = client.post(
        f"/v1/contributions/{cid}/comments", json={"body": "delete me"}
    ).json()
    delete = client.delete(f"/v1/comments/{created['comment_id']}")
    assert delete.status_code == 204

    listed = client.get(f"/v1/contributions/{cid}/comments").json()
    assert len(listed) == 1
    assert listed[0]["redacted_at"] is not None
    assert listed[0]["body"].startswith("_[redacted")


def test_cannot_redact_someone_elses_comment(client: TestClient) -> None:
    """A second authenticated user attempting to redact the first
    user's comment is forbidden (curator powers are off by default in
    dev — see `_is_curator` in `web/app.py`)."""
    cid = _any_contribution_id(client)
    created = client.post(
        f"/v1/contributions/{cid}/comments", json={"body": "mine"}
    ).json()

    # Swap the dep override to a different user mid-test.
    from dequorum.web.app import configure_app, create_app

    other_user = AuthenticatedUser(
        uid="someone-else-uid",
        email="other@example.com",
        display_name="Other",
        email_verified=True,
    )
    app = create_app()
    configure_app(use_mock=True, router="keyword", min_score=1.0)
    app.dependency_overrides[require_user] = lambda: other_user
    with TestClient(app) as other_client:
        r = other_client.delete(f"/v1/comments/{created['comment_id']}")
    assert r.status_code == 403


def test_replacement_chain(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    original = client.post(
        f"/v1/contributions/{cid}/comments", json={"body": "v1"}
    ).json()
    replacement = client.post(
        f"/v1/contributions/{cid}/comments",
        json={
            "body": "v2 — fixed a typo",
            "replaces_comment_id": original["comment_id"],
        },
    )
    assert replacement.status_code == 201
    assert replacement.json()["replaces_comment_id"] == original["comment_id"]


def test_replace_someone_elses_comment_rejected(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    original = client.post(
        f"/v1/contributions/{cid}/comments", json={"body": "mine"}
    ).json()

    other_user = AuthenticatedUser(
        uid="impersonator-uid",
        email="x@example.com",
        display_name="X",
        email_verified=True,
    )
    app = create_app()
    configure_app(use_mock=True, router="keyword", min_score=1.0)
    app.dependency_overrides[require_user] = lambda: other_user
    with TestClient(app) as other_client:
        r = other_client.post(
            f"/v1/contributions/{cid}/comments",
            json={
                "body": "hostile takeover",
                "replaces_comment_id": original["comment_id"],
            },
        )
    assert r.status_code == 403


def test_line_anchor_round_trip(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.post(
        f"/v1/contributions/{cid}/comments",
        json={
            "body": "anchored to lines 3-5",
            "line_anchor": {"start_line": 3, "end_line": 5},
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["line_anchor"] == {"start_line": 3, "end_line": 5}


def test_invalid_line_anchor_rejected(client: TestClient) -> None:
    cid = _any_contribution_id(client)
    r = client.post(
        f"/v1/contributions/{cid}/comments",
        json={
            "body": "bad anchor",
            "line_anchor": {"start_line": 9, "end_line": 1},
        },
    )
    assert r.status_code == 400
