from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)
from app.modules.affiliate.models.affiliate_referral_click import (
    AffiliateReferralClick,
)
from app.modules.affiliate.security.dependencies import (
    get_current_affiliate,
)


affiliate_router = APIRouter(
    prefix="/affiliates",
    tags=["Affiliate Analytics"],
)

admin_router = APIRouter(
    prefix="/admin/affiliates/analytics",
    tags=["Admin - Affiliate Analytics"],
)


# ============================================================
# SHARED HELPERS
# ============================================================

def _date_window(
    start_date: date,
    end_date: date,
) -> tuple[datetime, datetime]:
    """
    Return UTC boundaries for an inclusive date range.

    Example:
        start_date = 2026-10-01
        end_date   = 2026-10-10

    Database range:
        [2026-10-01 00:00 UTC, 2026-10-11 00:00 UTC)
    """

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

    start = datetime.combine(
        start_date,
        time.min,
        tzinfo=timezone.utc,
    )

    end = datetime.combine(
        end_date + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )

    return start, end


def _click_count(
    db: Session,
    start: datetime,
    end: datetime,
    affiliate_id: int | None = None,
) -> int:
    query = select(
        func.count(AffiliateReferralClick.id)
    ).where(
        AffiliateReferralClick.clicked_at >= start,
        AffiliateReferralClick.clicked_at < end,
    )

    if affiliate_id is not None:
        query = query.where(
            AffiliateReferralClick.affiliate_id == affiliate_id
        )

    return int(db.scalar(query) or 0)


def _attribution_count(
    db: Session,
    start: datetime,
    end: datetime,
    affiliate_id: int | None = None,
) -> int:
    query = select(
        func.count(AffiliateAttribution.id)
    ).where(
        AffiliateAttribution.attributed_at >= start,
        AffiliateAttribution.attributed_at < end,
    )

    if affiliate_id is not None:
        query = query.where(
            AffiliateAttribution.affiliate_id == affiliate_id
        )

    return int(db.scalar(query) or 0)


def _commission_totals(
    db: Session,
    start: datetime,
    end: datetime,
    affiliate_id: int | None = None,
) -> list[dict]:
    """
    Aggregate ledger entries by currency.

    Net earnings are calculated as the sum of all ledger entries,
    including commissions, reversals, and adjustments.
    """

    query = select(
        AffiliateCommissionLedger.currency,
        AffiliateCommissionLedger.entry_type,
        func.sum(
            AffiliateCommissionLedger.amount
        ).label("amount"),
        func.count(
            AffiliateCommissionLedger.id
        ).label("entries"),
    ).where(
        AffiliateCommissionLedger.created_at >= start,
        AffiliateCommissionLedger.created_at < end,
    )

    if affiliate_id is not None:
        query = query.where(
            AffiliateCommissionLedger.affiliate_id == affiliate_id
        )

    rows = db.execute(
        query.group_by(
            AffiliateCommissionLedger.currency,
            AffiliateCommissionLedger.entry_type,
        )
    ).all()

    by_currency: dict[str, dict] = {}

    for row in rows:
        currency = row.currency

        item = by_currency.setdefault(
            currency,
            {
                "currency": currency,
                "commission_amount": Decimal("0.00"),
                "reversal_amount": Decimal("0.00"),
                "adjustment_amount": Decimal("0.00"),
                "net_earnings": Decimal("0.00"),
                "commission_entries": 0,
                "ledger_entries": 0,
            },
        )

        amount = Decimal(str(row.amount or 0))

        item["net_earnings"] += amount
        item["ledger_entries"] += int(row.entries)

        if row.entry_type == "COMMISSION":
            item["commission_amount"] += amount
            item["commission_entries"] += int(row.entries)

        elif row.entry_type == "REVERSAL":
            item["reversal_amount"] += amount

        elif row.entry_type == "ADJUSTMENT":
            item["adjustment_amount"] += amount

    return [
        by_currency[currency]
        for currency in sorted(by_currency)
    ]


