from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AuthProvider, UserType
from app.models.mixins import TimestampMixin
from app.models.sqlalchemy_types import enum_values


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType, name="user_type", values_callable=enum_values))
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, name="auth_provider", values_callable=enum_values)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False, foreign_keys="StaffProfile.user_id")
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False)
