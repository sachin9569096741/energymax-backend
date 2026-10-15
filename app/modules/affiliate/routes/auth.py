from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.schemas.auth import (
    AffiliateActivateRequest,
    AffiliateLoginRequest,
    AffiliateMeResponse,
    AffiliateMessageResponse,
    AffiliateSessionResponse,
)
from app.modules.affiliate.security.captcha import verify_captcha
from app.modules.affiliate.security.dependencies import (
    get_current_affiliate,
)
from app.modules.affiliate.services.auth_service import (
    AffiliateAuthService,
)

router = APIRouter(
    prefix="/affiliates/auth",
    tags=["Affiliate - Authentication"],
)


@router.post("/activate", response_model=AffiliateMessageResponse)
def activate_affiliate(
    payload: AffiliateActivateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    verify_captcha(
        payload.captcha_token,
        request.client.host if request.client else None,
    )

    try:
        AffiliateAuthService(db).activate(
            payload.token,
            payload.new_password,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AffiliateMessageResponse(
        message="Affiliate account activated. You can now log in."
    )


@router.post("/login", response_model=AffiliateSessionResponse)
def login_affiliate(
    payload: AffiliateLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    verify_captcha(
        payload.captcha_token,
        request.client.host if request.client else None,
    )

    try:
        affiliate, token, expires_at = AffiliateAuthService(db).login(
            str(payload.email),
            payload.password,
        )

        db.commit()
        db.refresh(affiliate)

        return AffiliateSessionResponse(
            access_token=token,
            expires_at=expires_at,
            affiliate=AffiliateMeResponse.model_validate(affiliate),
        )

    except Exception:
        db.rollback()
        raise


@router.post("/logout", response_model=AffiliateMessageResponse)
def logout_affiliate(
    request: Request,
    current_affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    # Extract the Bearer token for session revocation.
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Affiliate authentication required.",
        )

    try:
        AffiliateAuthService(db).logout(token.strip())
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AffiliateMessageResponse(
        message="Affiliate logged out successfully."
    )


@router.get("/me", response_model=AffiliateMeResponse)
def get_my_affiliate_profile(
    affiliate: Affiliate = Depends(get_current_affiliate),
):
    return AffiliateMeResponse.model_validate(affiliate)