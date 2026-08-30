"""Password hashing and session cookies."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import Response, g, request

from self_healing_rag.config import (
    LOGIN_ID_PATTERN,
    MIN_PASSWORD_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_TTL,
)

_hasher = PasswordHasher()
_LOGIN_RE = re.compile(LOGIN_ID_PATTERN)

# Compared on unknown-user logins so response time does not leak existence.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def now() -> datetime:
    return datetime.now(timezone.utc)


def validate_login_id(login_id: str) -> str | None:
    if not _LOGIN_RE.fullmatch(login_id):
        return "Login id must be 3–32 characters: letters, digits, underscore."
    return None


def validate_password(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return None


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def dummy_verify(password: str) -> None:
    """Burn the same verify cost when the login id is unknown."""
    try:
        _hasher.verify(_DUMMY_HASH, password)
    except Exception:
        pass


def new_session_token() -> tuple[str, str]:
    """Return (raw token for the cookie, sha256 hex for the database)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="Lax",
        path="/",
        max_age=int(SESSION_TTL.total_seconds()),
        secure=request.is_secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def as_iso(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat(timespec="seconds")
    return str(value)


def as_str(value: Any) -> str:
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def current_user_id() -> str:
    user = getattr(g, "user", None)
    if not user:
        raise RuntimeError("current_user_id called without a session")
    return user["id"]
