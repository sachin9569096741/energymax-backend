from uuid import uuid4
from decimal import Decimal

from fastapi import HTTPException

from app.modules.shop.order.constants.status import (
    ORDER_STATUSES,
    ORDER_STATUS_TRANSITIONS,
)
from sqlalchemy import select

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.notifications.services.notification import (
    NotificationService,
)

from app.modules.shop.order.models.order_status_history import (
    OrderStatusHistory,
)
from app.modules.shop.order.constants.status import (
    ORDER_STATUS_LABELS,
)
from app.modules.shop.checkout.repositories.checkout import (
    CheckoutRepository,
)
from app.modules.shop.order.models.order import Order
from app.modules.shop.order.models.order_item import OrderItem
from app.modules.shop.order.repositories.order import OrderRepository


class OrderService:
    def __init__(self, db):
        self.db = db
        self.order_repository = OrderRepository(db)
        self.checkout_repository = CheckoutRepository(db)

    def create_order(
        self,
        checkout_public_id: str,
        customer,
    ) -> Order:
        checkout = self.checkout_repository.get_by_public_id(
            public_id=checkout_public_id,
            customer_id=customer.id,
        )

        if checkout is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        existing_order = self.order_repository.get_by_checkout_id(
            checkout.id
        )

        if existing_order is not None:
            raise HTTPException(
                status_code=409,
                detail="An order already exists for this checkout.",
            )

        if checkout.status != "pricing_locked":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Order can only be created from "
                    "a pricing-locked checkout."
                ),
            )

        if not checkout.items:
            raise HTTPException(
                status_code=400,
                detail="Cannot create order without items.",
            )

        if checkout.selected_address_id is None:
            raise HTTPException(
                status_code=400,
                detail="Checkout does not have a delivery address.",
            )

        address = self.checkout_repository.get_customer_address_by_id(
            address_id=checkout.selected_address_id,
            customer_id=customer.id,
        )

        if address is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected delivery address is "
                    "no longer available."
                ),
            )

        address_snapshot = self._build_address_snapshot(address)

        customer_name = customer.first_name

        if customer.last_name:
            customer_name = (
                f"{customer.first_name} "
                f"{customer.last_name}"
            )

        order = Order(
            public_id=str(uuid4()),
            order_number=self._generate_order_number(),
            customer_id=customer.id,
            checkout_id=checkout.id,
            status="pending_payment",
            customer_name=customer_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            shipping_address_snapshot=address_snapshot,
            subtotal=Decimal(str(checkout.subtotal)),
            discount_amount=Decimal(
                str(checkout.discount_amount)
            ),
            shipping_amount=Decimal(
                str(checkout.shipping_amount)
            ),
            tax_amount=Decimal(
                str(checkout.tax_amount)
            ),
            total_amount=Decimal(
                str(checkout.total_amount)
            ),
        )

        self.order_repository.create(order)

        for checkout_item in checkout.items:
            order_item = OrderItem(
                public_id=str(uuid4()),
                order_id=order.id,
                product_id=checkout_item.product_id,
                product_name=checkout_item.product_name,
                unit_price=Decimal(
                    str(checkout_item.unit_price)
                ),
                quantity=checkout_item.quantity,
                subtotal=Decimal(
                    str(checkout_item.subtotal)
                ),
            )

            self.db.add(order_item)

        checkout.status = "order_created"

        initial_status = OrderStatusHistory(
            order_id=order.id,
            status=order.status,
            note="Order created.",
            changed_by="system",
        )

        self.db.add(initial_status)

        self.order_repository.save()

        notification_service = NotificationService(self.db)
        active_admins = self.db.scalars(
            select(AdminUser).where(
                AdminUser.is_active.is_(True)
            )
        ).all()

        for admin in active_admins:
            notification_service.notify_order_created(
                admin_user_id=admin.id,

                order_public_id=order.public_id,
                order_number=order.order_number,
                customer_name=customer_name,
                amount=str(order.total_amount),



            )
        self.order_repository.save()


        return order

    @staticmethod
    def _generate_order_number() -> str:
        return f"EMX-{uuid4().hex[:12].upper()}"

    @staticmethod
    def _build_address_snapshot(address) -> dict:
        return {
            "public_id": address.public_id,
            "label": address.label,
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "address_line1": address.address_line1,
            "address_line2": address.address_line2,
            "landmark": address.landmark,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        }

    def update_order_status(
        self,
        order,
        new_status: str,
        note: str | None = None,
        changed_by: str | None = None,
    ):
        """
        Update an order status using the allowed transition rules.

        Every successful status change creates an
        OrderStatusHistory record.
        """

        # Validate requested status.
        if new_status not in ORDER_STATUSES:
            raise ValueError(
                f"Invalid order status: {new_status}"
            )

        current_status = order.status

        # No-op if the order already has this status.
        if current_status == new_status:
            return order

        # Get allowed next statuses.
        allowed_statuses = ORDER_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )

        # Reject invalid transition.
        if new_status not in allowed_statuses:
            raise ValueError(
                "Invalid order status transition: "
                f"{current_status} -> {new_status}"
            )

        # Update order status.
        order.status = new_status

        # Create tracking history entry.
        history = OrderStatusHistory(
            order_id=order.id,
            status=new_status,
            note=note,
            changed_by=changed_by,
        )

        self.db.add(history)

        # Flush changes without committing.
        self.db.flush()

        return order

    def mark_order_paid(self, order):
        """
        Mark an order as paid using the central
        status transition system.
        """

        return self.update_order_status(
            order=order,
            new_status="paid",
            note="Payment received.",
            changed_by="system",
        )

    def get_order_tracking(
        self,
        order_public_id: str,
        customer_id: int,
    ):
        order = self.order_repository.get_by_public_id(
            public_id=order_public_id,
            customer_id=customer_id,
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        return order

    def get_order_tracking_by_number(
        self,
        order_number: str,
    ):
        order = self.order_repository.get_by_order_number_for_tracking(
            order_number=order_number.strip().upper(),
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
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
    def list_admin_orders(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        search: str | None = None,
    ):
        if page < 1:
            raise ValueError("Page must be greater than 0.")

        if page_size < 1 or page_size > 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        orders, total = self.order_repository.list_admin_orders(
            page=page,
            page_size=page_size,
            status=status,
            search=search,
        )

        total_pages = (
            (total + page_size - 1) // page_size
            if total
            else 0
        )

        return {
            "items": orders,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }
