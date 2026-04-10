from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OrderType, PaymentMethod, PosOrderStatus
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class PosOrder(TimestampMixin, Base):
    __tablename__ = "pos_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"), nullable=True)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type", values_callable=enum_values),
        default=OrderType.DINE_IN,
        nullable=False,
    )
    status: Mapped[PosOrderStatus] = mapped_column(
        Enum(PosOrderStatus, name="pos_order_status", values_callable=enum_values),
        default=PosOrderStatus.OPEN,
        nullable=False,
    )
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=enum_values),
        nullable=True,
    )
    amount_paid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    branch = relationship("Branch")
    table = relationship("Table")
    staff_user = relationship("User")
    items = relationship("PosOrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("PosPayment", back_populates="order", cascade="all, delete-orphan")
    discounts = relationship("OrderDiscount", back_populates="order", cascade="all, delete-orphan")
