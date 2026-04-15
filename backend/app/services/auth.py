"""
auth.py — Authentication service
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  • authenticate_staff_by_pin()  — 5-digit PIN login with lockout enforcement
  • Staff login now issues refresh tokens (aligned with Google OAuth customer
    flow, needed for long-running POS terminals).
  • store_refresh_token() / rotate_refresh_token() — DB-backed token rotation
    enables per-device revocation.
  • build_login_response() — single helper returns access token + UserSession
    so routes stay thin.
  • All PIN lockout logic centralised here (no duplication in service layer).
"""

import hashlib
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_pin,
    verify_password,
    verify_pin,
    verify_token,
)
from app.db.models import (
    AuthProvider,
    CustomerProfile,
    RefreshToken,
    Role,
    StaffProfile,
    StaffStatus,
    User,
    UserType,
    VenueSettings,
)
from app.schemas.auth import AccessTokenResponse, LoginResponse, UserSession

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# ─────────────────────────────────────────────────────────────────────────────
# User finders
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.staff_profile),
            selectinload(User.customer_profile),
        )
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.staff_profile),
            selectinload(User.customer_profile),
        )
        .where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


# ─────────────────────────────────────────────────────────────────────────────
# Initial admin bootstrap
# ─────────────────────────────────────────────────────────────────────────────

async def ensure_initial_admin(db: AsyncSession) -> None:
    existing = await get_user_by_email(db, settings.INITIAL_ADMIN_EMAIL)
    if existing:
        return

    admin_user = User(
        email=settings.INITIAL_ADMIN_EMAIL.lower(),
        full_name="Initial Admin",
        password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        user_type=UserType.STAFF,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
    )
    db.add(admin_user)
    await db.flush()
    db.add(
        StaffProfile(
            user_id=admin_user.id,
            role=Role.ADMIN,
            status=StaffStatus.ACTIVE,
        )
    )
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Staff password login
# ─────────────────────────────────────────────────────────────────────────────

