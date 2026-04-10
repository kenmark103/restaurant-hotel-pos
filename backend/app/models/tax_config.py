from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TaxConfig(TimestampMixin, Base):
    __tablename__ = "tax_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="VAT")
    rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0.1600"))
    is_inclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    branch = relationship("Branch")
