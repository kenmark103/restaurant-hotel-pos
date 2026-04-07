from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Role, StaffStatus
from app.models.sqlalchemy_types import enum_values


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role", values_callable=enum_values), nullable=False)
    status: Mapped[StaffStatus] = mapped_column(
        Enum(StaffStatus, name="staff_status", values_callable=enum_values),
        default=StaffStatus.INVITED,
    )
    branch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="staff_profile", foreign_keys=[user_id])
