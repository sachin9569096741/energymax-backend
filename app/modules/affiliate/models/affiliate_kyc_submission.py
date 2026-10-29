from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AffiliateKYCSubmission(Base):
    __tablename__ = "affiliate_kyc_submissions"

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_submission_status",
        ),
        Index(
            "ix_affiliate_kyc_submission_queue",
            "status",
            "submitted_at",
        ),
        Index(
            "ix_affiliate_kyc_submission_affiliate_created",
            "affiliate_id",
            "created_at",
        ),
        Index(
            "ix_affiliate_kyc_submission_reviewer_status",
            "assigned_reviewer_id",
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
        index=True,
    )

    affiliate_id: Mapped[int] = mapped_column(
        ForeignKey("affiliates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # A submission is created only when documents are submitted.
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING_REVIEW",
        index=True,
    )

    assigned_reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    affiliate: Mapped["Affiliate"] = relationship(
        "Affiliate",
        foreign_keys=[affiliate_id],
    )

    assigned_reviewer: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[assigned_reviewer_id],
    )

    documents: Mapped[list["AffiliateKYCDocument"]] = relationship(
        "AffiliateKYCDocument",
        back_populates="submission",
        cascade="save-update, merge",
        passive_deletes=True,
        order_by="AffiliateKYCDocument.document_type",
    )

    review_history: Mapped[list["AffiliateKYCReviewHistory"]] = relationship(
        "AffiliateKYCReviewHistory",
        back_populates="submission",
        cascade="save-update, merge",
        passive_deletes=True,
        order_by="AffiliateKYCReviewHistory.created_at",
    )