"""
printing/printing_service.py — Print job orchestration
─────────────────────────────────────────────────────────────────────────────
Responsibilities:
  • Receive PrintRequested events (from event bus) or direct calls
  • Build ReceiptData / StationTicketData / ZReportData from DB objects
  • Render HTML via templates
  • Convert HTML → PDF (via weasyprint; swap for puppeteer/playwright if needed)
  • Write PrintJob rows (ledger for reprints + audit)
  • Store PDF to file system / S3 (URL stored in PrintJob.pdf_url)

MVP note:
  In development the PDF is written to /tmp/print_jobs/.
  In production, replace _store_pdf() with an S3/GCS upload.

Dependencies:
  pip install weasyprint   (or playwright for richer CSS support)
"""

import io
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuditAction,
    AuditLog,
    KitchenStation,
    PosOrder,
    PosOrderItem,
    PrintJob,
    PrintJobStatus,
    PrintJobType,
    VenueSettings,
)
from app.services.base import NotFoundError, ValidationError
from app.templates.printing.receipt import ReceiptData, render_receipt
from app.templates.printing.station_ticket import (
    StationTicketData,
    TicketItem,
    render_station_ticket,
)
from app.templates.printing.z_report import ZReportData, render_z_report

logger = logging.getLogger(__name__)

