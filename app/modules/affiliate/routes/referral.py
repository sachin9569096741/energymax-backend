
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
    )
)

    if affiliate is None:
        logger.warning(
            "Referral lookup: code not found; code=%s",
            public_code,
        )
        raise HTTPException(
            status_code=404,
            detail="Referral code not found in connected database.",
        )

    logger.info(
        "Referral lookup: id=%s status=%s activated=%s",
        affiliate.id,
        affiliate.status,
        affiliate.activated_at is not None,
    )

    if affiliate.status != "active" or affiliate.activated_at is None:
        raise HTTPException(
            status_code=404,
            detail="Referral link is invalid or inactive.",
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
