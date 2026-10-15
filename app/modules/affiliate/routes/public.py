
from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.schemas.application import (
    AffiliateApplicationCreate,
    AffiliateApplicationPublicResponse,
)
from app.modules.affiliate.services.application_service import (
    AffiliateApplicationService,
)

router = APIRouter(
    prefix="/affiliates",
    tags=["Affiliate - Applications"],
)


@router.post(
    "/applications",
    response_model=AffiliateApplicationPublicResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_affiliate_application(
    payload: AffiliateApplicationCreate,
    db: Session = Depends(get_db),
):
    try:
        application = AffiliateApplicationService(db).submit(payload)

        db.commit()
        db.refresh(application)

        return AffiliateApplicationPublicResponse(
            public_id=application.public_id,
            status=application.status,
            submitted_at=application.submitted_at,
        )

    except Exception:
        db.rollback()
        raise