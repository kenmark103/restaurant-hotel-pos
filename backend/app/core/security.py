"""
security.py — Cryptographic utilities
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  • Added hash_pin() / verify_pin()      — bcrypt-based, same strength as passwords
  • Added generate_pin_fingerprint()     — deterministic HMAC-SHA256 digest used
    for the unique (branch_id, pin_fingerprint) index without exposing the raw PIN
  • decode_token() consolidated from separate helper (was duplicate logic)
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Request, Response
from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
REFRESH_COOKIE_NAME = "pos_refresh_token"

# ─────────────────────────────────────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# PIN hashing
# Numeric PINs are short — we bcrypt them for storage security,
# but we also need a deterministic fingerprint for uniqueness-per-branch checks
# (bcrypt salts prevent direct comparison of two hashes of the same value).
# ─────────────────────────────────────────────────────────────────────────────

def hash_pin(pin: str) -> str:
    """Securely hash a numeric PIN using bcrypt.  Store in staff_profiles.pin_hash."""
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_pin(pin: str, pin_hash: str | None) -> bool:
    """Return True if *pin* matches the stored bcrypt *pin_hash*."""
    if not pin_hash:
        return False
    return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))


def generate_pin_fingerprint(pin: str, branch_id: int) -> str:
    """
    Deterministic HMAC-SHA256 digest of ``pin + branch_id``.

    Stored in staff_profiles.pin_fingerprint and indexed with a UNIQUE
    constraint on (branch_id, pin_fingerprint) so the DB can enforce that no
    two active staff share a PIN within the same branch — without storing the
    raw PIN or allowing bcrypt comparisons.

    The HMAC key is the application SECRET_KEY, so fingerprints cannot be
    reverse-engineered without access to the server secret.
    """
    message = f"{branch_id}:{pin}".encode("utf-8")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def validate_pin_format(pin: str) -> bool:
    """Return True if *pin* is a valid 5-digit numeric PIN."""
    return pin.isdigit() and len(pin) == 5


# ─────────────────────────────────────────────────────────────────────────────
# JWT token creation / verification
# ─────────────────────────────────────────────────────────────────────────────

def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    return _create_token(
        str(subject),
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        str(subject),
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def verify_token(token: str, expected_type: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.  Raises ValueError on any failure (expired,
    wrong type, bad signature).  Callers map to HTTP 401.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token.") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('type')}'.")

    return payload


def decode_token(token: str, expected_type: str) -> str:
    """Shorthand — verify token and return the subject (user_id as string)."""
    payload = verify_token(token, expected_type)
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token subject missing.")
    return str(subject)


# ─────────────────────────────────────────────────────────────────────────────
# Refresh token cookie helpers
# ─────────────────────────────────────────────────────────────────────────────

def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")


def decode_refresh_cookie(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)