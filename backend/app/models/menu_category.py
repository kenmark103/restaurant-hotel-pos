from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class MenuCategory(TimestampMixin, Base):
    __tablename__ = "menu_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    available_from: Mapped[str | None] = mapped_column(String(5), nullable=True)   # "06:00"
    available_until: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "11:00"

    branch = relationship("Branch", back_populates="menu_categories")
    parent = relationship("MenuCategory", remote_side="MenuCategory.id", back_populates="children")
    children = relationship(
        "MenuCategory",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="MenuCategory.display_order, MenuCategory.name",
    )
    items = relationship(
        "MenuItem",
        back_populates="category",
        order_by="MenuItem.name",
    )