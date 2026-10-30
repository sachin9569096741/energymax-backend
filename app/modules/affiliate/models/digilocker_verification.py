from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DigiLockerVerification(Base):
    __tablename__ = "affiliate_digilocker_verifications"

    __table_args__ = (
        UniqueConstraint(
            "verification_id",
            name="uq_affiliate_digilocker_verification_id",
        ),
        Index(
            "ix_digilocker_affiliate_status",
            "affiliate_id",
            "status",
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

    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    verification_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    provider_reference_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="initiated",
        index=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="AADHAAR",
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