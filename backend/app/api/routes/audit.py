"""
routes/audit.py — Audit log endpoints
─────────────────────────────────────────────────────────────────────────────
Read-only access to the AuditLog table.  MANAGER+ only.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_manager
from app.db.models import AuditAction, User
from app.db.session import get_db
from app.services.audit_service import AuditService

router = APIRouter()


class AuditLogRead(BaseModel):
    id: int
    branch_id: Optional[int]
    actor_id: int
    approved_by_id: Optional[int]
    action: AuditAction
    entity_type: Optional[str]
    entity_id: Optional[int]
    payload: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


def _svc(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> AuditService:
    return AuditService(db, user)


@router.get("/logs", response_model=list[AuditLogRead])
async def get_audit_logs(
    branch_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    from_dt: Optional[datetime] = Query(default=None, description="ISO datetime filter start"),
    to_dt: Optional[datetime] = Query(default=None, description="ISO datetime filter end"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    _: User = Depends(require_manager),
    svc: AuditService = Depends(_svc),
):
    """
    Paginated, filtered audit log.  All filters are optional.
    Returns newest-first.
    """
    return await svc.get_logs(
        branch_id=branch_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        from_dt=from_dt,
        to_dt=to_dt,
        skip=skip,
        limit=limit,
    )


@router.get("/logs/{log_id}", response_model=AuditLogRead)
async def get_audit_log(
    log_id: int,
    _: User = Depends(require_manager),
    svc: AuditService = Depends(_svc),
):
    return await svc.get_log(log_id)