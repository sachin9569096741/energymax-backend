
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AffiliateAttribution(Base):
    __tablename__ = "affiliate_attributions"

    __table_args__ = (
        CheckConstraint(
            "source IN ('CLICK', 'COUPON')",
            name="ck_affiliate_attributions_source",
        ),
        Index(
            "ix_affiliate_attributions_affiliate_attributed",
            "affiliate_id",
            "attributed_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # One final attribution record per order.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Present when attribution came from a referral click.
    click_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "affiliate_referral_clicks.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    # The coupon used on the order, if any.
    coupon_id: Mapped[int | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # True when the order's coupon belongs to a different affiliate
    # from the affiliate selected by the eligible last click.
    coupon_conflict: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    attributed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Snapshot of the policy applied when this record was created.
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="last_click_coupon_fallback_v1",
    )

    order = relationship("Order")
    affiliate = relationship("Affiliate")
    click = relationship("AffiliateReferralClick")
    coupon = relationship("Coupon")
