"""
reporting_service.py — Business Intelligence & Reporting
─────────────────────────────────────────────────────────────────────────────
Covers:
  • Z-Report  (daily reconciliation)
  • Hourly sales breakdown
  • Top-selling items (menu engineering)
  • Staff performance
  • Inventory valuation (cost report)
  • COGS variance (theoretical vs actual)
  • CSV export helper

Note: ReportingService does NOT extend BaseService — it has no single primary
model and overriding _validate_model would be misleading boilerplate.
"""
import csv
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import between, extract, func, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    MenuItem,
    PaymentMethod,
    PosOrder,
    PosOrderItem,
    PosOrderStatus,
    StockMovement,
    StockMovementType,
)
from app.services.base import ValidationError, to_money
from app.services.inventory_service import InventoryService


class ReportingService:
    def __init__(self, db, current_user=None) -> None:
        self.db = db
        self.user = current_user
        self.inventory = InventoryService(db, current_user)

    # ═══════════════════════════════════════════════════════════════════════════
    # Z-REPORT  (daily sales reconciliation)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_daily_sales_summary(
        self,
        branch_id: int,
        date: Optional[datetime] = None,
    ) -> Dict:
        """
        Z-Report equivalent.
        Returns a full reconciliation of a trading day including:
          • Total orders, revenue, discounts, tax
          • Payment method breakdown
          • Void summary
          • Hourly breakdown
        """
        if not date:
            date = datetime.now(timezone.utc)

        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        orders_result = await self.db.execute(
            select(PosOrder)
            .options(selectinload(PosOrder.payments), selectinload(PosOrder.items))
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                between(PosOrder.closed_at, start, end),
            )
        )
        orders = orders_result.scalars().all()

        # Payment breakdown — uses PosPayment rows for split-tender accuracy
        payments: Dict[str, Decimal] = {m.value: Decimal("0.00") for m in PaymentMethod}
        for order in orders:
            for pmt in order.payments:
                payments[pmt.method.value] = to_money(
                    payments[pmt.method.value] + pmt.amount
                )

        total_sales = to_money(sum(o.total_amount for o in orders))
        total_discounts = to_money(sum(o.discount_total for o in orders))
        total_tax = to_money(sum(o.tax_amount for o in orders))
        total_subtotal = to_money(sum(o.subtotal for o in orders))

        # Voided items within the period
        voided_result = await self.db.execute(
            select(PosOrderItem)
            .join(PosOrder)
            .where(
                PosOrder.branch_id == branch_id,
                PosOrderItem.is_voided == True,
                PosOrderItem.voided_at.isnot(None),
                between(PosOrderItem.voided_at, start, end),
            )
        )
        voided_items = voided_result.scalars().all()

        # Voided orders within the period
        voided_orders_result = await self.db.execute(
            select(func.count(PosOrder.id)).where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.VOIDED,
                between(PosOrder.created_at, start, end),
            )
        )
        voided_order_count = voided_orders_result.scalar() or 0

        return {
            "date": date.strftime("%Y-%m-%d"),
            "branch_id": branch_id,
            "summary": {
                "total_orders": len(orders),
                "gross_sales": to_money(total_subtotal + total_tax),
                "total_discounts": total_discounts,
                "total_tax": total_tax,
                "net_sales": total_sales,
                "avg_order_value": to_money(total_sales / len(orders)) if orders else Decimal("0.00"),
                "void_items_count": len(voided_items),
                "void_items_amount": to_money(sum(i.line_total for i in voided_items)),
                "voided_orders_count": voided_order_count,
            },
            "payments": payments,
            "hourly_breakdown": await self._get_hourly_breakdown(branch_id, start, end),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # HOURLY BREAKDOWN
    # ═══════════════════════════════════════════════════════════════════════════

    async def _get_hourly_breakdown(
        self,
        branch_id: int,
        start: datetime,
        end: datetime,
    ) -> List[Dict]:
        """Sales aggregated by hour-of-day.  Uses DB extract() for efficiency."""
        result = await self.db.execute(
            select(
                extract("hour", PosOrder.closed_at).label("hour"),
                func.count(PosOrder.id).label("order_count"),
                func.sum(PosOrder.total_amount).label("revenue"),
            )
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                between(PosOrder.closed_at, start, end),
            )
            .group_by(extract("hour", PosOrder.closed_at))
            .order_by(extract("hour", PosOrder.closed_at))
        )

        rows = result.all()
        breakdown = []
        for row in rows:
            hour = int(row.hour)
            breakdown.append({
                "hour": hour,
                "label": f"{hour:02d}:00",
                "order_count": int(row.order_count),
                "revenue": to_money(row.revenue or 0),
            })

        return breakdown

    # ═══════════════════════════════════════════════════════════════════════════
    # MENU / ITEM PERFORMANCE  (Menu Engineering)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_item_performance(
        self,
        branch_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Top-selling items by quantity and revenue.
        Forms the basis of menu engineering analysis (stars / plowhorses / dogs).
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        result = await self.db.execute(
            select(
                PosOrderItem.menu_item_id,
                PosOrderItem.menu_item_name,
                func.sum(PosOrderItem.quantity).label("total_qty"),
                func.sum(PosOrderItem.line_total).label("total_revenue"),
                func.count(PosOrderItem.id.distinct()).label("times_ordered"),
            )
            .join(PosOrder)
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                PosOrderItem.is_voided == False,
                between(PosOrder.closed_at, start_date, end_date),
            )
            .group_by(PosOrderItem.menu_item_id, PosOrderItem.menu_item_name)
            .order_by(func.sum(PosOrderItem.quantity).desc())
            .limit(limit)
        )

        rows = result.all()
        total_qty = sum(r.total_qty or 0 for r in rows) or 1
        total_rev = sum(r.total_revenue or 0 for r in rows) or 1

        items = []
        for row in rows:
            qty = int(row.total_qty or 0)
            rev = to_money(row.total_revenue or 0)

            # Fetch cost price for margin calculation
            item = await self.db.get(MenuItem, row.menu_item_id)
            cost_price = item.cost_price if item else None
            margin = None
            if cost_price and qty > 0:
                total_cost = to_money(cost_price * qty)
                margin = to_money(
                    (rev - total_cost) / rev * 100
                ) if rev > 0 else None

            items.append({
                "menu_item_id": row.menu_item_id,
                "item_name": row.menu_item_name,
                "quantity_sold": qty,
                "revenue": rev,
                "times_ordered": int(row.times_ordered),
                "revenue_share_pct": to_money(rev / to_money(total_rev) * 100),
                "qty_share_pct": to_money(qty / total_qty * 100),
                "gross_margin_pct": margin,
            })

        return items

    # ═══════════════════════════════════════════════════════════════════════════
    # STAFF PERFORMANCE
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_staff_performance(
        self,
        branch_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict]:
        """Sales and productivity metrics per staff member."""
        result = await self.db.execute(
            select(
                PosOrder.staff_user_id,
                func.count(PosOrder.id).label("order_count"),
                func.sum(PosOrder.total_amount).label("total_sales"),
                func.avg(PosOrder.total_amount).label("avg_sale"),
                func.sum(PosOrder.discount_total).label("total_discounts_given"),
            )
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                between(PosOrder.closed_at, start_date, end_date),
            )
            .group_by(PosOrder.staff_user_id)
            .order_by(func.sum(PosOrder.total_amount).desc())
        )

        return [
            {
                "staff_id": row.staff_user_id,
                "orders_served": int(row.order_count),
                "total_sales": to_money(row.total_sales or 0),
                "avg_order_value": to_money(row.avg_sale or 0),
                "total_discounts_given": to_money(row.total_discounts_given or 0),
            }
            for row in result.all()
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # INVENTORY VALUATION
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_inventory_valuation(self, branch_id: int) -> Dict:
        """
        Current stock value report.
        Delegates to InventoryService.get_stock_valuation which uses the
        average costing method (cost_price on MenuItem/Variant).
        """
        return await self.inventory.get_stock_valuation(branch_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # COGS VARIANCE  (theoretical vs actual)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_cogs_variance_report(
        self,
        branch_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """
        Compares theoretical COGS (based on recipe/cost_price × qty sold) against
        actual stock depletion from the movement ledger.
        Variance = spoilage + theft + portioning errors.
        """
        # Theoretical COGS from order items
        sold_result = await self.db.execute(
            select(
                PosOrderItem.menu_item_id,
                func.sum(PosOrderItem.quantity).label("qty_sold"),
            )
            .join(PosOrder)
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                PosOrderItem.is_voided == False,
                between(PosOrder.closed_at, start_date, end_date),
            )
            .group_by(PosOrderItem.menu_item_id)
        )
        sold_rows = {r.menu_item_id: int(r.qty_sold) for r in sold_result.all()}

        # Actual depletion from ledger
        depleted_result = await self.db.execute(
            select(
                StockMovement.menu_item_id,
                func.sum(StockMovement.quantity).label("net_qty"),
                func.sum(
                    StockMovement.quantity * func.coalesce(StockMovement.unit_cost, 0)
                ).label("total_cost"),
            )
            .where(
                StockMovement.branch_id == branch_id,
                StockMovement.movement_type.in_([
                    StockMovementType.SALE,
                    StockMovementType.WASTE,
                ]),
                between(StockMovement.created_at, start_date, end_date),
            )
            .group_by(StockMovement.menu_item_id)
        )
        depleted_map = {
            r.menu_item_id: {
                "net_qty": Decimal(str(r.net_qty or 0)),
                "total_cost": Decimal(str(r.total_cost or 0)),
            }
            for r in depleted_result.all()
        }

        # Build line-by-line comparison
        line_items = []
        total_theoretical = Decimal("0.00")
        total_actual = Decimal("0.00")

        for item_id, qty_sold in sold_rows.items():
            item = await self.db.get(MenuItem, item_id)
            if not item:
                continue
            cost_price = item.cost_price or Decimal("0")
            theoretical = to_money(cost_price * qty_sold)
            actual_data = depleted_map.get(item_id, {})
            actual = to_money(abs(actual_data.get("total_cost", Decimal("0"))))

            variance = to_money(actual - theoretical)
            total_theoretical += theoretical
            total_actual += actual

            line_items.append({
                "menu_item_id": item_id,
                "item_name": item.name,
                "qty_sold": qty_sold,
                "cost_price": to_money(cost_price),
                "theoretical_cogs": theoretical,
                "actual_cogs": actual,
                "variance": variance,
                "variance_pct": to_money(variance / theoretical * 100) if theoretical > 0 else None,
            })

        return {
            "branch_id": branch_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "totals": {
                "theoretical_cogs": to_money(total_theoretical),
                "actual_cogs": to_money(total_actual),
                "total_variance": to_money(total_actual - total_theoretical),
            },
            "items": sorted(line_items, key=lambda x: abs(x["variance"]), reverse=True),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # SALES TREND  (multi-day)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_sales_trend(
        self,
        branch_id: int,
        days: int = 30,
    ) -> List[Dict]:
        """Daily revenue trend for charting."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.date(PosOrder.closed_at).label("sale_date"),
                func.count(PosOrder.id).label("order_count"),
                func.sum(PosOrder.total_amount).label("revenue"),
                func.sum(PosOrder.discount_total).label("discounts"),
            )
            .where(
                PosOrder.branch_id == branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                between(PosOrder.closed_at, start_date, end_date),
            )
            .group_by(func.date(PosOrder.closed_at))
            .order_by(func.date(PosOrder.closed_at))
        )

        return [
            {
                "date": str(row.sale_date),
                "order_count": int(row.order_count),
                "revenue": to_money(row.revenue or 0),
                "discounts": to_money(row.discounts or 0),
            }
            for row in result.all()
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # EXPORT HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def export_to_csv(self, data: List[Dict], headers: Optional[List[str]] = None) -> str:
        """
        Serialize a list of dicts to a CSV string.
        Headers are auto-detected from the first row if not supplied.

        Usage::

            csv_str = svc.export_to_csv(await svc.get_item_performance(...))
            return Response(content=csv_str, media_type="text/csv")
        """
        if not data:
            return ""

        buffer = io.StringIO()
        fieldnames = headers or list(data[0].keys())
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for row in data:
            # Convert Decimals / datetimes to strings for CSV safety
            cleaned = {
                k: str(v) if isinstance(v, (Decimal, datetime)) else v
                for k, v in row.items()
            }
            writer.writerow(cleaned)

        return buffer.getvalue()