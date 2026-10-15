from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AffiliateSession(Base):
    __tablename__ = "affiliate_sessions"

    __table_args__ = (
        Index(
            "ix_affiliate_sessions_affiliate_active",
            "affiliate_id", "is_active"
        ),
        Index("ix_affiliate_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False,
        default=lambda: str(uuid4())
    )
    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    affiliate = relationship(
        "Affiliate", back_populates="sessions"
    )