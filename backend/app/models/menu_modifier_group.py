from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class MenuModifierGroup(TimestampMixin, Base):
    __tablename__ = "menu_modifier_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_selections: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    menu_item = relationship("MenuItem", back_populates="modifier_groups")
    options = relationship("MenuModifierOption", back_populates="group", cascade="all, delete-orphan")