def _group_expression(
    group_by: str,
    column,
):
    """
    Build the SQL grouping expression.

    Day:   calendar date
    Week:  PostgreSQL week bucket
    Month: PostgreSQL month bucket
    """

    if group_by == "day":
        return func.date(column)

    return func.date_trunc(group_by, column)


# ============================================================
# AFFILIATE: ANALYTICS OVERVIEW
# ============================================================

@affiliate_router.get("/analytics/overview")
def affiliate_analytics_overview(
    start_date: date = Query(...),
    end_date: date = Query(...),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    clicks = _click_count(
        db,
        start,
        end,
        affiliate.id,
    )

    conversions = _attribution_count(
        db,
        start,
        end,
        affiliate.id,
    )

    conversion_rate = (
        round(conversions / clicks * 100, 2)
        if clicks
        else 0.0
    )

    earnings = _commission_totals(
        db,
        start,
        end,
        affiliate.id,
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
        },
        "clicks": clicks,
        "conversions": conversions,
        "conversion_rate_percent": conversion_rate,
        "earnings": earnings,
    }


# ============================================================
# AFFILIATE: PERFORMANCE ANALYTICS
# ============================================================

@affiliate_router.get("/analytics/performance")
def affiliate_analytics_performance(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: Literal["day", "week", "month"] = Query("day"),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    click_bucket = _group_expression(
        group_by,
        AffiliateReferralClick.clicked_at,
    )

    conversion_bucket = _group_expression(
        group_by,
        AffiliateAttribution.attributed_at,
    )

    # Aggregate referral clicks.
    click_rows = db.execute(
        select(
            click_bucket.label("bucket"),
            func.count(
                AffiliateReferralClick.id
            ).label("total"),
        )
        .where(
            AffiliateReferralClick.affiliate_id == affiliate.id,
            AffiliateReferralClick.clicked_at >= start,
            AffiliateReferralClick.clicked_at < end,
        )
        .group_by(click_bucket)
        .order_by(click_bucket)
    ).all()

    # Aggregate attributed conversions.
    conversion_rows = db.execute(
        select(
            conversion_bucket.label("bucket"),
            func.count(
                AffiliateAttribution.id
            ).label("total"),
        )
        .where(
            AffiliateAttribution.affiliate_id == affiliate.id,
            AffiliateAttribution.attributed_at >= start,
            AffiliateAttribution.attributed_at < end,
        )
        .group_by(conversion_bucket)
        .order_by(conversion_bucket)
    ).all()

    buckets: dict[str, dict] = {}

    for row in click_rows:
        key = (
            row.bucket.isoformat()
            if hasattr(row.bucket, "isoformat")
            else str(row.bucket)
        )

        buckets.setdefault(
            key,
            {
                "period": key,
                "clicks": 0,
                "conversions": 0,
            },
        )["clicks"] = int(row.total)

    for row in conversion_rows:
        key = (
            row.bucket.isoformat()
            if hasattr(row.bucket, "isoformat")
            else str(row.bucket)
        )

        buckets.setdefault(
            key,
            {
                "period": key,
                "clicks": 0,
                "conversions": 0,
            },
        )["conversions"] = int(row.total)

    series = sorted(
        buckets.values(),
        key=lambda item: item["period"],
    )

    for item in series:
        clicks = item["clicks"]
        conversions = item["conversions"]

        item["conversion_rate_percent"] = (
            round(conversions / clicks * 100, 2)
            if clicks
            else 0.0
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
            "group_by": group_by,
        },
        "data": series,
    }


# ============================================================
# AFFILIATE: EARNINGS ANALYTICS
# ============================================================

