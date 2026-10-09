from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GuestCartItem(Base):
    __tablename__ = "guest_cart_items"

    __table_args__ = (
        UniqueConstraint(
            "cart_id",
            "product_id",
            "variant_id",
            name="uq_guest_cart_product",
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
    # Relationships
    # ---------------------------------------------------------------

    cart_id: Mapped[int] = mapped_column(
        ForeignKey(
            "guest_carts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------------
    # Cart data
    # ---------------------------------------------------------------

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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

    variant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------

    cart = relationship(
        "GuestCart",
        back_populates="items",
    )

    product = relationship(
        "Product",
    )
    variant = relationship("ProductVariant")