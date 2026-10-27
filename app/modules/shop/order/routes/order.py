from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    tracking_token: str | None = None
from app.modules.admin.notifications.models.admin_notification import (
    AdminNotification,
)
from app.modules.admin.notifications.services.realtime_dispatcher import (
    dispatch_admin_notification_payload,
    serialize_admin_notification,
)
from app.db.session import get_db
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.order.schemas.order import OrderResponse
from app.modules.shop.order.services.order import OrderService
from app.modules.shop.order.schemas.order import (
    OrderResponse,
    OrderTrackingResponse,
    CustomerOrderListResponse
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
    background_tasks: BackgroundTasks,
    payload: CreateOrderRequest | None = None,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    try:
        order = service.create_order(
            checkout_public_id=checkout_public_id,
            customer=current_customer,
            tracking_token=(
                payload.tracking_token.strip()
                if payload and payload.tracking_token
                else None
            )
        )
        notifications = db.scalars(
            select(AdminNotification).where(
                AdminNotification.entity_type == "ORDER",
                AdminNotification.entity_public_id == order.public_id,
                AdminNotification.notification_type == "ORDER_CREATED",
            )
        ).all()


        pending_deliveries = [
            (
                notification.admin_user_id,
                serialize_admin_notification(notification),
            )
            for notification in notifications
        ]

        db.commit()
        db.refresh(order)

        for admin_user_id, payload in pending_deliveries:
            background_tasks.add_task(
                dispatch_admin_notification_payload,
                admin_user_id=admin_user_id,
                payload=payload,
            )
        return order

    except Exception:
        db.rollback()
        raise


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


@router.get(
    "/my",
    response_model=CustomerOrderListResponse,
)
def get_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    orders, total = service.get_customer_orders(
        customer_id=current_customer.id,
        page=page,
        page_size=page_size,
    )

    total_pages = (
        (total + page_size - 1) // page_size
        if total
        else 0
    )

    return {
        "items": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }