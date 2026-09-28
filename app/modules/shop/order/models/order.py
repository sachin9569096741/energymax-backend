from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_public_id", "public_id"),
    )

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

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    checkout_id: Mapped[int] = mapped_column(
        ForeignKey("checkouts.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_payment",
        index=True,
    )

    # Customer snapshot
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    customer_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Immutable shipping-address snapshot
    shipping_address_snapshot: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    # Pricing snapshot
    subtotal: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    shipping_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    tax_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
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

    customer = relationship("Customer")
    checkout = relationship("Checkout")

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )