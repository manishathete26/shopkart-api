from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
