
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AffiliateReferralClick(Base):
    __tablename__ = "affiliate_referral_clicks"

    __table_args__ = (
        Index(
            "ix_affiliate_referral_clicks_affiliate_id_clicked_at",
            "affiliate_id",
            "clicked_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Store a hash, not the visitor's raw IP address.
    visitor_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    referrer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    affiliate = relationship("Affiliate")
