from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.order.schemas.order import OrderResponse
from app.modules.shop.order.services.order import OrderService
from app.modules.shop.order.schemas.order import (
    OrderResponse,
    OrderTrackingResponse,
)
from app.modules.shop.order.constants.status import (
    ORDER_STATUS_LABELS,
)


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

@router.get(
    "/{order_public_id}/tracking",
    response_model=OrderTrackingResponse,
)
def get_order_tracking(
    order_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    order = service.get_order_tracking(
        order_public_id=order_public_id,
        customer_id=current_customer.id,
    )

    timeline = []

    for history in order.status_history:
        timeline.append(
            {
                "status": history.status,
                "label": ORDER_STATUS_LABELS.get(
                    history.status,
                    history.status.replace("_", " ").title(),
                ),
                "completed": True,
                "current": history.status == order.status,
                "timestamp": history.created_at,
                "note": history.note,
            }
        )

    return {
        "public_id": order.public_id,
        "order_number": order.order_number,
        "current_status": order.status,
        "timeline": timeline,
    }


@router.get(
    "/track/{order_number}",
    response_model=OrderTrackingResponse,
)
def track_order_by_number(
    order_number: str,
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    return service.get_order_tracking_by_number(
        order_number=order_number,
    )