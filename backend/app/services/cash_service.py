"""
cash_service.py — Cash session & transaction management
─────────────────────────────────────────────────────────────────────────────
Extracted from pos_service.py.

Covers:
  • Open / close shift (one session per branch at a time)
  • Paid-outs and safe drops
  • Full reconciliation on close (cash sales vs float)
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select

from app.db.models import (
    AuditAction,
    AuditLog,
    CashSession,
    CashSessionStatus,
    CashTransaction,
    PaymentMethod,
    PosOrder,
    PosOrderStatus,
)
from app.services.base import BaseService, NotFoundError, ValidationError, to_money


class CashService(BaseService[CashSession]):
    model = CashSession

    # ─────────────────────────────────────────────────────────────────────────
    # Session lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    async def get_current_session(self, branch_id: int) -> Optional[CashSession]:
        return await self.db.scalar(
            select(CashSession).where(
                CashSession.branch_id == branch_id,
                CashSession.status == CashSessionStatus.OPEN,
            )
        )

    async def open_session(
        self,
        branch_id: int,
        staff_user_id: int,
        opening_float: Decimal,
    ) -> CashSession:
        """
        Open the till for a shift.
        Enforces one open session per branch — prevents accidental double-opens.
        """
        existing = await self.get_current_session(branch_id)
        if existing:
            raise ValidationError(
                f"A cash session is already open (session #{existing.id}). "
                "Close it before opening a new one."
            )

        session = CashSession(
            branch_id=branch_id,
            staff_user_id=staff_user_id,
            opening_float=to_money(opening_float),
            status=CashSessionStatus.OPEN,
            opened_at=datetime.now(UTC),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def close_session(
        self,
        session_id: int,
        closing_float: Decimal,
        closure_notes: Optional[str] = None,
    ) -> CashSession:
        """
        Close a session with full reconciliation:
          expected = opening_float + cash_sales - paid_outs - safe_drops
          discrepancy = closing_float - expected
        """
        session = await self.db.get(CashSession, session_id)
        if not session or session.status != CashSessionStatus.OPEN:
            raise NotFoundError("Open cash session")

        # ── Aggregate sales in this session window ────────────────────────
        sales_result = await self.db.execute(
            select(PosOrder).where(
                PosOrder.branch_id == session.branch_id,
                PosOrder.status == PosOrderStatus.CLOSED,
                PosOrder.closed_at >= session.opened_at,
            )
        )
        orders = sales_result.scalars().all()

        def _sum_method(method: PaymentMethod) -> Decimal:
            return to_money(
                sum(p.amount for o in orders for p in o.payments if p.method == method)
                if orders else Decimal("0")
            )

        cash_sales = _sum_method(PaymentMethod.CASH)
        card_sales = _sum_method(PaymentMethod.CARD)
        mobile_sales = _sum_method(PaymentMethod.MOBILE_MONEY)

        # ── Paid-outs / safe drops reduce the expected float ──────────────
        paid_out_total = await self.db.scalar(
            select(
                func.coalesce(func.sum(CashTransaction.amount), 0)
            ).where(
                CashTransaction.session_id == session_id,
                CashTransaction.transaction_type.in_(["paid_out", "safe_drop"]),
            )
        ) or Decimal("0")

        expected_closing = to_money(
            session.opening_float + cash_sales - Decimal(str(paid_out_total))
        )
        discrepancy = to_money(to_money(closing_float) - expected_closing)

        session.closing_float = to_money(closing_float)
        session.expected_closing = expected_closing
        session.discrepancy = discrepancy
        session.total_cash_sales = cash_sales
        session.total_card_sales = card_sales
        session.total_mobile_sales = mobile_sales
        session.closure_notes = closure_notes
        session.status = CashSessionStatus.CLOSED
        session.closed_at = datetime.now(UTC)

        if self.user:
            self.db.add(
                AuditLog(
                    branch_id=session.branch_id,
                    actor_id=self.user.id,
                    action=AuditAction.CASH_SESSION_CLOSED,
                    entity_type="cash_session",
                    entity_id=session_id,
                    payload={
                        "expected": str(expected_closing),
                        "actual": str(closing_float),
                        "discrepancy": str(discrepancy),
                    },
                )
            )

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ─────────────────────────────────────────────────────────────────────────
    # In-session transactions
    # ─────────────────────────────────────────────────────────────────────────

    async def record_transaction(
        self,
        session_id: int,
        transaction_type: str,   # paid_out | safe_drop
        amount: Decimal,
        reason: str,
        authorized_by_id: int,
    ) -> CashTransaction:
        """Record a petty cash outgoing or safe drop against an open session."""
        session = await self.db.get(CashSession, session_id)
        if not session or session.status != CashSessionStatus.OPEN:
            raise NotFoundError("Open cash session")
        if amount <= 0:
            raise ValidationError("Amount must be positive")
        if transaction_type not in ("paid_out", "safe_drop"):
            raise ValidationError("transaction_type must be 'paid_out' or 'safe_drop'")

        action = (
            AuditAction.PAID_OUT
            if transaction_type == "paid_out"
            else AuditAction.SAFE_DROP
        )

        tx = CashTransaction(
            session_id=session_id,
            transaction_type=transaction_type,
            amount=to_money(amount),
            reason=reason,
            authorized_by_id=authorized_by_id,
        )
        self.db.add(tx)

        self.db.add(
            AuditLog(
                branch_id=session.branch_id,
                actor_id=self.user.id if self.user else authorized_by_id,
                approved_by_id=authorized_by_id,
                action=action,
                entity_type="cash_session",
                entity_id=session_id,
                payload={"amount": str(amount), "reason": reason},
            )
        )

        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def get_session_transactions(self, session_id: int) -> List[CashTransaction]:
        result = await self.db.execute(
            select(CashTransaction)
            .where(CashTransaction.session_id == session_id)
            .order_by(CashTransaction.created_at)
        )
        return list(result.scalars().all())

    async def get_sessions(
        self,
        branch_id: int,
        limit: int = 30,
    ) -> List[CashSession]:
        result = await self.db.execute(
            select(CashSession)
            .where(CashSession.branch_id == branch_id)
            .order_by(CashSession.opened_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())