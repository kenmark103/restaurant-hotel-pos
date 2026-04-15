"""
table_service.py — Table & Reservation management
─────────────────────────────────────────────────────────────────────────────
Extracted from pos_service.py.  POSService imports get_active_table_order()
from here to avoid circular deps.

Covers:
  • Table CRUD (branch-scoped)
  • Floor status updates + WebSocket broadcast
  • Table reservations lifecycle
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import (
    PosOrder,
    PosOrderStatus,
    Table,
    TableReservation,
    TableStatus,
)
from app.services.base import BaseService, ConflictError, NotFoundError, ValidationError


class TableService(BaseService[Table]):
    model = Table

    def __init__(self, db, current_user=None, websocket_manager=None) -> None:
        super().__init__(db, current_user)
        self.ws = websocket_manager

    # ─────────────────────────────────────────────────────────────────────────
    # Shared helper  (also used by POSService.create_order)
    # ─────────────────────────────────────────────────────────────────────────

    async def get_active_table_order(self, table_id: int) -> Optional[PosOrder]:
        return await self.db.scalar(
            select(PosOrder).where(
                PosOrder.table_id == table_id,
                PosOrder.status.in_((PosOrderStatus.OPEN, PosOrderStatus.SENT)),
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Table CRUD
    # ─────────────────────────────────────────────────────────────────────────

    async def get_tables(
        self,
        branch_id: int,
        status: Optional[TableStatus] = None,
        floor_zone: Optional[str] = None,
    ) -> List[Table]:
        query = (
            select(Table)
            .where(Table.branch_id == branch_id)
            .order_by(Table.floor_zone, Table.table_number)
        )
        if status:
            query = query.where(Table.status == status)
        if floor_zone:
            query = query.where(Table.floor_zone == floor_zone)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_table(
        self,
        branch_id: int,
        table_number: str,
        capacity: int,
        floor_zone: Optional[str] = None,
        position_x: Optional[int] = None,
        position_y: Optional[int] = None,
    ) -> Table:
        existing = await self.db.scalar(
            select(Table).where(
                Table.branch_id == branch_id,
                Table.table_number == table_number,
            )
        )
        if existing:
            raise ConflictError(f"Table '{table_number}' already exists in this branch")

        table = Table(
            branch_id=branch_id,
            table_number=table_number,
            capacity=capacity,
            floor_zone=floor_zone,
            position_x=position_x,
            position_y=position_y,
        )
        self.db.add(table)
        await self.db.commit()
        await self.db.refresh(table)
        return table

    async def update_table(self, table_id: int, **updates) -> Table:
        table = await self.get_or_404(table_id)
        for key, value in updates.items():
            if value is not None and hasattr(table, key):
                setattr(table, key, value)
        await self.db.commit()
        await self.db.refresh(table)
        return table

    async def update_table_status(self, table_id: int, status: TableStatus) -> Table:
        table = await self.get_or_404(table_id)
        table.status = status
        await self.db.commit()
        if self.ws:
            await self.ws.notify_table_status(table.branch_id, table_id, status.value)
        return table

    async def delete_table(self, table_id: int) -> None:
        table = await self.get_or_404(table_id)
        if table.status == TableStatus.OCCUPIED:
            raise ValidationError("Cannot delete a table with an active order")
        await self.db.delete(table)
        await self.db.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Reservations
    # ─────────────────────────────────────────────────────────────────────────

    async def get_reservations(
        self,
        branch_id: int,
        date: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> List[TableReservation]:
        query = (
            select(TableReservation)
            .join(Table, TableReservation.table_id == Table.id)
            .options(selectinload(TableReservation.table))
            .where(Table.branch_id == branch_id)
            .order_by(TableReservation.reservation_time)
        )
        if date:
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = date.replace(hour=23, minute=59, second=59)
            query = query.where(TableReservation.reservation_time.between(day_start, day_end))
        if status:
            query = query.where(TableReservation.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_reservation(
        self,
        table_id: int,
        customer_name: str,
        party_size: int,
        reservation_time: datetime,
        duration_minutes: int = 120,
        customer_phone: Optional[str] = None,
        special_requests: Optional[str] = None,
    ) -> TableReservation:
        table = await self.get_or_404(table_id)
        if table.capacity < party_size:
            raise ValidationError(
                f"Table capacity ({table.capacity}) is less than party size ({party_size})"
            )

        reservation = TableReservation(
            table_id=table_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            reservation_time=reservation_time,
            duration_minutes=duration_minutes,
            special_requests=special_requests,
            status="confirmed",
        )
        self.db.add(reservation)
        table.status = TableStatus.RESERVED
        await self.db.commit()
        await self.db.refresh(reservation)

        if self.ws:
            await self.ws.notify_table_status(table.branch_id, table_id, "reserved")

        return reservation

    async def update_reservation_status(
        self,
        reservation_id: int,
        status: str,   # confirmed | seated | cancelled | no_show
    ) -> TableReservation:
        reservation = await self.db.get(TableReservation, reservation_id)
        if not reservation:
            raise NotFoundError("Reservation")

        reservation.status = status
        table = await self.db.get(Table, reservation.table_id)

        if table:
            if status == "seated":
                table.status = TableStatus.OCCUPIED
            elif status in ("cancelled", "no_show"):
                active = await self.get_active_table_order(table.id)
                if not active:
                    table.status = TableStatus.AVAILABLE

        await self.db.commit()
        if self.ws and table:
            await self.ws.notify_table_status(table.branch_id, table.id, table.status.value)

        return reservation

    async def cancel_reservation(self, reservation_id: int) -> None:
        await self.update_reservation_status(reservation_id, "cancelled")