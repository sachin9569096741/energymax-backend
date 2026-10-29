from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AffiliateKYCDocument(Base):
    __tablename__ = "affiliate_kyc_documents"

    __table_args__ = (
        CheckConstraint(
            "document_type IN ("
            "'AADHAAR_FRONT', "
            "'AADHAAR_BACK', "
            "'PAN_CARD'"
            ")",
            name="ck_affiliate_kyc_document_type",
        ),
        CheckConstraint(
            "file_size_bytes > 0",
            name="ck_affiliate_kyc_document_positive_size",
        ),
        UniqueConstraint(
            "submission_id",
            "document_type",
            name="uq_affiliate_kyc_submission_document_type",
        ),
        Index(
            "ix_affiliate_kyc_document_submission_type",
            "submission_id",
            "document_type",
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

    submission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "affiliate_kyc_submissions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # Allowed values:
    # AADHAAR_FRONT, AADHAAR_BACK, PAN_CARD
    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Private storage identifier, never a public URL.
    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    sha256_checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    submission: Mapped["AffiliateKYCSubmission"] = relationship(
        "AffiliateKYCSubmission",
        back_populates="documents",
    )