from sqlalchemy.orm import Session

from app.modules.admin.notifications.models.admin_notification import (
    AdminNotification,
)
from app.modules.admin.notifications.repositories.notification import (
    AdminNotificationRepository,
)


class NotificationService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = AdminNotificationRepository(db)

    # ---------------------------------------------------------
    # CREATE NOTIFICATION
    # ---------------------------------------------------------

    def create_notification(
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
        """
        Create a single notification for one admin user.
        """

        return self.repository.create(
            admin_user_id=admin_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            data=data,
        )

    # ---------------------------------------------------------
    # ORDER CREATED
    # ---------------------------------------------------------

    def notify_order_created(
        self,
        *,
        admin_user_id: int,
        order_public_id: str,
        order_number: str | None = None,
        customer_name: str | None = None,
        amount: str | None = None,
    ) -> AdminNotification:
        """
        Notify an admin that a new order has been created.
        """

        order_label = order_number or order_public_id

        message = f"New order {order_label} has been received."

        if customer_name:
            message += f" Customer: {customer_name}."

        if amount:
            message += f" Amount: ₹{amount}."

        return self.create_notification(
            admin_user_id=admin_user_id,
            notification_type="ORDER_CREATED",
            title="New Order Received",
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "order_number": order_number,
                "customer_name": customer_name,
                "amount": amount,
            },
        )

    # ---------------------------------------------------------
    # PAYMENT SUCCESS
    # ---------------------------------------------------------

    def notify_payment_success(
        self,
        *,
        admin_user_id: int,
        order_public_id: str,
        payment_public_id: str | None = None,
        order_number: str | None = None,
        amount: str | None = None,
    ) -> AdminNotification:
        """
        Notify an admin that payment succeeded.
        """

        order_label = order_number or order_public_id

        message = f"Payment received successfully for order {order_label}."

        if amount:
            message += f" Amount: ₹{amount}."

        return self.create_notification(
            admin_user_id=admin_user_id,
            notification_type="PAYMENT_SUCCESS",
            title="Payment Successful",
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "payment_public_id": payment_public_id,
                "order_number": order_number,
                "amount": amount,
            },
        )

    # ---------------------------------------------------------
    # PAYMENT FAILED
    # ---------------------------------------------------------

    def notify_payment_failed(
        self,
        *,
        admin_user_id: int,
        order_public_id: str,
        payment_public_id: str | None = None,
        order_number: str | None = None,
        reason: str | None = None,
    ) -> AdminNotification:
        """
        Notify an admin that payment failed.
        """

        order_label = order_number or order_public_id

        message = f"Payment failed for order {order_label}."

        if reason:
            message += f" Reason: {reason}."

        return self.create_notification(
            admin_user_id=admin_user_id,
            notification_type="PAYMENT_FAILED",
            title="Payment Failed",
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "payment_public_id": payment_public_id,
                "order_number": order_number,
                "reason": reason,
            },
        )

    # ---------------------------------------------------------
    # ORDER PAID
    # ---------------------------------------------------------

    def notify_order_paid(
        self,
        *,
        admin_user_id: int,
        order_public_id: str,
        order_number: str | None = None,
        amount: str | None = None,
    ) -> AdminNotification:
        """
        Notify an admin that an order has been marked as paid.
        """

        order_label = order_number or order_public_id

        message = f"Order {order_label} has been marked as paid."

        if amount:
            message += f" Amount: ₹{amount}."

        return self.create_notification(
            admin_user_id=admin_user_id,
            notification_type="ORDER_PAID",
            title="Order Paid",
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "order_number": order_number,
                "amount": amount,
            },
        )

    # ---------------------------------------------------------
    # ORDER STATUS CHANGE
    # ---------------------------------------------------------

    def notify_order_status_changed(
        self,
        *,
        admin_user_id: int,
        order_public_id: str,
        new_status: str,
        old_status: str | None = None,
        order_number: str | None = None,
    ) -> AdminNotification:
        """
        Notify an admin when an order status changes.
        """

        order_label = order_number or order_public_id

        message = f"Order {order_label} status changed to {new_status}."

        if old_status:
            message = (
                f"Order {order_label} status changed "
                f"from {old_status} to {new_status}."
            )

        notification_type = self._status_to_notification_type(new_status)

        title = self._status_to_title(new_status)

        return self.create_notification(
            admin_user_id=admin_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "order_number": order_number,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

    # ---------------------------------------------------------
    # LIST NOTIFICATIONS
    # ---------------------------------------------------------

    def get_notifications(
        self,
        *,
        admin_user_id: int,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[AdminNotification]:
        """
        Get notifications belonging to the current admin.
        """

        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        return self.repository.list_for_admin(
            admin_user_id=admin_user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )

    # ---------------------------------------------------------
    # GET SINGLE NOTIFICATION
    # ---------------------------------------------------------

    def get_notification(
        self,
        *,
        public_id: str,
        admin_user_id: int,
    ) -> AdminNotification | None:
        """
        Get one notification belonging to the current admin.
        """

        return self.repository.get_by_public_id(
            public_id=public_id,
            admin_user_id=admin_user_id,
        )

    # ---------------------------------------------------------
    # UNREAD COUNT
    # ---------------------------------------------------------

    def get_unread_count(
        self,
        *,
        admin_user_id: int,
    ) -> int:
        """
        Return unread notification count for an admin.
        """

        return self.repository.unread_count(admin_user_id)

    # ---------------------------------------------------------
    # MARK AS READ
    # ---------------------------------------------------------

    def mark_as_read(
        self,
        *,
        public_id: str,
        admin_user_id: int,
    ) -> AdminNotification | None:
        """
        Mark one notification as read.
        """

        notification = self.repository.get_by_public_id(
            public_id=public_id,
            admin_user_id=admin_user_id,
        )

        if notification is None:
            return None

        return self.repository.mark_as_read(
            notification=notification,
        )

    # ---------------------------------------------------------
    # MARK ALL AS READ
    # ---------------------------------------------------------

    def mark_all_as_read(
        self,
        *,
        admin_user_id: int,
    ) -> int:
        """
        Mark all unread notifications as read.
        """

        return self.repository.mark_all_as_read(
            admin_user_id=admin_user_id,
        )

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _status_to_notification_type(status: str) -> str:
        """
        Convert order status into notification type.
        """

        normalized_status = status.upper()

        mapping = {
            "PAID": "ORDER_PAID",
            "PROCESSING": "ORDER_PROCESSING",
            "SHIPPED": "ORDER_SHIPPED",
            "DELIVERED": "ORDER_DELIVERED",
            "CANCELLED": "ORDER_CANCELLED",
        }

        return mapping.get(
            normalized_status,
            "ORDER_STATUS_CHANGED",
        )

    @staticmethod
    def _status_to_title(status: str) -> str:
        """
        Convert order status into human-readable notification title.
        """

        normalized_status = status.upper()

        mapping = {
            "PAID": "Order Paid",
            "PROCESSING": "Order Processing",
            "SHIPPED": "Order Shipped",
            "DELIVERED": "Order Delivered",
            "CANCELLED": "Order Cancelled",
        }

        return mapping.get(
            normalized_status,
            "Order Status Updated",
        )