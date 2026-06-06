"""Firebase Auth integration — token verification + a current-user dep."""

from dequorum.auth.firebase import (
    AuthenticatedUser,
    InvalidTokenError,
    init_firebase,
    require_user,
    verify_token,
)

__all__ = [
    "AuthenticatedUser",
    "InvalidTokenError",
    "init_firebase",
    "require_user",
    "verify_token",
]
