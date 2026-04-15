"""
routes/reporting.py
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_manager
from app.db.models import User
from app.db.session import get_db
from app.services.reporting_service import ReportingService

router = APIRouter()


def _rep(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> ReportingService:
    return ReportingService(db, user)


@router.get("/daily")
async def daily_summary(
    branch_id: int,
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD, defaults to today"),
    _: User = Depends(require_manager),
    svc: ReportingService = Depends(_rep),
):
    report_date = datetime.fromisoformat(date) if date else None
    return await svc.get_daily_sales_summary(branch_id, date=report_date)


@router.get("/items")
async def top_items(
    branch_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    _: User = Depends(require_manager),
    svc: ReportingService = Depends(_rep),
):
    start = datetime.fromisoformat(date_from) if date_from else None
    end = datetime.fromisoformat(date_to) if date_to else None
    return await svc.get_top_items(branch_id, date_from=start, date_to=end, limit=limit)


@router.get("/staff")
async def staff_performance(
    branch_id: int,
    date: Optional[str] = None,
    _: User = Depends(require_manager),
    svc: ReportingService = Depends(_rep),
):
    report_date = datetime.fromisoformat(date) if date else None
    return await svc.get_staff_performance(branch_id, date=report_date)


@router.get("/inventory")
async def inventory_valuation(
    branch_id: int,
    _: User = Depends(require_manager),
    svc: ReportingService = Depends(_rep),
):
    return await svc.get_inventory_valuation(branch_id)


@router.get("/export/csv")
async def export_csv(
    branch_id: int,
    date: Optional[str] = None,
    _: User = Depends(require_manager),
    svc: ReportingService = Depends(_rep),
):
    report_date = datetime.fromisoformat(date) if date else None
    summary = await svc.get_daily_sales_summary(branch_id, date=report_date)
    csv_bytes = await svc.export_to_csv(summary)
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{branch_id}_{date or 'today'}.csv"},
    )