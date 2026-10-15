from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import (
    require_permission,
)
from app.modules.shop.shipping.schemas.shipment import (
    ShipmentCreateRequest,
    ShipmentResponse,
)
from app.modules.shop.shipping.services.shipment import ShipmentService
from app.core.shiprocket import ShiprocketError
from fastapi import Query
from app.modules.admin.order.schemas.order import (
    AdminOrderListResponse,
    AdminOrderStatusUpdateRequest,
)
from app.modules.shop.order.repositories.order import OrderRepository
from app.modules.shop.order.schemas.order import OrderResponse
from app.modules.shop.order.services.order import OrderService


router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin - Orders"],
)



@router.get(
    "/{order_public_id}",
    response_model=OrderResponse,
)
def get_order(
    order_public_id: str,
    current_admin: AdminUser = Depends(
        require_permission("orders.view")
    ),
    db: Session = Depends(get_db),
):
    repository = OrderRepository(db)

    order = repository.get_admin_by_public_id(
        public_id=order_public_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    return order
@router.patch(
    "/{order_public_id}/status",
    response_model=OrderResponse,
)
def update_order_status(
    order_public_id: str,
    payload: AdminOrderStatusUpdateRequest,
    current_admin: AdminUser = Depends(
        require_permission("orders.update_status")
    ),
    db: Session = Depends(get_db),
):
    repository = OrderRepository(db)

    order = repository.get_admin_by_public_id(
        public_id=order_public_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )

    service = OrderService(db)

    try:
        updated_order = service.update_order_status(
            order=order,
            new_status=payload.status,
            note=payload.note,
            changed_by=f"admin:{current_admin.id}",
        )

        db.commit()
        db.refresh(updated_order)

        return updated_order

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    

@router.get(
    "",
    response_model=AdminOrderListResponse,
)
def list_orders(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    current_admin: AdminUser = Depends(
        require_permission("orders.view")
    ),
    db: Session = Depends(get_db),
):
    service = OrderService(db)

    try:
        return service.list_admin_orders(
            page=page,
            page_size=page_size,
            status=status_filter,
            search=search,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc



@router.post(
    "/{order_public_id}/shipment",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order_shipment(
    order_public_id: str,
    payload: ShipmentCreateRequest,
    current_admin: AdminUser = Depends(
        require_permission("orders.update_status")
    ),
    db: Session = Depends(get_db),
):
    service = ShipmentService(db)

    try:
        return service.create_shipment(
            order_public_id=order_public_id,
            package=payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ShiprocketError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
