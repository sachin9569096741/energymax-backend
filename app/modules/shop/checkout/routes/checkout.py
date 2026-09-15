from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.checkout.schemas.checkout import (
    CheckoutAddressRequest,
    CheckoutResponse,
)
from app.modules.shop.checkout.services.checkout import CheckoutService
from app.modules.shop.customer.security.dependencies import get_current_customer


router = APIRouter(
    prefix="/checkout",
    tags=["Shop - Checkout"],
)


@router.post(
    "",
    response_model=CheckoutResponse,
    status_code=201,
)
def create_checkout(
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = CheckoutService(db)

    checkout = service.create_checkout(
        customer_id=current_customer.id,
    )

    db.commit()
    db.refresh(checkout)

    return checkout


@router.get(
    "/{checkout_public_id}",
    response_model=CheckoutResponse,
)
def get_checkout(
    checkout_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = CheckoutService(db)

    return service.get_checkout(
        public_id=checkout_public_id,
        customer_id=current_customer.id,
    )


@router.patch(
    "/{checkout_public_id}/address",
    response_model=CheckoutResponse,
)
def select_checkout_address(
    checkout_public_id: str,
    data: CheckoutAddressRequest,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = CheckoutService(db)

    checkout = service.select_address(
        checkout_public_id=checkout_public_id,
        customer_id=current_customer.id,
        address_public_id=data.address_public_id,
    )

    db.commit()
    db.refresh(checkout)

    return checkout


@router.post(
    "/{checkout_public_id}/confirm",
    response_model=CheckoutResponse,
)
def confirm_checkout(
    checkout_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = CheckoutService(db)

    checkout = service.confirm_checkout(
        checkout_public_id=checkout_public_id,
        customer_id=current_customer.id,
    )

    db.commit()
    db.refresh(checkout)

    return checkout