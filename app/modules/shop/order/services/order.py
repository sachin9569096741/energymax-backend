from uuid import uuid4
from decimal import Decimal

from fastapi import HTTPException

from app.modules.shop.checkout.repositories.checkout import CheckoutRepository
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
                detail="Order can only be created from a pricing-locked checkout.",
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

        for checkout_item in checkout.items:
            order_item = OrderItem(
                public_id=str(uuid4()),
                order_id=order.id,
                product_id=checkout_item.product_id,
                product_name=checkout_item.product_name,
                unit_price=Decimal(str(checkout_item.unit_price)),
                quantity=checkout_item.quantity,
                subtotal=Decimal(str(checkout_item.subtotal)),
            )

            self.db.add(order_item)

        checkout.status = "order_created"

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

    def mark_order_paid(self, order: Order) -> None:
        if order.status == "paid":
            return

        if order.status != "pending_payment":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Order cannot be marked as paid from "
                    f"'{order.status}' status."
                ),
            )

        order.status = "paid"
        self.order_repository.save()