# Output directory for MVP file-based PDF storage
PDF_OUTPUT_DIR = Path(os.environ.get("PDF_OUTPUT_DIR", "/tmp/print_jobs"))
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PrintingService:

    def __init__(self, db: AsyncSession, current_user=None) -> None:
        self.db = db
        self.user = current_user

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def print_receipt(
        self,
        order_id: int,
        is_reprint: bool = False,
    ) -> PrintJob:
        """Generate a receipt PDF for a closed order."""
        order = await self._load_order(order_id)
        venue = await self.db.scalar(select(VenueSettings))
        data = ReceiptData.from_order(order, venue)
        html = render_receipt(data)
        job_type = PrintJobType.REPRINT if is_reprint else PrintJobType.RECEIPT
        return await self._generate_and_store(
            html=html,
            job_type=job_type,
            branch_id=order.branch_id,
            order_id=order_id,
            payload={"receipt_number": data.receipt_number},
        )

    async def print_station_ticket(
        self,
        order_id: int,
        station_id: str,
    ) -> PrintJob:
        """Generate a kitchen station ticket for a specific station's items."""
        order = await self._load_order(order_id)
        station = await self.db.get(KitchenStation, station_id)
        if not station:
            raise NotFoundError("KitchenStation")

        station_items = [
            TicketItem(
                name=i.menu_item_name,
                quantity=i.quantity,
                variant=i.variant_name,
                modifiers=[m.option_name for m in i.modifiers],
                note=i.note,
            )
            for i in order.items
            if not i.is_voided
            and any(t.station_id == station_id for t in i.kds_tickets)
        ]

        if not station_items:
            raise ValidationError(f"No items routed to station '{station.name}'")

        table_label = "Counter"
        if order.table:
            table_label = f"Table {order.table.table_number}"
        elif order.order_type == "takeaway":
            table_label = "Takeaway"
        elif order.order_type == "room_charge":
            table_label = f"Room {order.room_number}" if order.room_number else "Room"

        # Estimate max prep time across items for this station
        max_prep = max(
            (t.estimated_prep_time for i in order.items for t in i.kds_tickets if t.station_id == station_id),
            default=10,
        )

        data = StationTicketData(
            station_name=station.name,
            station_color=station.color,
            order_id=order_id,
            ticket_number=f"{station_id[:3].upper()}-{order_id:03d}",
            table_label=table_label,
            order_type=order.order_type.value,
            sent_at=datetime.now(UTC),
            items=station_items,
            estimated_minutes=max_prep,
        )
        html = render_station_ticket(data)
        return await self._generate_and_store(
            html=html,
            job_type=PrintJobType.STATION_TICKET,
            branch_id=order.branch_id,
            order_id=order_id,
            station_id=station_id,
            payload={"station": station.name},
        )

    async def print_z_report(
        self,
        branch_id: int,
        report_date_str: str,        # "YYYY-MM-DD"
        report_data: dict,           # from ReportingService.get_daily_sales_summary()
    ) -> PrintJob:
        """Generate a Z-Report PDF."""
        from datetime import date
        from decimal import Decimal

        branch = await self.db.get(__import__("app.db.models", fromlist=["Branch"]).Branch, branch_id)
        venue = await self.db.scalar(select(VenueSettings))

        payments = report_data.get("payment_breakdown", {})
        session = report_data.get("cash_session", {}) or {}

        data = ZReportData(
            branch_name=branch.name if branch else "Branch",
            branch_code=branch.code if branch else "BR",
            report_date=date.fromisoformat(report_date_str),
            generated_at=datetime.now(UTC),
            generated_by=self.user.full_name if self.user else "System",
            total_orders=report_data.get("total_orders", 0),
            total_revenue=Decimal(str(report_data.get("total_revenue", "0"))),
            total_discounts=Decimal(str(report_data.get("total_discounts", "0"))),
            total_tax=Decimal(str(report_data.get("total_tax", "0"))),
            void_count=report_data.get("void_count", 0),
            void_amount=Decimal(str(report_data.get("void_amount", "0"))),
            net_revenue=Decimal(str(report_data.get("net_revenue", "0"))),
            cash_total=Decimal(str(payments.get("cash", "0"))),
            card_total=Decimal(str(payments.get("card", "0"))),
            mobile_money_total=Decimal(str(payments.get("mobile_money", "0"))),
            complimentary_total=Decimal(str(payments.get("complimentary", "0"))),
            opening_float=Decimal(str(session.get("opening_float", "0"))),
            closing_float=Decimal(str(session.get("closing_float", "0"))),
            expected_closing=Decimal(str(session.get("expected_closing", "0"))),
            discrepancy=Decimal(str(session.get("discrepancy", "0"))),
            hourly=report_data.get("hourly_breakdown", []),
            top_items=report_data.get("top_items", []),
            currency_symbol=venue.currency_symbol if venue else "KSh",
        )
        html = render_z_report(data)
        return await self._generate_and_store(
            html=html,
            job_type=PrintJobType.Z_REPORT,
            branch_id=branch_id,
            payload={"date": report_date_str},
        )

    async def get_print_job(self, job_id: int) -> PrintJob:
        job = await self.db.get(PrintJob, job_id)
        if not job:
            raise NotFoundError("PrintJob")
        return job

    async def list_print_jobs(
        self,
        branch_id: int,
        job_status: PrintJobStatus | None = None,
        job_type: PrintJobType | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PrintJob]:
        """List print jobs for a branch, newest first."""
        query = (
            select(PrintJob)
            .where(PrintJob.branch_id == branch_id)
            .order_by(PrintJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if job_status is not None:
            query = query.where(PrintJob.status == job_status)
        if job_type is not None:
            query = query.where(PrintJob.job_type == job_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # PDF generation
    # ─────────────────────────────────────────────────────────────────────────

    async def _generate_and_store(
        self,
        html: str,
        job_type: PrintJobType,
        branch_id: int,
        order_id: Optional[int] = None,
        station_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> PrintJob:
        job = PrintJob(
            branch_id=branch_id,
            order_id=order_id,
            station_id=station_id,
            requested_by_id=self.user.id if self.user else 0,
            job_type=job_type,
            status=PrintJobStatus.PENDING,
            payload=payload,
        )
        self.db.add(job)
        await self.db.flush()   # get job.id

        try:
            pdf_bytes = self._html_to_pdf(html)
            pdf_url = await self._store_pdf(pdf_bytes, job.id, job_type)
            job.pdf_url = pdf_url
            job.status = PrintJobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
        except Exception as exc:
            logger.exception("PDF generation failed for job %s", job.id)
            job.status = PrintJobStatus.FAILED
            job.error_message = str(exc)[:500]

        await self.db.commit()
        await self.db.refresh(job)
        return job

    def _html_to_pdf(self, html: str) -> bytes:
        """
        Convert HTML → PDF bytes.

        Uses weasyprint.  To switch to Playwright:
          from playwright.sync_api import sync_playwright
          with sync_playwright() as p:
              browser = p.chromium.launch()
              page = browser.new_page()
              page.set_content(html)
              return page.pdf(format="A4")
        """
        try:
            from weasyprint import HTML  # type: ignore
            return HTML(string=html).write_pdf()
        except ImportError:
            # Fallback: return raw HTML bytes in development (no weasyprint installed)
            logger.warning("weasyprint not installed — returning HTML bytes instead of PDF")
            return html.encode("utf-8")

    async def _store_pdf(self, pdf_bytes: bytes, job_id: int, job_type: PrintJobType) -> str:
        """
        Store PDF bytes and return a URL/path.
        MVP: write to /tmp/print_jobs/<id>.pdf
        Production: replace with S3/GCS upload returning a signed URL.
        """
        filename = f"{job_type.value}_{job_id}_{uuid.uuid4().hex[:8]}.pdf"
        path = PDF_OUTPUT_DIR / filename
        path.write_bytes(pdf_bytes)
        # Return a relative URL that the API can serve via /static/print_jobs/<filename>
        return f"/static/print_jobs/{filename}"

    # ─────────────────────────────────────────────────────────────────────────
    # DB helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _load_order(self, order_id: int) -> PosOrder:
        result = await self.db.execute(
            select(PosOrder)
            .options(
                selectinload(PosOrder.items).selectinload(PosOrderItem.modifiers),
                selectinload(PosOrder.items).selectinload(PosOrderItem.kds_tickets),
                selectinload(PosOrder.payments),
                selectinload(PosOrder.table),
                selectinload(PosOrder.staff_user),
            )
            .where(PosOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("PosOrder")
        return order