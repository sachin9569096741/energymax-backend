from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.shop.customer.security.dependencies import (
    get_current_customer,
)

from app.modules.shop.customer.models.customer import Customer

from app.modules.shop.customer.notifications.schemas.notification import (
    CustomerNotificationListResponse,
    CustomerNotificationReadAllResponse,
    CustomerNotificationReadResponse,
    CustomerNotificationResponse,
    CustomerNotificationUnreadCountResponse,
)

from app.modules.shop.customer.notifications.services.notification import (
    CustomerNotificationService,
)


router = APIRouter(
    prefix="/customer/notifications",
    tags=["Customer Notifications"],
)


# =========================================================
# LIST
# =========================================================

@router.get(
    "",
    response_model=CustomerNotificationListResponse,
)
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):

    service = CustomerNotificationService(db)

    items, total = service.list_notifications(
        customer_id=current_customer.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )

    return CustomerNotificationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# =========================================================
# UNREAD COUNT
# =========================================================

@router.get(
    "/unread-count",
    response_model=CustomerNotificationUnreadCountResponse,
)
def unread_count(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):

    service = CustomerNotificationService(db)

    count = service.get_unread_count(
        customer_id=current_customer.id,
    )

    return CustomerNotificationUnreadCountResponse(
        unread_count=count,
    )


# =========================================================
# GET ONE
# =========================================================

@router.get(
    "/{public_id}",
    response_model=CustomerNotificationResponse,
)
def get_notification(
    public_id: str,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):

    service = CustomerNotificationService(db)

    notification = service.get_notification(
        customer_id=current_customer.id,
        public_id=public_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return notification


# =========================================================
# MARK ONE AS READ
# =========================================================

@router.patch(
    "/{public_id}/read",
    response_model=CustomerNotificationResponse,
)
def mark_as_read(
    public_id: str,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):

    service = CustomerNotificationService(db)

    notification = service.mark_as_read(
        customer_id=current_customer.id,
        public_id=public_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.commit()
    db.refresh(notification)

    return notification


# =========================================================
# MARK ALL AS READ
# =========================================================

@router.patch(
    "/read-all",
    response_model=CustomerNotificationReadAllResponse,
)
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):

    service = CustomerNotificationService(db)

    updated_count = service.mark_all_as_read(
        customer_id=current_customer.id,
    )

    db.commit()

    return CustomerNotificationReadAllResponse(
        updated_count=updated_count,
    )