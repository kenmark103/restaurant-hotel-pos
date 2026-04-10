import secrets

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TableStatus
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class Table(TimestampMixin, Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), nullable=False)
    table_number: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[TableStatus] = mapped_column(
        Enum(TableStatus, name="table_status", values_callable=enum_values),
        default=TableStatus.AVAILABLE,
        nullable=False,
    )
    qr_code_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(32),
    )

    branch = relationship("Branch", back_populates="tables")
