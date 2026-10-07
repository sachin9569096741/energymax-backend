from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import (
    get_current_admin,
)

from app.modules.admin.notifications.schemas.notification import (
    AdminNotificationListResponse,
    AdminNotificationReadAllResponse,
    AdminNotificationReadResponse,
    AdminNotificationResponse,
    AdminNotificationUnreadCountResponse,
)

from app.modules.admin.notifications.services.notification import (
    NotificationService,
)


router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin Notifications"],
)


# =========================================================
# LIST NOTIFICATIONS
# =========================================================

@router.get(
    "",
    response_model=AdminNotificationListResponse,
)
def list_notifications(
    current_user: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    unread_only: bool = Query(
        default=False,
    ),
):
    service = NotificationService(db)

    notifications = service.get_notifications(
        admin_user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )

    return AdminNotificationListResponse(
        items=notifications,
        total=len(notifications),
        limit=limit,
        offset=offset,
    )


# =========================================================
# UNREAD COUNT
# =========================================================

@router.get(
    "/unread-count",
    response_model=AdminNotificationUnreadCountResponse,
)
def get_unread_count(
    current_user: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)

    unread_count = service.get_unread_count(
        admin_user_id=current_user.id,
    )

    return AdminNotificationUnreadCountResponse(
        unread_count=unread_count,
    )


# =========================================================
# MARK ALL AS READ
# =========================================================

@router.patch(
    "/read-all",
    response_model=AdminNotificationReadAllResponse,
)
def mark_all_notifications_as_read(
    current_user: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)

    updated_count = service.mark_all_as_read(
        admin_user_id=current_user.id,
    )

    db.commit()

    return AdminNotificationReadAllResponse(
        message="All notifications marked as read.",
        updated_count=updated_count,
    )


# =========================================================
# GET SINGLE NOTIFICATION
# =========================================================

@router.get(
    "/{public_id}",
    response_model=AdminNotificationResponse,
)
def get_notification(
    public_id: str,
    current_user: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)

    notification = service.get_notification(
        public_id=public_id,
        admin_user_id=current_user.id,
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
    response_model=AdminNotificationReadResponse,
)
def mark_notification_as_read(
    public_id: str,
    current_user: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)

    notification = service.mark_as_read(
        public_id=public_id,
        admin_user_id=current_user.id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.commit()
    db.refresh(notification)

    return AdminNotificationReadResponse(
        message="Notification marked as read.",
        notification=notification,
    )