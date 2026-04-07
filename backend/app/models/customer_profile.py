from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CustomerProfile(TimestampMixin, Base):
    __tablename__ = "customer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    google_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(default=0, nullable=False)
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="customer_profile")
