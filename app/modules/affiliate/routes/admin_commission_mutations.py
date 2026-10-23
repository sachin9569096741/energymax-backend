from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)
from app.modules.affiliate.schemas.commission_adjustment import (
    CommissionAdjustmentRequest,
    CommissionReversalRequest,
)
from app.modules.affiliate.schemas.commision_ledger import (
    CommissionLedgerResponse,
)
from app.modules.affiliate.services.commission_ledger_mutation_service import (
    CommissionLedgerMutationService,
)

router = APIRouter(
    prefix="/admin/affiliates/commissions",
    tags=["Admin - Commission Adjustments and Reversals"],
)


def _get_original_commission(
    db: Session,
    public_id: str,
) -> AffiliateCommissionLedger:
    original = db.query(AffiliateCommissionLedger).filter(
        AffiliateCommissionLedger.public_id == public_id
    ).first()

    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commission ledger entry not found.",
        )

    return original


@router.post(
    "/{public_id}/adjust",
    response_model=CommissionLedgerResponse,
    status_code=status.HTTP_201_CREATED,
)
def adjust_commission(
    public_id: str,
    payload: CommissionAdjustmentRequest,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        original = _get_original_commission(db, public_id)

        entry = CommissionLedgerMutationService(db).adjust(
            original=original,
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            idempotency_key=payload.idempotency_key,
            admin_id=admin.id,
        )

        db.commit()
        db.refresh(entry)
        return entry

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The ledger operation conflicts with an existing entry. "
                "Check the idempotency key and retry safely."
            ),
        ) from exc
    except Exception:
        db.rollback()
        raise


@router.post(
    "/{public_id}/reverse",
    response_model=CommissionLedgerResponse,
    status_code=status.HTTP_201_CREATED,
)
def reverse_commission(
    public_id: str,
    payload: CommissionReversalRequest,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        original = _get_original_commission(db, public_id)

        entry = CommissionLedgerMutationService(db).reverse(
            original=original,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            admin_id=admin.id,
        )

        db.commit()
        db.refresh(entry)
        return entry

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The ledger operation conflicts with an existing entry. "
                "Check the idempotency key and retry safely."
            ),
        ) from exc
    except Exception:
        db.rollback()
        raise