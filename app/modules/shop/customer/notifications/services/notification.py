from sqlalchemy.orm import Session

from app.modules.shop.customer.notifications.models.customer_notification import (
    CustomerNotification,
)
from app.modules.shop.customer.notifications.repositories.notification import (
    CustomerNotificationRepository,
)


class CustomerNotificationService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = CustomerNotificationRepository(db)

    # =========================================================
    # CREATE
    # =========================================================

    def create_notification(
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

        return self.repository.create(
            customer_id=customer_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            data=data,
        )

    # =========================================================
    # ORDER CONFIRMED
    # =========================================================

    def notify_order_confirmed(
        self,
        *,
        customer_id: int,
        order_public_id: str,
        order_number: str | None = None,
    ) -> CustomerNotification:

        order_label = order_number or order_public_id

        return self.create_notification(
            customer_id=customer_id,
            notification_type="ORDER_CONFIRMED",
            title="Order Confirmed",
            message=(
                f"Your order {order_label} "
                "has been confirmed successfully."
            ),
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "order_number": order_number,
            },
        )

    # =========================================================
    # PAYMENT SUCCESS
    # =========================================================

    def notify_payment_success(
        self,
        *,
        customer_id: int,
        order_public_id: str,
        payment_public_id: str | None = None,
        order_number: str | None = None,
        amount: str | None = None,
    ) -> CustomerNotification:

        order_label = order_number or order_public_id

        message = (
            f"Payment for order {order_label} "
            "was successful."
        )

        if amount:
            message += f" Amount: ₹{amount}."

        return self.create_notification(
            customer_id=customer_id,
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

    # =========================================================
    # PAYMENT FAILED
    # =========================================================

    def notify_payment_failed(
        self,
        *,
        customer_id: int,
        order_public_id: str,
        payment_public_id: str | None = None,
        order_number: str | None = None,
    ) -> CustomerNotification:

        order_label = order_number or order_public_id

        return self.create_notification(
            customer_id=customer_id,
            notification_type="PAYMENT_FAILED",
            title="Payment Failed",
            message=(
                f"Payment for order {order_label} "
                "could not be completed. "
                "Please try again."
            ),
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "payment_public_id": payment_public_id,
                "order_number": order_number,
            },
        )

    # =========================================================
    # ORDER STATUS
    # =========================================================

    def notify_order_status_changed(
        self,
        *,
        customer_id: int,
        order_public_id: str,
        order_number: str | None,
        new_status: str,
    ) -> CustomerNotification:

        order_label = order_number or order_public_id

        status = new_status.lower()

        status_map = {
            "processing": (
                "ORDER_PROCESSING",
                "Order Processing",
                f"Your order {order_label} is now being processed.",
            ),
            "shipped": (
                "ORDER_SHIPPED",
                "Order Shipped",
                f"Your order {order_label} has been shipped.",
            ),
            "delivered": (
                "ORDER_DELIVERED",
                "Order Delivered",
                f"Your order {order_label} has been delivered successfully.",
            ),
            "cancelled": (
                "ORDER_CANCELLED",
                "Order Cancelled",
                f"Your order {order_label} has been cancelled.",
            ),
        }

        (
            notification_type,
            title,
            message,
        ) = status_map.get(
            status,
            (
                "ORDER_STATUS_CHANGED",
                "Order Status Updated",
                f"The status of your order {order_label} has been updated.",
            ),
        )

        return self.create_notification(
            customer_id=customer_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type="ORDER",
            entity_public_id=order_public_id,
            data={
                "order_public_id": order_public_id,
                "order_number": order_number,
                "status": new_status,
            },
        )

    # =========================================================
    # LIST
    # =========================================================

    def list_notifications(
        self,
        *,
        customer_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CustomerNotification], int]:

        items = self.repository.list_for_customer(
            customer_id=customer_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

        total = self.repository.count_for_customer(
            customer_id=customer_id,
            unread_only=unread_only,
        )

        return items, total

    # =========================================================
    # GET ONE
    # =========================================================

    def get_notification(
        self,
        *,
        customer_id: int,
        public_id: str,
    ) -> CustomerNotification | None:

        return self.repository.get_by_public_id(
            public_id=public_id,
            customer_id=customer_id,
        )

    # =========================================================
    # UNREAD COUNT
    # =========================================================

    def get_unread_count(
        self,
        *,
        customer_id: int,
    ) -> int:

        return self.repository.unread_count(
            customer_id=customer_id,
        )

    # =========================================================
    # MARK ONE READ
    # =========================================================

    def mark_as_read(
        self,
        *,
        customer_id: int,
        public_id: str,
    ) -> CustomerNotification | None:

        notification = self.repository.get_by_public_id(
            public_id=public_id,
            customer_id=customer_id,
        )

        if notification is None:
            return None

        return self.repository.mark_as_read(
            notification
        )

    # =========================================================
    # MARK ALL READ
    # =========================================================

    def mark_all_as_read(
        self,
        *,
        customer_id: int,
    ) -> int:

        return self.repository.mark_all_as_read(
            customer_id=customer_id,
        )