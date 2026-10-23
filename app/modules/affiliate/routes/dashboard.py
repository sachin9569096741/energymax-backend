from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_referral_click import (
    AffiliateReferralClick,
)
from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from app.modules.affiliate.security.dependencies import (
    get_current_affiliate,
)
from app.modules.affiliate.services.commission_ledger_query_service import (
    CommissionLedgerQueryService,
)


router = APIRouter(
    prefix="/affiliates",
    tags=["Affiliate Dashboard"],
)


@router.get("/dashboard")
def get_affiliate_dashboard(
    current_affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    affiliate_id = current_affiliate.id

    # --------------------------------------------------------
    # TOTAL REFERRAL CLICKS
    # --------------------------------------------------------

    total_clicks = db.scalar(
        select(
            func.count(AffiliateReferralClick.id)
        ).where(
            AffiliateReferralClick.affiliate_id == affiliate_id
        )
    ) or 0

    # --------------------------------------------------------
    # TOTAL ATTRIBUTED ORDERS
    # --------------------------------------------------------

    total_attributed_orders = db.scalar(
        select(
            func.count(AffiliateAttribution.id)
        ).where(
            AffiliateAttribution.affiliate_id == affiliate_id
        )
    ) or 0

    # --------------------------------------------------------
    # CONVERSION RATE
    # --------------------------------------------------------

    conversion_rate = (
        round(
            total_attributed_orders / total_clicks * 100,
            2,
        )
        if total_clicks > 0
        else 0.0
    )

    # --------------------------------------------------------
    # AFFILIATE STATUS
    # --------------------------------------------------------

    is_activated = current_affiliate.activated_at is not None

    is_active = (
        current_affiliate.status == "active"
        and is_activated
    )

    # --------------------------------------------------------
    # COMMISSION SUMMARY
    # --------------------------------------------------------

    earnings = CommissionLedgerQueryService(
        db
    ).get_earnings_summary(current_affiliate)

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "affiliate": {
            "id": str(current_affiliate.id),
            "public_code": current_affiliate.public_code,
            "status": current_affiliate.status,
            "is_activated": is_activated,
            "can_earn": is_active,
        },
        "performance": {
            "total_clicks": total_clicks,
            "total_attributed_orders": total_attributed_orders,
            "click_to_order_rate_percent": conversion_rate,
        },
        "commissions": {
            "available": True,
            "earnings_by_currency": earnings,
        },
    }