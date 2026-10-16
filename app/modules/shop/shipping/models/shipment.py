
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Shipment(Base):
    __tablename__ = "shipments"

    __table_args__ = (
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    shiprocket_order_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    shiprocket_shipment_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    awb_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    courier_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    tracking_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    length_cm: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    breadth_cm: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    height_cm: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    weight_kg: Mapped[float] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    pickup_token_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    pickup_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    label_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    manifest_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    awb_operation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="idle"
    )
    pickup_operation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="idle"
    )
    label_operation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="idle"
    )
    manifest_operation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="idle"
    )

    order = relationship("Order")

