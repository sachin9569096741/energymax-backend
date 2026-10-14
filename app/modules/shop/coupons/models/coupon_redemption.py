from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    __table_args__ = (
        UniqueConstraint(
            "checkout_id",
            name="uq_coupon_redemptions_checkout",
        ),
        CheckConstraint(
            "status IN ('reserved', 'redeemed', 'released')",
            name="ck_coupon_redemptions_status",
        ),
        Index(
            "ix_coupon_redemptions_coupon_status",
            "coupon_id",
            "status",
        ),
        Index(
            "ix_coupon_redemptions_customer_status",
            "customer_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=False,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    checkout_id: Mapped[int] = mapped_column(
        ForeignKey("checkouts.id", ondelete="CASCADE"),
        nullable=False,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
    )

    # reserved = temporarily held
    # redeemed = successful order/payment
    # released = coupon no longer held
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="reserved",
    )

    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    reserved_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    coupon = relationship("Coupon")