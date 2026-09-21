from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.security.dependencies import (
    get_current_customer,
)
from app.modules.shop.payment.schemas.refund import (
    RefundRequest,
    RefundResponse,
)
from app.modules.shop.payment.services.refund import RefundService


router = APIRouter(
    prefix="/payments",
    tags=["Shop - Refunds"],
)


@router.post(
    "/{payment_public_id}/refunds",
    response_model=RefundResponse,
    status_code=201,
)
def create_refund(
    payment_public_id: str,
    request: RefundRequest,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required.",
        )

    service = RefundService(db)

    try:
        refund = service.create_refund(
            payment_public_id=payment_public_id,
            customer=current_customer,
            amount=request.amount,
            idempotency_key=idempotency_key,
            reason=request.reason,
        )

        db.commit()
        db.refresh(refund)

        return refund

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to process refund.",
        )
    

@router.post(
    "/refunds/{refund_public_id}/reconcile",
    response_model=RefundResponse,
    status_code=200,
)
def reconcile_refund(
    refund_public_id: str,
    db: Session = Depends(get_db),
):
    service = RefundService(db)

    try:
        refund = service.reconcile_refund(
            refund_public_id=refund_public_id,
        )

        db.commit()
        db.refresh(refund)

        return refund

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to reconcile refund.",
        )