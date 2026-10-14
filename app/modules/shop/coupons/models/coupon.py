from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    __table_args__ = (
        CheckConstraint(
            "discount_percent IN (5, 10)",
            name="ck_coupons_discount_percent",
        ),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions > 0",
            name="ck_coupons_max_redemptions_positive",
        ),
        CheckConstraint(
            "max_redemptions_per_customer IS NULL "
            "OR max_redemptions_per_customer > 0",
            name="ck_coupons_customer_limit_positive",
        ),
        CheckConstraint(
            "minimum_subtotal IS NULL OR minimum_subtotal >= 0",
            name="ck_coupons_minimum_subtotal_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    discount_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    minimum_subtotal: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    max_redemptions: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    max_redemptions_per_customer: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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