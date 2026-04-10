from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DiscountType
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class OrderDiscount(TimestampMixin, Base):
    """
    Discount applied at order level or to a specific line item.

    order_item_id = None  →  order-level discount (applied to total)
    order_item_id = X     →  line-level discount (applied to that line only)

    `amount` is the computed KES value of the discount and is stored for audit.
    Recalculated by the order service whenever totals are recomputed.
    """

    __tablename__ = "order_discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pos_orders.id", ondelete="CASCADE"), nullable=False
    )
    order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("pos_order_items.id", ondelete="CASCADE"), nullable=True
    )

    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type", values_callable=enum_values),
        nullable=False,
    )
    # For percent: 10.00 means 10%. For fixed: 50.00 means KES 50 off.
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Computed discount in money terms, stored for Z-report and audit
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authorized_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    order = relationship("PosOrder", back_populates="discounts")
    order_item = relationship("PosOrderItem")
    authorized_by = relationship("User", foreign_keys=[authorized_by_user_id])