from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    __table_args__ = (

        UniqueConstraint(
            "public_id",
            name="uq_wishlist_items_public_id",
        ),
        UniqueConstraint(
            "customer_id",
            "product_id",
            name="uq_wishlist_customer_product",
        ),
        Index(
            "ix_wishlist_customer_created",
            "customer_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    public_id: Mapped[str] = mapped_column(
        # UUID stored as a string, consistent with your other models.
        __import__("sqlalchemy").String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    customer = relationship("Customer")
    product = relationship("Product")