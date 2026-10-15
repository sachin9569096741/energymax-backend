
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin

from app.modules.affiliate.schemas.application import (
    AffiliateApplicationAdminResponse,
    AffiliateApplicationDecision,
    AffiliateResponse,
)
from app.modules.affiliate.services.application_service import (
    AffiliateApplicationService,
)
from app.modules.affiliate.services.auth_service import (
    AffiliateAuthService,
)


router = APIRouter(
    prefix="/admin/affiliate-applications",
    tags=["Admin - Affiliates"],
)


@router.get(
    "",
    response_model=list[AffiliateApplicationAdminResponse],
)
def list_affiliate_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AffiliateApplicationService(db).list_applications(
        status_filter,
        limit,
        offset,
    )


@router.post(
    "/{public_id}/approve",
    response_model=AffiliateResponse,
    status_code=status.HTTP_201_CREATED,
)
def approve_affiliate_application(
    public_id: str,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    application_service = AffiliateApplicationService(db)
    auth_service = AffiliateAuthService(db)

    try:
        # Approve the application and create the affiliate.
        affiliate = application_service.approve(
            public_id,
            admin.id,
        )

        # Generate a single-use activation token.
        raw_token = auth_service.issue_activation_token(affiliate)

        # Persist approval and token before attempting email delivery.
        db.commit()
        db.refresh(affiliate)

    except Exception:
        db.rollback()
        raise

    # Send email only after the transaction has committed.
    # If delivery fails, the approved affiliate remains in the database.
    auth_service.send_activation_email(
        affiliate,
        raw_token,
    )

    return affiliate


@router.post(
    "/{public_id}/reject",
    response_model=AffiliateApplicationAdminResponse,
)
def reject_affiliate_application(
    public_id: str,
    payload: AffiliateApplicationDecision,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = AffiliateApplicationService(db)

    try:
        application = service.reject(
            public_id,
            admin.id,
            payload.decision_reason,
        )

        db.commit()
        db.refresh(application)

        return application

    except Exception:
        db.rollback()
        raise


affiliates_router = APIRouter(
    prefix="/admin/affiliates",
    tags=["Admin - Affiliates"],
)


@affiliates_router.get(
    "",
    response_model=list[AffiliateResponse],
)
def list_affiliates(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AffiliateApplicationService(db).list_affiliates(
        status_filter,
        limit,
        offset,
    )
