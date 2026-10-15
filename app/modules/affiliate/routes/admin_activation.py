
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import (
    require_super_admin,
)
from app.modules.affiliate.repositories.auth_repo import (
    AffiliateAuthRepository,
)
from app.modules.affiliate.schemas.auth import (
    AffiliateMessageResponse,
)
from app.modules.affiliate.services.auth_service import (
    AffiliateAuthService,
)


router = APIRouter(
    prefix="/admin/affiliates",
    tags=["Admin - Affiliate Activation"],
)


@router.post(
    "/{public_id}/send-activation",
    response_model=AffiliateMessageResponse,
)
def send_affiliate_activation(
    public_id: str,
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    auth_service = AffiliateAuthService(db)
    repository = AffiliateAuthRepository(db)

    affiliate = repository.get_by_public_id(public_id)

    if affiliate is None:
        raise HTTPException(
            status_code=404,
            detail="Affiliate not found.",
        )

    if affiliate.status != "active":
        raise HTTPException(
            status_code=403,
            detail="Affiliate account is not active.",
        )

    if affiliate.password_hash:
        raise HTTPException(
            status_code=409,
            detail="Affiliate account is already activated.",
        )

    try:
        raw_token = auth_service.issue_activation_token(affiliate)

        # Save the token before sending the email.
        db.commit()
        db.refresh(affiliate)

    except Exception:
        db.rollback()
        raise

    # Send the email after committing the database transaction.
    auth_service.send_activation_email(
        affiliate,
        raw_token,
    )

    return AffiliateMessageResponse(
        message="Activation email sent."
    )
