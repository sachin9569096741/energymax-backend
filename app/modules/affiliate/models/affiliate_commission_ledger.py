from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

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


class AffiliateCommissionLedger(Base):
    __tablename__ = "affiliate_commission_ledger"

    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('COMMISSION', 'REVERSAL', 'ADJUSTMENT')",
            name="ck_affiliate_commission_ledger_entry_type",
        ),
        CheckConstraint(
            "amount <> 0",
            name="ck_affiliate_commission_ledger_amount_nonzero",
        ),
        CheckConstraint(
            "base_amount >= 0",
            name="ck_affiliate_commission_ledger_base_nonnegative",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_affiliate_commission_ledger_idempotency_key",
        ),
        Index(
            "ix_affiliate_commission_ledger_affiliate_created",
            "affiliate_id",
            "created_at",
        ),
        Index(
            "ix_affiliate_commission_ledger_order",
            "order_id",
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
        index=True,
    )

    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="RESTRICT"),
        nullable=False,
    )

    attribution_id: Mapped[int] = mapped_column(
        ForeignKey("affiliate_attributions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # COMMISSION, REVERSAL, or ADJUSTMENT.
    entry_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Positive for earned commission; negative for reversal entries.
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    # Snapshots make the calculation auditable.
    base_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),
        nullable=False,
    )

    # Stable key supplied by the trusted server-side caller.
    idempotency_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # Reference to the commission being reversed, if applicable.
    reverses_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "affiliate_commission_ledger.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    affiliate = relationship("Affiliate")
    attribution = relationship("AffiliateAttribution")
    order = relationship("Order")

    reverses_entry = relationship(
        "AffiliateCommissionLedger",
        remote_side="AffiliateCommissionLedger.id",
        foreign_keys=[reverses_entry_id],
    )