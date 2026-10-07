from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.admin.notifications.models.admin_notification import (
    AdminNotification,
)


class AdminNotificationRepository:

    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # CREATE
    # =========================================================

    def create(
        self,
        *,
        admin_user_id: int,
        notification_type: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_public_id: str | None = None,
        data: dict | None = None,
    ) -> AdminNotification:

        notification = AdminNotification(
            admin_user_id=admin_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            data=data,
            is_read=False,
        )

        self.db.add(notification)
        self.db.flush()

        return notification

    # =========================================================
    # GET BY PUBLIC ID
    # =========================================================

    def get_by_public_id(
        self,
        public_id: str,
        admin_user_id: int,
    ) -> AdminNotification | None:

        statement = select(AdminNotification).where(
            AdminNotification.public_id == public_id,
            AdminNotification.admin_user_id == admin_user_id,
        )

        return self.db.scalar(statement)

    # =========================================================
    # LIST
    # =========================================================

    def list_for_admin(
        self,
        *,
        admin_user_id: int,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[AdminNotification]:

        statement = (
            select(AdminNotification)
            .where(
                AdminNotification.admin_user_id == admin_user_id
            )
            .order_by(
                AdminNotification.created_at.desc()
            )
            .limit(limit)
            .offset(offset)
        )

        if unread_only:
            statement = statement.where(
                AdminNotification.is_read.is_(False)
            )

        return list(
            self.db.scalars(statement).all()
        )

    # =========================================================
    # UNREAD COUNT
    # =========================================================

    def unread_count(
        self,
        admin_user_id: int,
    ) -> int:

        statement = select(
            func.count(AdminNotification.id)
        ).where(
            AdminNotification.admin_user_id == admin_user_id,
            AdminNotification.is_read.is_(False),
        )

        return int(
            self.db.scalar(statement) or 0
        )

    # =========================================================
    # MARK ONE AS READ
    # =========================================================

    def mark_as_read(
        self,
        *,
        notification: AdminNotification,
    ) -> AdminNotification:

        if not notification.is_read:

            notification.is_read = True

            notification.read_at = (
                datetime.now(timezone.utc)
            )

            self.db.flush()

        return notification

    # =========================================================
    # MARK ALL AS READ
    # =========================================================

    def mark_all_as_read(
        self,
        admin_user_id: int,
    ) -> int:

        now = datetime.now(timezone.utc)

        statement = (
            update(AdminNotification)
            .where(
                AdminNotification.admin_user_id
                == admin_user_id,
                AdminNotification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=now,
            )
        )

        result = self.db.execute(statement)

        self.db.flush()

        return result.rowcount or 0