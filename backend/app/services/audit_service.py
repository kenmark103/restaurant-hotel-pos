"""
audit_service.py — Audit log query service
─────────────────────────────────────────────────────────────────────────────
Read-only access to the AuditLog table.  The log itself is written by other
services (staff.py, cash_service.py, pos_service.py, override_service.py).
This service only queries — never writes.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import AuditAction, AuditLog, User
from app.services.base import BaseService


class AuditService(BaseService[AuditLog]):
    model = AuditLog

    async def get_logs(
        self,
        branch_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        """
        Filtered, paginated audit log query.
        All parameters are optional — omit to get the full log.
        Results ordered newest-first.
        """
        query = (
            select(AuditLog)
            .options(
                selectinload(AuditLog.actor),
                selectinload(AuditLog.approved_by),
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if branch_id is not None:
            query = query.where(AuditLog.branch_id == branch_id)
        if actor_id is not None:
            query = query.where(AuditLog.actor_id == actor_id)
        if action is not None:
            query = query.where(AuditLog.action == action)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if from_dt is not None:
            query = query.where(AuditLog.created_at >= from_dt)
        if to_dt is not None:
            query = query.where(AuditLog.created_at <= to_dt)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_log(self, log_id: int) -> AuditLog:
        return await self.get_or_404(log_id)