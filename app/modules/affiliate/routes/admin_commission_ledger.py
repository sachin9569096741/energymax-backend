from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin
from app.modules.affiliate.schemas.commision_ledger import (
    CommissionLedgerResponse,
)
from app.modules.affiliate.services.commission_ledger_query_service import (
    CommissionLedgerQueryService,
)

router = APIRouter(
    prefix="/admin/affiliates/commissions",
    tags=["Admin - Affiliate Commissions"],
)


@router.get("", response_model=list[CommissionLedgerResponse])
def list_commissions(
    affiliate_public_id: str | None = Query(default=None),
    entry_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return CommissionLedgerQueryService(db).list_commissions(
        affiliate_public_id=affiliate_public_id,
        entry_type=entry_type,
        limit=limit,
        offset=offset,
    )


@router.get("/{public_id}", response_model=CommissionLedgerResponse)
def get_commission(
    public_id: str,
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return CommissionLedgerQueryService(db).get_commission(public_id)