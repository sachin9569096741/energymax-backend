
import hashlib
import hmac
from urllib.parse import urlencode
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_referral_click import (
    AffiliateReferralClick,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/affiliates/r",
    tags=["Affiliate - Referrals"],
)


def _visitor_hash(request: Request) -> str | None:
    """
    Create a keyed hash of the client IP without storing the raw IP.
    Uses the configured application secret as the HMAC key.
    """
    client_ip = request.client.host if request.client else None

    if not client_ip:
        return None

    digest = hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        client_ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return digest


@router.get("/{public_code}", name="affiliate_referral_redirect")
def track_affiliate_referral(
    public_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Record an eligible affiliate referral click and redirect
    the visitor to the storefront with the referral code.
    """
    affiliate = db.scalar(
        select(Affiliate).where(
            Affiliate.public_code == public_code,
            Affiliate.status == "active",
            Affiliate.activated_at.is_not(None),
        )
    )

    if affiliate is None:
        raise HTTPException(
            status_code=404,
            detail="Referral link is invalid or inactive.",
        )

    click = AffiliateReferralClick(
        affiliate_id=affiliate.id,
        visitor_hash=_visitor_hash(request),
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
    )

    try:
        db.add(click)
        db.flush()
    except Exception:
        logger.exception("Failed to record affiliate referral click")
        raise HTTPException(
            status_code=503,
            detail="Referral service is temporarily unavailable.",
        )

    # Preserve any existing storefront query parameters.
    destination = settings.frontend_base_url.rstrip("/") + "/"
    query_params = dict(request.query_params)
    query_params["ref"] = affiliate.public_code

    return RedirectResponse(
        url=f"{destination}?{urlencode(query_params)}",
        status_code=302,
    )
