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
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.modules.affiliate.models.affiliate_kyc_submission import (
        AffiliateKYCSubmission,
    )
from app.modules.admin.auth.models.admin_user import AdminUser
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AffiliateKYCReviewHistory(Base):
    __tablename__ = "affiliate_kyc_review_history"

    __table_args__ = (
        CheckConstraint(
            "action IN ("
            "'CLAIMED', "
            "'APPROVED', "
            "'REJECTED', "
            "'RESUBMISSION_REQUESTED', "
            "'REASSIGNED', "
            "'SUBMITTED' "
            "'RESUBMITTED' "
            ")",
            name="ck_affiliate_kyc_review_action",
        ),
        CheckConstraint(
            "new_status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_review_new_status",
        ),
        CheckConstraint(
            "previous_status IS NULL OR previous_status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_review_previous_status",
        ),
        Index(
            "ix_affiliate_kyc_history_submission_created",
            "submission_id",
            "created_at",
        ),
        Index(
            "ix_affiliate_kyc_history_reviewer_created",
            "reviewer_id",
            "created_at",
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

    # Nullable so the audit record can survive reviewer deletion.
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # CLAIMED, APPROVED, REJECTED,
    # RESUBMISSION_REQUESTED, REASSIGNED
    action: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    submission: Mapped["AffiliateKYCSubmission"] = relationship(
        "AffiliateKYCSubmission",
        back_populates="review_history",
    )

    reviewer: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[reviewer_id],
    )