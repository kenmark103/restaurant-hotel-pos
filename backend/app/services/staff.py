"""
staff.py — Staff lifecycle management
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  • invite_staff_member: fixed `created_by` parameter type annotation
    (was syntactically malformed: `created_by: int | None` → valid Python).
  • Added set_staff_pin()   — sets/replaces a staff PIN, writes AuditLog.
  • Added reset_staff_pin() — manager-initiated PIN clear (forces re-set).
  • Added unlock_staff_pin() — admin unlocks a locked-out account.
  • update_staff_member()  — partial update (role, branch, full_name).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_pin, generate_pin_fingerprint, verify_token
from app.db.models import (
    AuditAction,
    AuditLog,
    AuthProvider,
    StaffStatus,
    UserType,
)
from app.db.models import StaffProfile
from app.db.models import User
from app.schemas.staff import StaffInviteRequest, StaffRead, StaffUpdateRequest
from app.services.auth import (
    create_staff_activation_token,
    get_user_by_id,
)
from app.services.base import ConflictError, NotFoundError, PermissionError, ValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Invite
# ─────────────────────────────────────────────────────────────────────────────

async def invite_staff_member(
    db: AsyncSession,
    payload: StaffInviteRequest,
    created_by: int | None = None,   # BUG FIX: was syntactically invalid in v1
) -> tuple[StaffRead, str]:
    """
    Creates an INVITED staff user and returns the activation token that must
    be emailed to them.  No password is set at this stage.
    """
    # Guard against duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictError(f"Email '{payload.email}' is already registered.")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=None,
        user_type=UserType.STAFF,
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    profile = StaffProfile(
        user_id=user.id,
        role=payload.role,
        status=StaffStatus.INVITED,
        branch_id=payload.branch_id,
        created_by_user_id=created_by,
    )
    db.add(profile)

    if created_by:
        db.add(
            AuditLog(
                actor_id=created_by,
                action=AuditAction.STAFF_INVITED,
                entity_type="user",
                entity_id=user.id,
                payload={"email": user.email, "role": payload.role},
            )
        )

    await db.commit()

    activation_token = create_staff_activation_token(user.id)

    return (
        StaffRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=profile.role,
            status=profile.status,
            branch_id=profile.branch_id,
            has_pin=False,
        ),
        activation_token,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Activate
# ─────────────────────────────────────────────────────────────────────────────

async def activate_staff_account(
    db: AsyncSession,
    token: str,
    password: str,
) -> bool:
    """
    Validates the activation token, sets the password, and marks the staff
    account ACTIVE.  Returns True on success, False on any failure.
    """
    from app.core.security import hash_password  # local import avoids circular

    try:
        payload = verify_token(token, "access")
    except ValueError:
        return False

    if payload.get("scope") != "staff_activate":
        return False

    user = await get_user_by_id(db, int(payload["sub"]))
    if not user or user.user_type != UserType.STAFF or not user.staff_profile:
        return False
    if user.staff_profile.status == StaffStatus.DISABLED:
        return False

    user.password_hash = hash_password(password)
    user.staff_profile.status = StaffStatus.ACTIVE

    db.add(
        AuditLog(
            actor_id=user.id,
            action=AuditAction.STAFF_ACTIVATED,
            entity_type="user",
            entity_id=user.id,
            payload={"branch_id": user.staff_profile.branch_id},
        )
    )

    await db.commit()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# List / update / disable
# ─────────────────────────────────────────────────────────────────────────────

async def list_staff(db: AsyncSession, branch_id: int | None = None) -> list[StaffRead]:
    query = (
        select(User)
        .options(selectinload(User.staff_profile))
        .where(User.user_type == UserType.STAFF)
        .order_by(User.created_at.desc())
    )
    if branch_id is not None:
        query = query.join(StaffProfile).where(StaffProfile.branch_id == branch_id)

    result = await db.execute(query)
    users = result.scalars().all()
    return [
        StaffRead(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.staff_profile.role,
            status=u.staff_profile.status,
            branch_id=u.staff_profile.branch_id,
            has_pin=bool(u.staff_profile.pin_hash),
        )
        for u in users
        if u.staff_profile
    ]


async def update_staff_member(
    db: AsyncSession,
    staff_id: int,
    payload: StaffUpdateRequest,
    updated_by: int | None = None,
) -> StaffRead:
    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        raise NotFoundError("StaffProfile")

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.staff_profile.role = payload.role
    if payload.branch_id is not None:
        user.staff_profile.branch_id = payload.branch_id

    await db.commit()
    user = await get_user_by_id(db, staff_id)
    return StaffRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.staff_profile.role,
        status=user.staff_profile.status,
        branch_id=user.staff_profile.branch_id,
        has_pin=bool(user.staff_profile.pin_hash),
    )


async def disable_staff(
    db: AsyncSession,
    staff_id: int,
    disabled_by: int | None = None,
) -> None:
    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        return
    user.is_active = False
    user.staff_profile.status = StaffStatus.DISABLED

    if disabled_by:
        db.add(
            AuditLog(
                actor_id=disabled_by,
                action=AuditAction.STAFF_DISABLED,
                entity_type="user",
                entity_id=staff_id,
            )
        )

    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# PIN management  (blueprint §4.2 B, §5)
# ─────────────────────────────────────────────────────────────────────────────

async def set_staff_pin(
    db: AsyncSession,
    staff_id: int,
    pin: str,
    set_by: int,
) -> None:
    """
    Set or replace a staff PIN.

    Enforces:
      • 5-digit numeric format
      • Uniqueness within the branch (via pin_fingerprint index)

    Writes an AuditLog row.
    """
    from app.core.security import validate_pin_format

    if not validate_pin_format(pin):
        raise ValidationError("PIN must be exactly 5 numeric digits.")

    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        raise NotFoundError("StaffProfile")

    profile = user.staff_profile
    branch_id = profile.branch_id

    if branch_id is None:
        raise ValidationError("Staff must be assigned to a branch before setting a PIN.")

    fingerprint = generate_pin_fingerprint(pin, branch_id)

    # Check uniqueness — conflict handled by DB UNIQUE index but we give a
    # friendly error message first to avoid an opaque IntegrityError.
    from sqlalchemy import and_
    conflict = await db.scalar(
        select(StaffProfile).where(
            and_(
                StaffProfile.branch_id == branch_id,
                StaffProfile.pin_fingerprint == fingerprint,
                StaffProfile.user_id != staff_id,
            )
        )
    )
    if conflict:
        raise ConflictError("This PIN is already in use by another staff member at this branch.")

    profile.pin_hash = hash_pin(pin)
    profile.pin_fingerprint = fingerprint
    profile.pin_set_at = datetime.now(UTC)
    profile.pin_failed_attempts = 0
    profile.pin_locked_until = None

    db.add(
        AuditLog(
            actor_id=set_by,
            action=AuditAction.PIN_SET,
            entity_type="user",
            entity_id=staff_id,
            payload={"branch_id": branch_id},
        )
    )

    await db.commit()


async def reset_staff_pin(
    db: AsyncSession,
    staff_id: int,
    reset_by: int,
) -> None:
    """
    Clear a staff member's PIN (manager-initiated reset).
    Staff must re-set a new PIN on next touch.
    """
    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        raise NotFoundError("StaffProfile")

    profile = user.staff_profile
    profile.pin_hash = None
    profile.pin_fingerprint = None
    profile.pin_set_at = None
    profile.pin_failed_attempts = 0
    profile.pin_locked_until = None

    db.add(
        AuditLog(
            actor_id=reset_by,
            action=AuditAction.PIN_RESET,
            entity_type="user",
            entity_id=staff_id,
        )
    )
    await db.commit()


async def unlock_staff_pin(
    db: AsyncSession,
    staff_id: int,
    unlocked_by: int,
) -> None:
    """Admin manually clears a PIN lockout."""
    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        raise NotFoundError("StaffProfile")

    profile = user.staff_profile
    profile.pin_failed_attempts = 0
    profile.pin_locked_until = None

    db.add(
        AuditLog(
            actor_id=unlocked_by,
            action=AuditAction.PIN_UNLOCKED,
            entity_type="user",
            entity_id=staff_id,
        )
    )
    await db.commit()