from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.security.dependencies import get_current_affiliate
from app.modules.affiliate.services.wallet_service import WalletService

router = APIRouter(
    prefix="/affiliate/wallet",
    tags=["Affiliate - Wallet"],
)


@router.get("")
def get_wallet(
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    return WalletService(db).get_wallet(affiliate)


@router.get("/ledger")
def get_wallet_ledger(
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    from app.modules.affiliate.models.affiliate_commission_ledger import (
        AffiliateCommissionLedger,
    )
    from app.modules.affiliate.models.affiliate_withdrawal import (
        AffiliateWithdrawal,
    )
    from sqlalchemy import select

    commissions = list(
        db.scalars(
            select(AffiliateCommissionLedger)
            .where(
                AffiliateCommissionLedger.affiliate_id == affiliate.id
            )
            .order_by(AffiliateCommissionLedger.created_at.desc())
        ).all()
    )

    withdrawals = list(
        db.scalars(
            select(AffiliateWithdrawal)
            .where(AffiliateWithdrawal.affiliate_id == affiliate.id)
            .order_by(AffiliateWithdrawal.requested_at.desc())
        ).all()
    )

    return {
        "commissions": commissions,
        "withdrawals": withdrawals,
    }