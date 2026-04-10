from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StockMovementType
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class StockMovement(TimestampMixin, Base):
    """
    Immutable ledger of every inventory change.

    Rules:
    - quantity > 0  →  stock coming IN  (purchase, return_in, adjustment +)
    - quantity < 0  →  stock going OUT  (sale, waste, adjustment -)
    - Current stock for an item = SUM(quantity) WHERE branch_id = X
    - Do NOT delete rows. Use an adjustment entry to correct mistakes.

    Auto-created by order.py service on close (sale movements, quantity negative).
    Manually created by stock.py service for purchases, returns, adjustments.
    """

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_item_variants.id"), nullable=True
    )

    # positive = in, negative = out; 3 decimal places for weight-based items
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(StockMovementType, name="stock_movement_type", values_callable=enum_values),
        nullable=False,
    )

    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # links back to originating record
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    menu_item = relationship("MenuItem")
    variant = relationship("MenuItemVariant")
    created_by = relationship("User", foreign_keys=[created_by_user_id])