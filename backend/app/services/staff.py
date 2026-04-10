from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_token, hash_password
from app.models.enums import AuthProvider, StaffStatus, UserType
from app.models.staff_profile import StaffProfile
from app.models.user import User
from app.schemas.staff import StaffInviteRequest, StaffRead
from app.services.auth import create_staff_activation_token, get_user_by_id


async def invite_staff_member(db: AsyncSession, payload: StaffInviteRequest, created_by: int | None) -> tuple[StaffRead, str]:
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
    await db.commit()

    return (
        StaffRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=profile.role,
            status=profile.status,
            branch_id=profile.branch_id,
        ),
        create_staff_activation_token(user.id),
    )


async def activate_staff_account(db: AsyncSession, token: str, password: str) -> bool:
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
    await db.commit()
    return True


async def list_staff(db: AsyncSession) -> list[StaffRead]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.staff_profile))
        .where(User.user_type == UserType.STAFF)
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        StaffRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.staff_profile.role,
            status=user.staff_profile.status,
            branch_id=user.staff_profile.branch_id,
        )
        for user in users
        if user.staff_profile
    ]


async def disable_staff(db: AsyncSession, staff_id: int) -> None:
    user = await get_user_by_id(db, staff_id)
    if not user or not user.staff_profile:
        return
    user.is_active = False
    user.staff_profile.status = StaffStatus.DISABLED
    await db.commit()
