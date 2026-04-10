from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PosOrderItem(TimestampMixin, Base):
    __tablename__ = "pos_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("pos_orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("menu_item_variants.id"), nullable=True)
    menu_item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_voided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order = relationship("PosOrder", back_populates="items")
    menu_item = relationship("MenuItem")
    variant = relationship("MenuItemVariant")
    modifiers = relationship("PosOrderItemModifier", back_populates="order_item", cascade="all, delete-orphan")
