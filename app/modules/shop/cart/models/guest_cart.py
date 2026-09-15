from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GuestCart(Base):
    __tablename__ = "guest_carts"

    __table_args__ = (
        Index("ix_guest_carts_token_hash", "token_hash"),
        Index("ix_guest_carts_expires_at", "expires_at"),
    )

    # ---------------------------------------------------------------
    # Identity
    # ---------------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    # ---------------------------------------------------------------
    # Guest authentication
    # ---------------------------------------------------------------

    token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------

    items = relationship(
        "GuestCartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )