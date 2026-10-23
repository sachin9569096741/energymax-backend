from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_withdrawal import (
    AffiliateWithdrawal,
)
from app.modules.affiliate.schemas.withdrawal import (
    WithdrawalCreate,
    WithdrawalMarkPaid,
    WithdrawalReject,
    WithdrawalResponse,
)
from app.modules.affiliate.security.dependencies import get_current_affiliate
from app.modules.affiliate.services.withdrawal_service import WithdrawalService

affiliate_router = APIRouter(
    prefix="/affiliate/withdrawals",
    tags=["Affiliate - Withdrawals"],
)

admin_router = APIRouter(
    prefix="/admin/affiliates/withdrawals",
    tags=["Admin - Affiliate Withdrawals"],
)


@affiliate_router.post(
    "",
    response_model=WithdrawalResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_withdrawal(
    payload: WithdrawalCreate,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    try:
        withdrawal = WithdrawalService(db).create_request(
            affiliate,
            amount=payload.amount,
            currency=payload.currency,
            idempotency_key=payload.idempotency_key,
        )
        db.commit()
        db.refresh(withdrawal)
        return withdrawal
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A conflicting withdrawal request exists.",
        ) from exc


@affiliate_router.get("", response_model=list[WithdrawalResponse])
def my_withdrawals(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    return WithdrawalService(db).list_for_affiliate(
        affiliate,
        limit=limit,
        offset=offset,
    )


@admin_router.get("", response_model=list[WithdrawalResponse])
def admin_list_withdrawals(
    withdrawal_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return WithdrawalService(db).list_for_admin(
        withdrawal_status=withdrawal_status,
        limit=limit,
        offset=offset,
    )


@admin_router.get(
    "/{public_id}",
    response_model=WithdrawalResponse,
)
def admin_get_withdrawal(
    public_id: str,
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return WithdrawalService(db).get_by_public_id(public_id)


@admin_router.post(
    "/{public_id}/approve",
    response_model=WithdrawalResponse,
)
def approve_withdrawal(
    public_id: str,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        withdrawal = WithdrawalService(db).approve(public_id, admin)
        db.commit()
        db.refresh(withdrawal)
        return withdrawal
    except HTTPException:
        db.rollback()
        raise


@admin_router.post(
    "/{public_id}/reject",
    response_model=WithdrawalResponse,
)
def reject_withdrawal(
    public_id: str,
    payload: WithdrawalReject,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        withdrawal = WithdrawalService(db).reject(
            public_id,
            admin,
            payload.reason,
        )
        db.commit()
        db.refresh(withdrawal)
        return withdrawal
    except HTTPException:
        db.rollback()
        raise


@admin_router.post(
    "/{public_id}/mark-paid",
    response_model=WithdrawalResponse,
)
def mark_withdrawal_paid(
    public_id: str,
    payload: WithdrawalMarkPaid,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        withdrawal = WithdrawalService(db).mark_paid(
            public_id,
            admin,
            payload.payout_reference,
        )
        db.commit()
        db.refresh(withdrawal)
        return withdrawal
    except HTTPException:
        db.rollback()
        raise