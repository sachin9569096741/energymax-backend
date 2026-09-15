from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.order.schemas.order import OrderResponse
from app.modules.shop.order.services.order import OrderService


router = APIRouter(
    prefix="/orders",
    tags=["Shop - Orders"],
)


@router.post(
    "/from-checkout/{checkout_public_id}",
    response_model=OrderResponse,
    status_code=201,
)
def create_order_from_checkout(
    checkout_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    order = service.create_order(
        checkout_public_id=checkout_public_id,
        customer=current_customer,
    )

    db.commit()
    db.refresh(order)

    return order