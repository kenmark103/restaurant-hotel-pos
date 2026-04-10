from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import KitchenStation
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)

    # ── identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    # ── pricing ───────────────────────────────────────────────────────────────
    # base_price = default sell price when no variant is selected
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # cost_price = purchase/recipe cost for COGS reporting
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # ── units & inventory ─────────────────────────────────────────────────────
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False, default="piece")
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_stock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── kitchen ───────────────────────────────────────────────────────────────
    prep_time_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    station: Mapped[KitchenStation] = mapped_column(
        Enum(KitchenStation, name="kitchen_station", values_callable=enum_values),
        default=KitchenStation.ANY,
        nullable=False,
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── relationships ─────────────────────────────────────────────────────────
    category = relationship("MenuCategory", back_populates="items")
    variants = relationship(
        "MenuItemVariant",
        back_populates="menu_item",
        cascade="all, delete-orphan",
        order_by="MenuItemVariant.display_order, MenuItemVariant.name",
    )
    modifier_groups = relationship(
        "MenuModifierGroup",
        back_populates="menu_item",
        cascade="all, delete-orphan",
    )