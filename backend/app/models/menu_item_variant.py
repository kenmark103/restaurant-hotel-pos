from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class MenuItemVariant(TimestampMixin, Base):
    """
    Size / portion variants for a menu item.
    Example: Margherita Pizza → Large (KES 1200), Medium (KES 900), Small (KES 650)

    When variants exist the POS must present a selection before adding to ticket.
    The variant sell_price overrides menu_item.base_price for that line item.
    """

    __tablename__ = "menu_item_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)      # "Large"
    sell_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # optional per-variant barcode / SKU for barcode scanning at POS
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    menu_item = relationship("MenuItem", back_populates="variants")