from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PosOrderItemModifier(TimestampMixin, Base):
    __tablename__ = "pos_order_item_modifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("pos_order_items.id", ondelete="CASCADE"), nullable=False)
    option_id: Mapped[int | None] = mapped_column(ForeignKey("menu_modifier_options.id"), nullable=True)
    option_name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    order_item = relationship("PosOrderItem", back_populates="modifiers")
    option = relationship("MenuModifierOption")
