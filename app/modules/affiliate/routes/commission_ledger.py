from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.schemas.commision_ledger import (
    AffiliateEarningsResponse,
    CommissionLedgerResponse,
)
from app.modules.affiliate.security.dependencies import get_current_affiliate
from app.modules.affiliate.services.commission_ledger_query_service import (
    CommissionLedgerQueryService,
)

router = APIRouter(
    prefix="/affiliate",
    tags=["Affiliate - Commissions and Earnings"],
)


@router.get(
    "/commissions",
    response_model=list[CommissionLedgerResponse],
)
def get_my_commissions(
    entry_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    return CommissionLedgerQueryService(db).list_affiliate_commissions(
        affiliate,
        entry_type=entry_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/earnings",
    response_model=list[AffiliateEarningsResponse],
)
def get_my_earnings(
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    return CommissionLedgerQueryService(db).get_earnings_summary(
        affiliate
    )