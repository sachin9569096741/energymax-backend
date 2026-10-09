from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.shop.catalog.models.product import Product


class ProductVariant(Base):
    __tablename__ = "product_variants"

    __table_args__ = (
        Index(
            "ix_product_variants_product_active",
            "product_id",
            "is_active",
        ),
       
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Product relationship
    # ------------------------------------------------------------------

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Variant identity
    # ------------------------------------------------------------------

    flavour: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Pricing
    # ------------------------------------------------------------------

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    mrp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    cost_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Storefront
    # ------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="variants",
    )



    inventory_balances = relationship(
        "InventoryBalance",
        back_populates="variant",
    )

    inventory_movements = relationship(
        "InventoryMovement",
        back_populates="variant",
    )

    inventory_reservations = relationship(
        "InventoryReservation",
        back_populates="variant",
    )

    stock_adjustments = relationship(
        "StockAdjustment",
        back_populates="variant",
    )