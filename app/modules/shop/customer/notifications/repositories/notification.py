from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.shop.customer.notifications.models.customer_notification import (
    CustomerNotification,
)


class CustomerNotificationRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        *,
        customer_id: int,
        notification_type: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_public_id: str | None = None,
        data: dict | None = None,
    ) -> CustomerNotification:

        notification = CustomerNotification(
            customer_id=customer_id,
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

    # ---------------------------------------------------------
    # GET ONE
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        *,
        public_id: str,
        customer_id: int,
    ) -> CustomerNotification | None:

        statement = select(CustomerNotification).where(
            CustomerNotification.public_id == public_id,
            CustomerNotification.customer_id == customer_id,
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list_for_customer(
        self,
        *,
        customer_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CustomerNotification]:

        statement = select(CustomerNotification).where(
            CustomerNotification.customer_id == customer_id
        )

        if unread_only:
            statement = statement.where(
                CustomerNotification.is_read.is_(False)
            )

        statement = (
            statement
            .order_by(CustomerNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(statement).all())

    # ---------------------------------------------------------
    # COUNT
    # ---------------------------------------------------------

    def count_for_customer(
        self,
        *,
        customer_id: int,
        unread_only: bool = False,
    ) -> int:

        statement = select(
            func.count(CustomerNotification.id)
        ).where(
            CustomerNotification.customer_id == customer_id
        )

        if unread_only:
            statement = statement.where(
                CustomerNotification.is_read.is_(False)
            )

        return int(self.db.scalar(statement) or 0)

    # ---------------------------------------------------------
    # UNREAD COUNT
    # ---------------------------------------------------------

    def unread_count(
        self,
        *,
        customer_id: int,
    ) -> int:

        statement = select(
            func.count(CustomerNotification.id)
        ).where(
            CustomerNotification.customer_id == customer_id,
            CustomerNotification.is_read.is_(False),
        )

        return int(self.db.scalar(statement) or 0)

    # ---------------------------------------------------------
    # MARK ONE AS READ
    # ---------------------------------------------------------

    def mark_as_read(
        self,
        notification: CustomerNotification,
    ) -> CustomerNotification:

        if not notification.is_read:

            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

            self.db.flush()

        return notification

    # ---------------------------------------------------------
    # MARK ALL AS READ
    # ---------------------------------------------------------

    def mark_all_as_read(
        self,
        *,
        customer_id: int,
    ) -> int:

        now = datetime.now(timezone.utc)

        statement = (
            update(CustomerNotification)
            .where(
                CustomerNotification.customer_id == customer_id,
                CustomerNotification.is_read.is_(False),
            )
            .values(
                is_read=True,
                read_at=now,
            )
        )

        result = self.db.execute(statement)

        self.db.flush()

        return result.rowcount or 0