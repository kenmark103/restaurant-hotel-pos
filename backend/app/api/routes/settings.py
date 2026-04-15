"""
routes/settings.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin, require_manager
from app.db.models import User
from app.db.session import get_db
from app.services.settings_service import PublicSettingsService, SettingsService

router = APIRouter()


def _svc(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> SettingsService:
    return SettingsService(db, user)


# ── Public (no auth) ──────────────────────────────────────────────────────────

@router.get("/public")
async def public_settings(db: AsyncSession = Depends(get_db)):
    return await PublicSettingsService(db).get_public_settings()


# ── Venue ─────────────────────────────────────────────────────────────────────

@router.get("/venue")
async def get_venue(_: User = Depends(require_manager), svc: SettingsService = Depends(_svc)):
    return await svc.get_venue_settings()


@router.patch("/venue")
async def update_venue(
    updates: dict,
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(_svc),
):
    return await svc.update_venue_settings(**updates)


# ── Branches ──────────────────────────────────────────────────────────────────

@router.get("/branches")
async def list_branches(
    active_only: bool = True,
    _: User = Depends(require_manager),
    svc: SettingsService = Depends(_svc),
):
    return await svc.list_branches(active_only=active_only)


@router.post("/branches", status_code=status.HTTP_201_CREATED)
async def create_branch(
    name: str,
    code: str,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    timezone: str = "Africa/Nairobi",
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(_svc),
):
    return await svc.create_branch(name, code, address, phone, timezone)


@router.patch("/branches/{branch_id}")
async def update_branch(
    branch_id: int,
    updates: dict,
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(_svc),
):
    return await svc.update_branch(branch_id, **updates)


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_branch(
    branch_id: int,
    _: User = Depends(require_admin),
    svc: SettingsService = Depends(_svc),
):
    await svc.deactivate_branch(branch_id)