async def authenticate_staff(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Verify email + password.  Returns User on success, None on failure."""
    await ensure_initial_admin(db)
    user = await get_user_by_email(db, email)
    if not user or user.user_type != UserType.STAFF:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.staff_profile or user.staff_profile.status != StaffStatus.ACTIVE:
        return None

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return await get_user_by_id(db, user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Staff PIN login  (blueprint §4.2 B)
# ─────────────────────────────────────────────────────────────────────────────

async def _get_pin_lockout_policy(db: AsyncSession) -> tuple[int, int]:
    """Return (max_attempts, lockout_minutes) from VenueSettings."""
    venue = await db.scalar(select(VenueSettings))
    max_attempts = venue.pin_max_attempts if venue else 5
    lockout_minutes = venue.pin_lockout_minutes if venue else 5
    return max_attempts, lockout_minutes


async def authenticate_staff_by_pin(
    db: AsyncSession,
    branch_id: int,
    pin: str,
) -> User:
    """
    Look up a staff member by branch + PIN, enforcing:
      • ACTIVE status check
      • Lockout after N failed attempts (configurable in VenueSettings)
      • Lockout TTL — automatic unlock after lockout_minutes

    Returns the authenticated User on success.
    Raises ValueError with an appropriate message on failure
    (callers map to HTTP 401 / 423).
    """
    max_attempts, lockout_minutes = await _get_pin_lockout_policy(db)

    # Find all ACTIVE staff for this branch who have a PIN set
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.staff_profile),
            selectinload(User.customer_profile),
        )
        .join(StaffProfile)
        .where(
            StaffProfile.branch_id == branch_id,
            StaffProfile.status == StaffStatus.ACTIVE,
            StaffProfile.pin_hash.is_not(None),
            User.is_active == True,
        )
    )
    candidates = result.scalars().all()

    now = datetime.now(UTC)
    for user in candidates:
        profile = user.staff_profile

        # Check lockout
        if profile.pin_locked_until and profile.pin_locked_until > now:
            # Don't reveal which account is locked during brute-force scan
            continue

        # Auto-clear expired lockout
        if profile.pin_locked_until and profile.pin_locked_until <= now:
            profile.pin_failed_attempts = 0
            profile.pin_locked_until = None

        if not verify_pin(pin, profile.pin_hash):
            continue

        # ── PIN matched ──────────────────────────────────────────────────────
        profile.pin_failed_attempts = 0
        profile.pin_locked_until = None
        user.last_login_at = now
        await db.commit()
        return await get_user_by_id(db, user.id)

    # No match — increment failure counters for ALL branch candidates
    # (so lockout still triggers even if attacker guesses wrong user)
    locked_until = None
    for user in candidates:
        profile = user.staff_profile
        if profile.pin_locked_until and profile.pin_locked_until > now:
            continue  # already locked, don't reset counter
        profile.pin_failed_attempts = (profile.pin_failed_attempts or 0) + 1
        if profile.pin_failed_attempts >= max_attempts:
            locked_until = now + timedelta(minutes=lockout_minutes)
            profile.pin_locked_until = locked_until
    if candidates:
        await db.commit()

    if locked_until:
        raise ValueError(
            f"Too many failed attempts. PIN locked for {lockout_minutes} minutes."
        )
    raise ValueError("Invalid PIN.")


# ─────────────────────────────────────────────────────────────────────────────
# Token building helpers
# ─────────────────────────────────────────────────────────────────────────────

def _staff_token_claims(user: User) -> dict:
    role = user.staff_profile.role.value if user.staff_profile else None
    branch_id = user.staff_profile.branch_id if user.staff_profile else None
    return {
        "role": role,
        "branch_id": branch_id,
        "user_type": UserType.STAFF.value,
    }


def build_staff_access_token(user: User) -> str:
    return create_access_token(
        subject=user.id,
        extra_claims=_staff_token_claims(user),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Refresh token DB persistence  (blueprint §4.2 A)
# ─────────────────────────────────────────────────────────────────────────────

def _hash_token(raw_token: str) -> str:
    """SHA-256 hex of the raw token — fast, non-reversible lookup key."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def store_refresh_token(
    db: AsyncSession,
    user_id: int,
    raw_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshToken:
    """Persist a new refresh token entry."""
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str]:
    """
    Validate an incoming refresh token, revoke it, issue a new one.
    Raises ValueError on any invalid state.
    """
    # Verify JWT signature / expiry first (cheap, no DB)
    try:
        payload = verify_token(raw_token, "refresh")
    except ValueError as exc:
        raise ValueError("Invalid refresh token.") from exc

    user_id = int(payload["sub"])

    # Look up the DB record
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == _hash_token(raw_token)
        )
    )
    record = result.scalar_one_or_none()

    if not record or not record.is_valid:
        raise ValueError("Refresh token revoked or expired.")
    if record.user_id != user_id:
        raise ValueError("Token user mismatch.")

    # Revoke old token
    record.revoked_at = datetime.now(UTC)

    # Issue new token
    new_raw = create_refresh_token(user_id)
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise ValueError("User not found or inactive.")

    await store_refresh_token(db, user_id, new_raw, user_agent, ip_address)
    await db.commit()

    return user, new_raw


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: int) -> int:
    """Revoke all active refresh tokens for a user (full logout)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.revoked_at = now
    await db.commit()
    return len(tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Login response builders
# ─────────────────────────────────────────────────────────────────────────────

def build_user_session(user: User) -> UserSession:
    session = UserSession(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type,
        auth_provider=user.auth_provider,
    )

    if user.user_type == UserType.STAFF and user.staff_profile:
        session.role = user.staff_profile.role
        session.staff_status = user.staff_profile.status
        session.branch_id = user.staff_profile.branch_id
        session.has_pin = bool(user.staff_profile.pin_hash)

    elif user.user_type == UserType.CUSTOMER and user.customer_profile:
        session.loyalty_points = user.customer_profile.loyalty_points

    return session


async def build_login_response(
    db: AsyncSession,
    user: User,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[LoginResponse, str]:
    """
    Build a LoginResponse (access token + session) and a new refresh token.
    Persists the refresh token to the DB for rotation / revocation support.
    Returns (response, raw_refresh_token).
    """
    access_token = build_staff_access_token(user)
    raw_refresh = create_refresh_token(user.id)
    await store_refresh_token(db, user.id, raw_refresh, user_agent, ip_address)

    return (
        LoginResponse(
            access_token=access_token,
            session=build_user_session(user),
        ),
        raw_refresh,
    )


def build_access_response(user: User) -> AccessTokenResponse:
    """Lightweight access-only response (no refresh — for short-lived contexts)."""
    return AccessTokenResponse(access_token=build_staff_access_token(user))


# ─────────────────────────────────────────────────────────────────────────────
# Google OAuth (customers)
# ─────────────────────────────────────────────────────────────────────────────

async def login_customer_with_google(
    db: AsyncSession,
    code: str,
) -> tuple[AccessTokenResponse, str]:
    if not settings.google_oauth_enabled:
        raise ValueError("Google OAuth is not configured.")

    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        google_access_token = token_resp.json()["access_token"]

        profile_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

    email = str(profile["email"]).lower()
    google_subject = str(profile["sub"])
    full_name = profile.get("name") or email

    customer_query = await db.execute(
        select(User)
        .options(selectinload(User.customer_profile))
        .join(CustomerProfile, isouter=True)
        .where(
            or_(
                User.email == email,
                CustomerProfile.google_subject == google_subject,
            )
        )
    )
    user = customer_query.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            user_type=UserType.CUSTOMER,
            auth_provider=AuthProvider.GOOGLE,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        db.add(
            CustomerProfile(
                user_id=user.id,
                google_subject=google_subject,
                preferences={"source": "google_oauth"},
            )
        )
    else:
        user.full_name = full_name
        user.auth_provider = AuthProvider.GOOGLE
        user.is_active = True
        if user.customer_profile is None:
            db.add(CustomerProfile(user_id=user.id, google_subject=google_subject))
        else:
            user.customer_profile.google_subject = google_subject

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    access_token = create_access_token(
        subject=user.id,
        extra_claims={"user_type": UserType.CUSTOMER.value},
    )
    refresh_token = create_refresh_token(subject=user.id)
    await store_refresh_token(db, user.id, refresh_token)
    return AccessTokenResponse(access_token=access_token), refresh_token


# ─────────────────────────────────────────────────────────────────────────────
# Staff activation token
# ─────────────────────────────────────────────────────────────────────────────

def create_staff_activation_token(user_id: int) -> str:
    return create_access_token(
        subject=user_id,
        extra_claims={
            "scope": "staff_activate",
            "exp": int(
                (
                    datetime.now(UTC)
                    + timedelta(hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS)
                ).timestamp()
            ),
        },
    )