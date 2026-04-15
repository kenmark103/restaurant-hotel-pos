"""
routes/staff.py
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin, require_manager
from app.db.models import User
from app.db.session import get_db
from app.schemas.staff import (
    AdminSetPinRequest,
    StaffActivateRequest,
    StaffInviteRequest,
    StaffRead,
    StaffUpdateRequest,
)
from app.services import staff as staff_svc

router = APIRouter()


@router.get("", response_model=list[StaffRead])
async def list_staff(
    branch_id: int | None = None,
    _: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    return await staff_svc.list_staff(db, branch_id=branch_id)


@router.post("", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    payload: StaffInviteRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    staff_read, activation_token = await staff_svc.invite_staff_member(
        db, payload, created_by=current_user.id
    )
    # In production: email the activation_token to staff_read.email
    return staff_read


@router.post("/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_account(
    payload: StaffActivateRequest,
    db: AsyncSession = Depends(get_db),
):
    success = await staff_svc.activate_staff_account(db, payload.token, payload.password)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid or expired activation token.")


@router.put("/{staff_id}", response_model=StaffRead)
async def update_staff(
    staff_id: int,
    payload: StaffUpdateRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    return await staff_svc.update_staff_member(db, staff_id, payload, updated_by=current_user.id)


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_staff(
    staff_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await staff_svc.disable_staff(db, staff_id, disabled_by=current_user.id)


# ── PIN management ────────────────────────────────────────────────────────────

@router.post("/{staff_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_pin(
    staff_id: int,
    payload: AdminSetPinRequest,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    await staff_svc.set_staff_pin(db, staff_id, payload.pin, set_by=current_user.id)


@router.delete("/{staff_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def reset_pin(
    staff_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    await staff_svc.reset_staff_pin(db, staff_id, reset_by=current_user.id)


@router.post("/{staff_id}/pin/unlock", status_code=status.HTTP_204_NO_CONTENT)
async def unlock_pin(
    staff_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    await staff_svc.unlock_staff_pin(db, staff_id, unlocked_by=current_user.id)