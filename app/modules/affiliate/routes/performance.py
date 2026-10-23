from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.modules.affiliate.security.dependencies import get_current_affiliate

router = APIRouter(
    prefix="/affiliates",
    tags=["Affiliate Performance"],
)


@router.get("/performance")
def get_affiliate_performance(
    start_date: date = Query(..., description="Start date, inclusive"),
    end_date: date = Query(..., description="End date, inclusive"),
    current_affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be on or after start_date.",
        )

    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=400,
            detail="Date range cannot exceed 366 calendar days.",
        )

    # Use UTC boundaries and a half-open interval [start, end).
    start_dt = datetime.combine(
        start_date, time.min, tzinfo=timezone.utc
    )
    end_dt = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    affiliate_id = current_affiliate.id

    # Aggregate clicks by UTC calendar date.
    click_rows = db.execute(
        select(
            func.date(AffiliateReferralClick.clicked_at).label("day"),
            func.count(AffiliateReferralClick.id).label("total"),
        )
        .where(
            AffiliateReferralClick.affiliate_id == affiliate_id,
            AffiliateReferralClick.clicked_at >= start_dt,
            AffiliateReferralClick.clicked_at < end_dt,
        )
        .group_by(func.date(AffiliateReferralClick.clicked_at))
        .order_by(func.date(AffiliateReferralClick.clicked_at))
    ).all()

    # Aggregate final attributed orders by UTC calendar date.
    order_rows = db.execute(
        select(
            func.date(AffiliateAttribution.attributed_at).label("day"),
            func.count(AffiliateAttribution.id).label("total"),
        )
        .where(
            AffiliateAttribution.affiliate_id == affiliate_id,
            AffiliateAttribution.attributed_at >= start_dt,
            AffiliateAttribution.attributed_at < end_dt,
        )
        .group_by(func.date(AffiliateAttribution.attributed_at))
        .order_by(func.date(AffiliateAttribution.attributed_at))
    ).all()

    clicks_by_day = {
        str(row.day): int(row.total)
        for row in click_rows
    }
    orders_by_day = {
        str(row.day): int(row.total)
        for row in order_rows
    }

    daily = []
    cursor = start_date

    while cursor <= end_date:
        day_key = cursor.isoformat()
        clicks = clicks_by_day.get(day_key, 0)
        orders = orders_by_day.get(day_key, 0)

        daily.append({
            "date": day_key,
            "clicks": clicks,
            "attributed_orders": orders,
            "click_to_order_rate_percent": (
                round(orders / clicks * 100, 2)
                if clicks
                else 0.0
            ),
        })

        cursor += timedelta(days=1)

    total_clicks = sum(clicks_by_day.values())
    total_orders = sum(orders_by_day.values())

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
        },
        "summary": {
            "total_clicks": total_clicks,
            "total_attributed_orders": total_orders,
            "click_to_order_rate_percent": (
                round(total_orders / total_clicks * 100, 2)
                if total_clicks
                else 0.0
            ),
        },
        "daily": daily,
    }