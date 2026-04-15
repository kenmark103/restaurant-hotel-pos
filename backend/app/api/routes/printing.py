"""
routes/printing.py
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_cashier, require_manager
from app.db.models import PrintJobStatus, PrintJobType, User
from app.db.session import get_db
from app.services.printing_service import PrintingService

router = APIRouter()


def _print(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> PrintingService:
    return PrintingService(db, user)


@router.get("/jobs")
async def list_print_jobs(
    branch_id: int,
    job_status: Optional[PrintJobStatus] = None,
    job_type: Optional[PrintJobType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    _: User = Depends(require_cashier),
    svc: PrintingService = Depends(_print),
):
    return await svc.list_print_jobs(
        branch_id=branch_id,
        job_status=job_status,
        job_type=job_type,
        skip=skip,
        limit=limit,
    )


@router.get("/jobs/{job_id}")
async def get_print_job(
    job_id: int,
    _: User = Depends(require_cashier),
    svc: PrintingService = Depends(_print),
):
    return await svc.get_print_job(job_id)


@router.post("/receipt/{order_id}")
async def print_receipt(
    order_id: int,
    _: User = Depends(require_cashier),
    svc: PrintingService = Depends(_print),
):
    job = await svc.print_receipt(order_id)
    return {"job_id": job.id, "pdf_url": job.pdf_url, "status": job.status}


@router.post("/receipt/{order_id}/reprint")
async def reprint_receipt(
    order_id: int,
    _: User = Depends(require_cashier),
    svc: PrintingService = Depends(_print),
):
    job = await svc.print_receipt(order_id, is_reprint=True)
    return {"job_id": job.id, "pdf_url": job.pdf_url, "status": job.status}


@router.post("/station-ticket/{order_id}/{station_id}")
async def print_station_ticket(
    order_id: int,
    station_id: str,
    _: User = Depends(require_cashier),
    svc: PrintingService = Depends(_print),
):
    job = await svc.print_station_ticket(order_id, station_id)
    return {"job_id": job.id, "pdf_url": job.pdf_url, "status": job.status}


@router.post("/z-report")
async def print_z_report(
    branch_id: int,
    report_date: str,
    report_data: dict,
    _: User = Depends(require_manager),
    svc: PrintingService = Depends(_print),
):
    job = await svc.print_z_report(branch_id, report_date, report_data)
    return {"job_id": job.id, "pdf_url": job.pdf_url, "status": job.status}