@affiliate_router.get("/analytics/earnings")
def affiliate_analytics_earnings(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: Literal["day", "week", "month"] = Query("day"),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    bucket = _group_expression(
        group_by,
        AffiliateCommissionLedger.created_at,
    )

    rows = db.execute(
        select(
            bucket.label("bucket"),
            AffiliateCommissionLedger.currency,
            AffiliateCommissionLedger.entry_type,
            func.sum(
                AffiliateCommissionLedger.amount
            ).label("amount"),
            func.count(
                AffiliateCommissionLedger.id
            ).label("entries"),
        )
        .where(
            AffiliateCommissionLedger.affiliate_id == affiliate.id,
            AffiliateCommissionLedger.created_at >= start,
            AffiliateCommissionLedger.created_at < end,
        )
        .group_by(
            bucket,
            AffiliateCommissionLedger.currency,
            AffiliateCommissionLedger.entry_type,
        )
        .order_by(bucket)
    ).all()

    series: dict[tuple[str, str], dict] = {}

    for row in rows:
        period_key = (
            row.bucket.isoformat()
            if hasattr(row.bucket, "isoformat")
            else str(row.bucket)
        )

        key = (period_key, row.currency)

        item = series.setdefault(
            key,
            {
                "period": period_key,
                "currency": row.currency,
                "commission_amount": Decimal("0.00"),
                "reversal_amount": Decimal("0.00"),
                "adjustment_amount": Decimal("0.00"),
                "net_earnings": Decimal("0.00"),
                "ledger_entries": 0,
            },
        )

        amount = Decimal(str(row.amount or 0))

        item["net_earnings"] += amount
        item["ledger_entries"] += int(row.entries)

        if row.entry_type == "COMMISSION":
            item["commission_amount"] += amount

        elif row.entry_type == "REVERSAL":
            item["reversal_amount"] += amount

        elif row.entry_type == "ADJUSTMENT":
            item["adjustment_amount"] += amount

    data = sorted(
        series.values(),
        key=lambda item: (
            item["period"],
            item["currency"],
        ),
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
            "group_by": group_by,
        },
        "data": data,
    }


# ============================================================
# ADMIN: PROGRAMME OVERVIEW
# ============================================================

@admin_router.get("/overview")
def admin_affiliate_analytics_overview(
    start_date: date = Query(...),
    end_date: date = Query(...),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    clicks = _click_count(
        db,
        start,
        end,
    )

    conversions = _attribution_count(
        db,
        start,
        end,
    )

    active_affiliates = int(
        db.scalar(
            select(func.count(Affiliate.id)).where(
                Affiliate.status == "active",
                Affiliate.activated_at.is_not(None),
            )
        )
        or 0
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
        },
        "active_affiliates": active_affiliates,
        "clicks": clicks,
        "conversions": conversions,
        "conversion_rate_percent": (
            round(conversions / clicks * 100, 2)
            if clicks
            else 0.0
        ),
        "earnings": _commission_totals(
            db,
            start,
            end,
        ),
    }


# ============================================================
# ADMIN: AFFILIATE-BY-AFFILIATE PERFORMANCE
# ============================================================

