
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.modules.affiliate.models.affiliate_kyc_submission import (
    AffiliateKYCSubmission,
)


def get_affiliate_kyc_status(
    db: Session,
    affiliate_id: int,
) -> str:
    """
    Return the status of the affiliate's latest KYC submission.

    A previous verified submission must not override a newer
    pending, rejected, or resubmitted application.
    """
    submission = db.scalar(
        select(AffiliateKYCSubmission)
        .where(
            AffiliateKYCSubmission.affiliate_id == affiliate_id
        )
        .order_by(
            AffiliateKYCSubmission.created_at.desc(),
            AffiliateKYCSubmission.id.desc(),
        )
        .limit(1)
    )

    if submission is None:
        return "NOT_STARTED"

    return str(submission.status).upper()


def require_verified_kyc(
    db: Session,
    affiliate_id: int,
) -> None:
    """
    Block a restricted operation unless the latest KYC is verified.
    """
    current_status = get_affiliate_kyc_status(
        db=db,
        affiliate_id=affiliate_id,
    )

    if current_status != "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "KYC_NOT_VERIFIED",
                "message": (
                    "Complete and verify your KYC before "
                    "requesting or processing a withdrawal."
                ),
                "kyc_status": current_status,
            },
        )
