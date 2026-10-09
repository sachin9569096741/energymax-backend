from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.shop.inventory.constants.enums import (
    InventoryReservationStatus,
)


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey(
            "warehouses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------
    # RESERVATION
    # ---------------------------------------------------------

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )

    status: Mapped[InventoryReservationStatus] = mapped_column(
        String(30),
        nullable=False,
        default=InventoryReservationStatus.ACTIVE,
        index=True,
    )

    # ---------------------------------------------------------
    # REFERENCE
    # ---------------------------------------------------------

    reference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reference_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

        # ---------------------------------------------------------
    # IDEMPOTENCY
    # ---------------------------------------------------------

    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    # ---------------------------------------------------------
    # EXPIRY
    # ---------------------------------------------------------

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------
    # AUDIT
    # ---------------------------------------------------------

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

    warehouse = relationship(
        "Warehouse",
        back_populates="inventory_reservations",
    )

    variant = relationship(
        "ProductVariant",
        back_populates="inventory_reservations",
    )