@admin_router.get("/performance")
def admin_affiliate_analytics_performance(
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    # Aggregate clicks separately to avoid multiplying counts
    # when joining clicks and conversions.
    click_subquery = (
        select(
            AffiliateReferralClick.affiliate_id.label("affiliate_id"),
            func.count(
                AffiliateReferralClick.id
            ).label("clicks"),
        )
        .where(
            AffiliateReferralClick.clicked_at >= start,
            AffiliateReferralClick.clicked_at < end,
        )
        .group_by(
            AffiliateReferralClick.affiliate_id,
        )
        .subquery()
    )

    # Aggregate conversions separately.
    conversion_subquery = (
        select(
            AffiliateAttribution.affiliate_id.label("affiliate_id"),
            func.count(
                AffiliateAttribution.id
            ).label("conversions"),
        )
        .where(
            AffiliateAttribution.attributed_at >= start,
            AffiliateAttribution.attributed_at < end,
        )
        .group_by(
            AffiliateAttribution.affiliate_id,
        )
        .subquery()
    )

    rows = db.execute(
        select(
            Affiliate.public_id,
            Affiliate.public_code,
            Affiliate.full_name,
            Affiliate.status,
            Affiliate.activated_at,
            func.coalesce(
                click_subquery.c.clicks,
                0,
            ).label("clicks"),
            func.coalesce(
                conversion_subquery.c.conversions,
                0,
            ).label("conversions"),
        )
        .outerjoin(
            click_subquery,
            click_subquery.c.affiliate_id == Affiliate.id,
        )
        .outerjoin(
            conversion_subquery,
            conversion_subquery.c.affiliate_id == Affiliate.id,
        )
        .order_by(
            func.coalesce(
                conversion_subquery.c.conversions,
                0,
            ).desc(),
            func.coalesce(
                click_subquery.c.clicks,
                0,
            ).desc(),
            Affiliate.id,
        )
        .limit(limit)
        .offset(offset)
    ).all()

    data = []

    for row in rows:
        clicks = int(row.clicks)
        conversions = int(row.conversions)

        data.append(
            {
                "affiliate_public_id": row.public_id,
                "public_code": row.public_code,
                "full_name": row.full_name,
                "status": row.status,
                "is_activated": row.activated_at is not None,
                "clicks": clicks,
                "conversions": conversions,
                "conversion_rate_percent": (
                    round(conversions / clicks * 100, 2)
                    if clicks
                    else 0.0
                ),
            }
        )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
        },
        "limit": limit,
        "offset": offset,
        "data": data,
    }


# ============================================================
# ADMIN: EARNINGS ANALYTICS
# ============================================================

@admin_router.get("/earnings")
def admin_affiliate_analytics_earnings(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: Literal["day", "week", "month"] = Query("day"),
    affiliate_public_id: str | None = Query(None),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    start, end = _date_window(start_date, end_date)

    bucket = func.date_trunc(
        group_by,
        AffiliateCommissionLedger.created_at,
    )

    query = select(
        bucket.label("bucket"),
        AffiliateCommissionLedger.currency,
        AffiliateCommissionLedger.entry_type,
        func.sum(
            AffiliateCommissionLedger.amount
        ).label("amount"),
        func.count(
            AffiliateCommissionLedger.id
        ).label("entries"),
    ).where(
        AffiliateCommissionLedger.created_at >= start,
        AffiliateCommissionLedger.created_at < end,
    )

    # Optional filter for a single affiliate.
    if affiliate_public_id:
        affiliate = db.scalar(
            select(Affiliate).where(
                Affiliate.public_id == affiliate_public_id,
            )
        )

        if affiliate is None:
            raise HTTPException(
                status_code=404,
                detail="Affiliate not found.",
            )

        query = query.where(
            AffiliateCommissionLedger.affiliate_id == affiliate.id
        )

    rows = db.execute(
        query.group_by(
            bucket,
            AffiliateCommissionLedger.currency,
            AffiliateCommissionLedger.entry_type,
        ).order_by(bucket)
    ).all()

    series: dict[tuple[str, str], dict] = {}

    for row in rows:
        period_key = (
            row.bucket.isoformat()
            if hasattr(row.bucket, "isoformat")
            else str(row.bucket)
        )

        key = (period_key, row.currency)

        item = series.setdefault(
            key,
            {
                "period": period_key,
                "currency": row.currency,
                "commission_amount": Decimal("0.00"),
                "reversal_amount": Decimal("0.00"),
                "adjustment_amount": Decimal("0.00"),
                "net_earnings": Decimal("0.00"),
                "ledger_entries": 0,
            },
        )

        amount = Decimal(str(row.amount or 0))

        item["net_earnings"] += amount
        item["ledger_entries"] += int(row.entries)

        if row.entry_type == "COMMISSION":
            item["commission_amount"] += amount

        elif row.entry_type == "REVERSAL":
            item["reversal_amount"] += amount

        elif row.entry_type == "ADJUSTMENT":
            item["adjustment_amount"] += amount

    data = sorted(
        series.values(),
        key=lambda item: (
            item["period"],
            item["currency"],
        ),
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "UTC",
            "group_by": group_by,
        },
        "affiliate_public_id": affiliate_public_id,
        "data": data,
    }