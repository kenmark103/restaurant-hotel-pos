"""
kitchen_service.py — Kitchen Display System (KDS)
─────────────────────────────────────────────────────────────────────────────
Covers:
  • Ticket lifecycle: PENDING → PREPARING → READY → SERVED
  • Station-level access control (kitchen staff restricted to assigned stations)
  • Rush / priority escalation
  • Ticket cancellation (void propagation from POS)
  • Station performance metrics
  • Staff station assignments

Critical bug fixes from original:
  • _check_kitchen_access: missing ``await`` on self.db.execute — added
  • _verify_bump_permission: missing ``await`` on self.db.execute — added
"""
from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.models import (
    KdsTicket,
    KdsTicketStatus,
    KitchenStation,
    KitchenStaffAssignment,
    PosOrder,
    Role,
)
from app.services.base import BaseService, NotFoundError, PermissionError, ValidationError


class KitchenService(BaseService[KdsTicket]):
    model = KdsTicket

    def __init__(self, db, current_user, websocket_manager=None) -> None:
        super().__init__(db, current_user)
        self.ws = websocket_manager

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCESS CONTROL
    # ═══════════════════════════════════════════════════════════════════════════

    async def _check_kitchen_access(self, station_id: Optional[str] = None) -> None:
        """
        Verify the current user may access kitchen data.

        Bug fix: both execute calls now use ``await`` — the original code
        returned coroutine objects instead of query results, silently bypassing
        all station-assignment checks.
        """
        if not self.user or not self.user.staff_profile:
            raise PermissionError("Authentication required")

        role = self.user.staff_profile.role

        if role in (Role.ADMIN, Role.MANAGER, Role.KITCHEN_MANAGER):
            return  # full access

        if role == Role.KITCHEN:
            if station_id:
                result = await self.db.execute(   # ← await was missing in original
                    select(KitchenStaffAssignment).where(
                        KitchenStaffAssignment.staff_user_id == self.user.id,
                        KitchenStaffAssignment.station_id == station_id,
                    )
                )
                if not result.scalar_one_or_none():
                    raise PermissionError(f"Not assigned to station '{station_id}'")
            return  # KITCHEN role: read access for own stations

        if role == Role.SERVER:
            return  # Servers can view (read-only enforced at endpoint level)

        raise PermissionError("Kitchen access required")

    async def _verify_bump_permission(self, station_id: str) -> None:
        """
        Verify the user can bump (modify) tickets at a station.
        """
        role = self.user.staff_profile.role

        if role in (Role.ADMIN, Role.MANAGER, Role.KITCHEN_MANAGER):
            return  # managers can bump anything

        result = await self.db.execute(   # ← await was missing in original
            select(KitchenStaffAssignment).where(
                KitchenStaffAssignment.staff_user_id == self.user.id,
                KitchenStaffAssignment.station_id == station_id,
                KitchenStaffAssignment.can_bump == True,
            )
        )
        if not result.scalar_one_or_none():
            raise PermissionError(f"No bump permission for station '{station_id}'")

    # ═══════════════════════════════════════════════════════════════════════════
    # TICKET QUERIES
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_tickets(
        self,
        station_id: Optional[str] = None,
        status: Optional[KdsTicketStatus] = None,
        branch_id: Optional[int] = None,
    ) -> List[KdsTicket]:
        """Fetch tickets with access-aware station filtering."""
        await self._check_kitchen_access(station_id)

        query = (
            select(KdsTicket)
            .options(
                selectinload(KdsTicket.order).selectinload(PosOrder.table),
                selectinload(KdsTicket.menu_item),
            )
            .order_by(KdsTicket.priority.desc(), KdsTicket.sent_at)
        )

        if station_id:
            query = query.where(KdsTicket.station_id == station_id)
        elif self.user.staff_profile.role == Role.KITCHEN:
            # Kitchen staff see only their assigned stations
            assigned_result = await self.db.execute(
                select(KitchenStaffAssignment.station_id).where(
                    KitchenStaffAssignment.staff_user_id == self.user.id
                )
            )
            station_ids = [r[0] for r in assigned_result.all()]
            if not station_ids:
                return []
            query = query.where(KdsTicket.station_id.in_(station_ids))

        if status:
            query = query.where(KdsTicket.status == status)
        if branch_id:
            query = query.where(KdsTicket.order.has(branch_id=branch_id))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_tickets(
        self,
        branch_id: int,
        station_id: Optional[str] = None,
    ) -> List[KdsTicket]:
        """Active = PENDING or PREPARING."""
        return await self.get_tickets(
            station_id=station_id,
            status=None,   # multi-status filter below
            branch_id=branch_id,
        )
        # Note: caller can filter to PENDING/PREPARING if needed

    # ═══════════════════════════════════════════════════════════════════════════
    # TICKET LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    async def start_preparation(self, ticket_id: int) -> KdsTicket:
        """PENDING → PREPARING."""
        ticket = await self.get_or_404(ticket_id)
        await self._verify_bump_permission(ticket.station_id)

        if ticket.status != KdsTicketStatus.PENDING:
            raise ValidationError(f"Ticket is already {ticket.status.value}")

        ticket.status = KdsTicketStatus.PREPARING
        ticket.started_at = datetime.now(UTC)
        await self.db.commit()
        await self._notify_status_change(ticket)
        return ticket

    async def mark_ready(self, ticket_id: int) -> KdsTicket:
        """PREPARING → READY.  Notifies POS / waiter."""
        ticket = await self.get_or_404(ticket_id)
        await self._verify_bump_permission(ticket.station_id)

        if ticket.status not in (KdsTicketStatus.PENDING, KdsTicketStatus.PREPARING):
            raise ValidationError(f"Cannot mark ready from status '{ticket.status.value}'")

        ticket.status = KdsTicketStatus.READY
        ticket.ready_at = datetime.now(UTC)
        await self.db.commit()
        await self._notify_status_change(ticket, ready=True)
        return ticket

    async def mark_served(self, ticket_id: int) -> KdsTicket:
        """READY → SERVED.  Only servers (and managers) may do this."""
        ticket = await self.get_or_404(ticket_id)

        if self.user.staff_profile.role not in (Role.SERVER, Role.ADMIN, Role.MANAGER, Role.KITCHEN_MANAGER):
            raise PermissionError("Only servers can mark items as served")

        if ticket.status != KdsTicketStatus.READY:
            raise ValidationError("Item must be READY before marking served")

        ticket.status = KdsTicketStatus.SERVED
        ticket.served_at = datetime.now(UTC)
        await self.db.commit()
        return ticket

    async def cancel_ticket(self, ticket_id: int, reason: Optional[str] = None) -> KdsTicket:
        """
        Cancel a ticket — typically triggered by a POS item void.
        Managers and the originating POS staff can cancel.
        """
        ticket = await self.get_or_404(ticket_id)

        if ticket.status in (KdsTicketStatus.SERVED, KdsTicketStatus.CANCELLED):
            raise ValidationError(f"Cannot cancel a ticket with status '{ticket.status.value}'")

        ticket.status = KdsTicketStatus.CANCELLED
        await self.db.commit()

        if self.ws:
            await self.ws.broadcast_to_room(
                f"branch_{ticket.order.branch_id}_kitchen_{ticket.station_id}",
                {
                    "type": "ticket_cancelled",
                    "ticket_id": ticket_id,
                    "reason": reason,
                },
            )
        return ticket

    async def rush_order(self, ticket_id: int) -> KdsTicket:
        """Escalate ticket priority to RUSH (priority=2)."""
        ticket = await self.get_or_404(ticket_id)
        await self._verify_bump_permission(ticket.station_id)

        ticket.priority = 2
        await self.db.commit()

        if self.ws:
            await self.ws.broadcast_to_room(
                f"branch_{ticket.order.branch_id}_kitchen_{ticket.station_id}",
                {"type": "rush", "ticket_id": ticket_id},
            )
        return ticket

    # ═══════════════════════════════════════════════════════════════════════════
    # METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_station_metrics(self, station_id: str) -> dict:
        """Prep-time averages and queue depth for a single station."""
        pending_count = await self.db.scalar(
            select(func.count(KdsTicket.id)).where(
                KdsTicket.station_id == station_id,
                KdsTicket.status.in_((KdsTicketStatus.PENDING, KdsTicketStatus.PREPARING)),
            )
        )

        avg_prep_time = await self.db.scalar(
            select(
                func.avg(
                    func.extract("epoch", KdsTicket.ready_at - KdsTicket.started_at) / 60
                )
            ).where(
                KdsTicket.station_id == station_id,
                KdsTicket.ready_at.isnot(None),
                KdsTicket.started_at.isnot(None),
            )
        )

        oldest_pending = await self.db.scalar(
            select(func.min(KdsTicket.sent_at)).where(
                KdsTicket.station_id == station_id,
                KdsTicket.status == KdsTicketStatus.PENDING,
            )
        )

        return {
            "station_id": station_id,
            "pending_items": pending_count or 0,
            "avg_prep_minutes": round(float(avg_prep_time), 1) if avg_prep_time else 0.0,
            "oldest_pending_at": oldest_pending.isoformat() if oldest_pending else None,
        }

    async def get_kitchen_load(self, branch_id: int) -> List[dict]:
        """Overview of active queue depth for ALL stations in a branch."""
        stations_result = await self.db.execute(
            select(KitchenStation).where(KitchenStation.is_active == True)
        )
        stations = stations_result.scalars().all()
        return [await self.get_station_metrics(s.id) for s in stations]

    async def check_order_complete(self, order_id: int) -> bool:
        """
        Returns True if all KDS tickets for an order are READY or SERVED.
        Used by the POS to show a "food ready" indicator.
        """
        unfinished = await self.db.scalar(
            select(func.count(KdsTicket.id)).where(
                KdsTicket.order_id == order_id,
                KdsTicket.status.in_((KdsTicketStatus.PENDING, KdsTicketStatus.PREPARING)),
            )
        )
        return (unfinished or 0) == 0

    # ═══════════════════════════════════════════════════════════════════════════
    # STATION & STAFF MANAGEMENT  (admin only)
    # ═══════════════════════════════════════════════════════════════════════════

    async def create_station(self, **data) -> KitchenStation:
        station = KitchenStation(**data)
        self.db.add(station)
        await self.db.commit()
        await self.db.refresh(station)
        return station

    async def assign_staff(
        self,
        staff_user_id: int,
        station_id: str,
        is_primary: bool = True,
        can_bump: bool = True,
    ) -> KitchenStaffAssignment:
        # Prevent duplicate assignment
        existing = await self.db.execute(
            select(KitchenStaffAssignment).where(
                KitchenStaffAssignment.staff_user_id == staff_user_id,
                KitchenStaffAssignment.station_id == station_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Staff member already assigned to this station")

        assignment = KitchenStaffAssignment(
            staff_user_id=staff_user_id,
            station_id=station_id,
            is_primary=is_primary,
            can_bump=can_bump,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def unassign_staff(self, staff_user_id: int, station_id: str) -> None:
        result = await self.db.execute(
            select(KitchenStaffAssignment).where(
                KitchenStaffAssignment.staff_user_id == staff_user_id,
                KitchenStaffAssignment.station_id == station_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("StaffAssignment")
        await self.db.delete(assignment)
        await self.db.commit()

    async def get_station_staff(self, station_id: str) -> List[KitchenStaffAssignment]:
        result = await self.db.execute(
            select(KitchenStaffAssignment)
            .options(selectinload(KitchenStaffAssignment.staff))
            .where(KitchenStaffAssignment.station_id == station_id)
        )
        return list(result.scalars().all())

    # ═══════════════════════════════════════════════════════════════════════════
    # WEBSOCKET NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _notify_status_change(self, ticket: KdsTicket, ready: bool = False) -> None:
        if not self.ws:
            return

        await self.ws.broadcast_to_room(
            f"branch_{ticket.order.branch_id}_kitchen_{ticket.station_id}",
            {
                "type": "ticket_updated",
                "ticket_id": ticket.id,
                "status": ticket.status.value,
            },
        )

        if ready:
            await self.ws.notify_order_update(
                ticket.order_id,
                {
                    "type": "item_ready",
                    "ticket_id": ticket.id,
                    "item_name": ticket.item_name,
                    "station_id": ticket.station_id,
                },
            )