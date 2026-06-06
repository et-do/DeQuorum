"""Firebase Auth token verification.

In dev the `FIREBASE_AUTH_EMULATOR_HOST` env var is set by compose
(`auth:9099`), which makes `firebase_admin.auth` skip signature
verification and talk to the local emulator — no service-account key
needed. In production the same module reads `GOOGLE_APPLICATION_CREDENTIALS`
(or runs as the default service account on Cloud Run) and verifies
against Google's public keys.

The FastAPI dependency `require_user` extracts `Authorization: Bearer
<id_token>`, verifies it, and returns an `AuthenticatedUser`. Routes
that need an identity declare it via `Depends(require_user)`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException

_FIREBASE_INITIALIZED = False


class InvalidTokenError(Exception):
    """Raised when the supplied token is missing / malformed / expired."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The fields we care about from a verified Firebase token."""

    uid: str
    email: str | None
    display_name: str | None
    email_verified: bool


def init_firebase() -> None:
    """Initialize the Firebase Admin SDK once per process.

    Safe to call multiple times — re-initialization is a no-op. Called
    from the FastAPI lifespan so the SDK is ready before any request
    needs to verify a token.
    """
    global _FIREBASE_INITIALIZED
    if _FIREBASE_INITIALIZED:
        return
    try:
        import firebase_admin
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "firebase-admin not installed — add it to services/app/pyproject.toml"
        ) from exc
    if not firebase_admin._apps:
        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        options = {"projectId": project_id} if project_id else None
        firebase_admin.initialize_app(options=options)
    _FIREBASE_INITIALIZED = True


def verify_token(id_token: str) -> AuthenticatedUser:
    """Verify a Firebase ID token. Raises InvalidTokenError on any failure."""
    init_firebase()
    from firebase_admin import auth as fb_auth  # type: ignore[import-untyped]

    try:
        # check_revoked=False because the emulator doesn't track revocation
        # and the production cost is one extra round-trip; sessions short
        # enough that revocation isn't load-bearing here.
        claims = fb_auth.verify_id_token(id_token, check_revoked=False)
    except Exception as exc:  # firebase_admin raises a variety of types
        raise InvalidTokenError(str(exc)) from exc
    uid = claims.get("uid") or claims.get("user_id")
    if not uid:
        raise InvalidTokenError("token has no uid")
    return AuthenticatedUser(
        uid=str(uid),
        email=claims.get("email"),
        display_name=claims.get("name") or claims.get("display_name"),
        email_verified=bool(claims.get("email_verified", False)),
    )


def require_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    """FastAPI dependency. Returns the verified user or raises 401."""
    if not authorization:
        raise HTTPException(401, "missing Authorization header")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Authorization must be `Bearer <token>`")
    try:
        return verify_token(parts[1])
    except InvalidTokenError as exc:
        raise HTTPException(401, f"invalid token: {exc}") from exc
