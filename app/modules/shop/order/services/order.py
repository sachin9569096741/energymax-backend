from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.notifications.services.notification import (
    NotificationService,
)
from app.modules.shop.catalog.models.product_variant import ProductVariant
from app.modules.shop.checkout.repositories.checkout import CheckoutRepository
from app.modules.shop.inventory.models.warehouse import Warehouse
from app.modules.shop.inventory.services.inventory_reservation import (
    InventoryReservationService,
)
from app.modules.shop.inventory.models.inventory_reservation import (
    InventoryReservation,
)
from app.modules.shop.order.constants.status import (
    ORDER_STATUSES,
    ORDER_STATUS_LABELS,
    ORDER_STATUS_TRANSITIONS,
)
from app.modules.shop.order.models.order import Order
from app.modules.shop.order.models.order_item import OrderItem
from app.modules.shop.order.models.order_status_history import (
    OrderStatusHistory,
)
from app.modules.shop.order.repositories.order import OrderRepository


DEFAULT_WAREHOUSE_ID = 1


class OrderService:
    def __init__(self, db):
        self.db = db
        self.order_repository = OrderRepository(db)
        self.checkout_repository = CheckoutRepository(db)
        self.inventory_reservation_service = InventoryReservationService(db)

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
                detail="Selected delivery address is no longer available.",
            )

        # Ensure the configured default warehouse exists and is active.
        warehouse = self.db.scalar(
            select(Warehouse).where(
                Warehouse.id == DEFAULT_WAREHOUSE_ID,
                Warehouse.is_active.is_(True),
            )
        )

        if warehouse is None:
            raise HTTPException(
                status_code=500,
                detail="The default inventory warehouse is unavailable.",
            )

        # Validate all variants before creating the order.
        # The transaction must be rolled back by the route if any
        # validation or reservation fails.
        validated_items = []

        for checkout_item in checkout.items:
            if checkout_item.variant_id is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Checkout item '{checkout_item.product_name}' "
                        "does not have a selected variant."
                    ),
                )

            variant = self.db.scalar(
                select(ProductVariant).where(
                    ProductVariant.id == checkout_item.variant_id
                )
            )

            if variant is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The selected variant for "
                        f"'{checkout_item.product_name}' no longer exists."
                    ),
                )

            if variant.product_id != checkout_item.product_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The selected variant does not belong to "
                        f"'{checkout_item.product_name}'."
                    ),
                )

            if not variant.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The selected variant for "
                        f"'{checkout_item.product_name}' is inactive."
                    ),
                )

            quantity = int(checkout_item.quantity)

            if quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Order item quantity must be greater than zero.",
                )

            validated_items.append((checkout_item, variant, quantity))

        address_snapshot = self._build_address_snapshot(address)

        customer_name = customer.first_name

        if customer.last_name:
            customer_name = (
                f"{customer.first_name} {customer.last_name}"
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
            discount_amount=Decimal(str(checkout.discount_amount)),
            shipping_amount=Decimal(str(checkout.shipping_amount)),
            tax_amount=Decimal(str(checkout.tax_amount)),
            total_amount=Decimal(str(checkout.total_amount)),
        )

        self.order_repository.create(order)

        # Flush to ensure order.id exists before creating order items.
        self.db.flush()

        for checkout_item, variant, quantity in validated_items:
            order_item = OrderItem(
                public_id=str(uuid4()),
                order_id=order.id,
                product_id=checkout_item.product_id,
                variant_id=variant.id,
                product_name=checkout_item.product_name,
                unit_price=Decimal(str(checkout_item.unit_price)),
                quantity=quantity,
                subtotal=Decimal(str(checkout_item.subtotal)),
            )

            self.db.add(order_item)

        # Flush order items before creating reservations.
        self.db.flush()

        # Reserve inventory for each order item.
        # Use the checkout's expiry so the reservation and checkout
        # do not have conflicting expiry times.
        for checkout_item, variant, quantity in validated_items:
            self.inventory_reservation_service.create(
                warehouse_id=DEFAULT_WAREHOUSE_ID,
                variant_id=variant.id,
                quantity=Decimal(quantity),
                reference_type="ORDER",
                reference_id=order.public_id,
                idempotency_key=(
                    f"order:{order.public_id}:"
                    f"item:{checkout_item.public_id}"
                ),
                expires_at=checkout.expires_at,
            )

        checkout.status = "order_created"

        initial_status = OrderStatusHistory(
            order_id=order.id,
            status=order.status,
            note="Order created and inventory reserved.",
            changed_by="system",
        )

        self.db.add(initial_status)
        self.db.flush()

        # Preserve existing admin notifications.
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
        self.db.flush()

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

        Every successful status change creates an OrderStatusHistory record.
        """
        if new_status not in ORDER_STATUSES:
            raise ValueError(f"Invalid order status: {new_status}")

        current_status = order.status
        
        if current_status == new_status:
            return order
        
        allowed_statuses = ORDER_STATUS_TRANSITIONS.get(
            current_status,
            set(),
        )

        if new_status not in allowed_statuses:
            raise ValueError(
                "Invalid order status transition: "
                f"{current_status} -> {new_status}"
            )

        order.status = new_status

        history = OrderStatusHistory(
            order_id=order.id,
            status=new_status,
            note=note,
            changed_by=changed_by,
        )

        self.db.add(history)
        self.db.flush()

        return order

    def mark_order_paid(self, order):
        """Confirm reserved inventory and mark the order as paid."""

        reservations = self.db.scalars(
            select(InventoryReservation)
            .where(
                InventoryReservation.reference_type == "ORDER",
                InventoryReservation.reference_id == order.public_id,
            )
            .with_for_update()
        ).all()

        if not reservations:
            raise HTTPException(
                status_code=409,
                detail="No inventory reservations found for this order.",
            )

        for reservation in reservations:
            if reservation.status == "CONFIRMED":
                # Already deducted; don't deduct stock again.
                continue

            if reservation.status != "ACTIVE":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Cannot complete payment processing because "
                        f"an inventory reservation is {reservation.status}."
                    ),
                )

            self.inventory_reservation_service.confirm(
                reservation_id=reservation.id
            )

        if order.status != "paid":
            return self.update_order_status(
                order=order,
                new_status="paid",
                note="Payment received and inventory confirmed.",
                changed_by="system",
            )

        return order

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
            raise ValueError("Page size must be between 1 and 100.")

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


    def release_order_reservations(self, order):
        """Release active inventory reservations for an unpaid order."""

        if order.status == "paid":
            return

        reservations = self.db.scalars(
            select(InventoryReservation)
            .where(
                InventoryReservation.reference_type == "ORDER",
                InventoryReservation.reference_id == order.public_id,
            )
            .with_for_update()
        ).all()

        for reservation in reservations:
            if reservation.status == "ACTIVE":
                self.inventory_reservation_service.release(
                    reservation_id=reservation.id
                )


    def get_customer_orders(
        self,
        *,
        customer_id: int,
        page: int = 1,
        page_size: int = 10,
    ):
        return self.order_repository.list_customer_orders(
            customer_id=customer_id,
            page=page,
            page_size=page_size,
        )


