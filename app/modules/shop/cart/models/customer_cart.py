from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerCart(Base):
    __tablename__ = "customer_carts"

    __table_args__ = (
        Index(
            "ix_customer_carts_customer_id",
            "customer_id",
        ),
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
    # Customer relationship
    # ---------------------------------------------------------------

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    # ---------------------------------------------------------------
    # Audit
    # ---------------------------------------------------------------

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

    customer = relationship(
        "Customer",
    )

    items = relationship(
        "CustomerCartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )