from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.staff import StaffActivationResponse, StaffActivateRequest, StaffInviteRequest, StaffRead
from app.services.auth import get_user_by_email
from app.services.staff import activate_staff_account, disable_staff, invite_staff_member, list_staff

router = APIRouter(prefix="/staff", tags=["staff"])


@router.post("/invite", response_model=StaffActivationResponse)
async def invite_staff(
    payload: StaffInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager"])),
) -> StaffActivationResponse:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use.")
    _, activation_token = await invite_staff_member(db, payload, created_by=current_user.id)
    return StaffActivationResponse(detail="Staff member invited.", activation_token=activation_token)


@router.post("/activate")
async def activate_account(
    payload: StaffActivateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    success = await activate_staff_account(db, payload.token, payload.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token.")
    return {"detail": "Account activated. You can now log in."}


@router.get("/", response_model=list[StaffRead])
async def get_staff_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> list[StaffRead]:
    return await list_staff(db)


@router.patch("/{staff_id}/disable")
async def disable_staff_member(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin"])),
) -> dict[str, str]:
    await disable_staff(db, staff_id)
    return {"detail": "Staff member disabled."}
