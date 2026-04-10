from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CashSessionStatus
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class CashSession(TimestampMixin, Base):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opening_float: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    closing_float: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[CashSessionStatus] = mapped_column(
        Enum(CashSessionStatus, name="cash_session_status", values_callable=enum_values),
        nullable=False,
        default=CashSessionStatus.OPEN,
    )

    branch = relationship("Branch")
    staff_user = relationship("User")
