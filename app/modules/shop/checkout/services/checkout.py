
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.modules.shop.checkout.models.checkout import Checkout
from app.modules.shop.checkout.models.checkout_item import CheckoutItem
from app.modules.shop.checkout.repositories.checkout import CheckoutRepository
from app.modules.shop.cart.repositories.customer_cart import CustomerCartRepository


CHECKOUT_EXPIRY_MINUTES = 30


class CheckoutService:
    def __init__(self, db):
        self.db = db
        self.checkout_repository = CheckoutRepository(db)
        self.cart_repository = CustomerCartRepository(db)

    def create_checkout(self, customer_id: int) -> Checkout:
        cart = self.cart_repository.get_by_customer_id(customer_id)

        if cart is None:
            raise HTTPException(
                status_code=400,
                detail="Customer cart not found.",
            )

        if not cart.items:
            raise HTTPException(
                status_code=400,
                detail="Cannot create checkout with an empty cart.",
            )

        subtotal = Decimal("0.00")

        checkout = Checkout(
            public_id=str(uuid4()),
            customer_id=customer_id,
            cart_id=cart.id,
            selected_address_id=None,
            status="created",
            subtotal=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            shipping_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=CHECKOUT_EXPIRY_MINUTES)
            ),
        )

        self.checkout_repository.create(checkout)

        for cart_item in cart.items:
            product = cart_item.product
            variant = cart_item.variant

            if product is None:
                raise HTTPException(
                    status_code=400,
                    detail="A product in the cart is no longer available.",
                )

            if not product.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product '{product.name}' is no longer available.",
                )

            # A valid variant is required for variant-based inventory.
            if variant is None or cart_item.variant_id is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"A valid variant must be selected for "
                        f"product '{product.name}'. Please update your cart."
                    ),
                )

            # Ensure the selected variant belongs to this product.
            if variant.product_id != product.id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The selected variant does not belong to "
                        f"product '{product.name}'. Please update your cart."
                    ),
                )

            if not variant.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"The selected variant for '{product.name}' "
                        "is no longer available."
                    ),
                )

            quantity = cart_item.quantity

            if quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cart item quantity must be greater than zero.",
                )

            # Variant price is authoritative, not the parent product price.
            unit_price = Decimal(str(variant.price)).quantize(
                Decimal("0.01")
            )
            item_subtotal = unit_price * quantity

            variant_label = getattr(variant, "flavour", None)
            product_name = (
                f"{product.name} - {variant_label}"
                if variant_label
                else product.name
            )

            checkout_item = CheckoutItem(
                public_id=str(uuid4()),
                checkout_id=checkout.id,
                product_id=product.id,
                variant_id=variant.id,
                product_name=product_name,
                unit_price=unit_price,
                quantity=quantity,
                subtotal=item_subtotal,
            )

            self.db.add(checkout_item)
            subtotal += item_subtotal

        checkout.subtotal = subtotal
        checkout.total_amount = subtotal

        self.checkout_repository.save()

        return checkout

    def get_checkout(
        self,
        public_id: str,
        customer_id: int,
    ) -> Checkout:
        checkout = self.checkout_repository.get_by_public_id(
            public_id=public_id,
            customer_id=customer_id,
        )

        if checkout is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        self._validate_checkout_expiry(checkout)

        return checkout

    def select_address(
        self,
        checkout_public_id: str,
        customer_id: int,
        address_public_id: str,
    ) -> Checkout:
        checkout = self.checkout_repository.get_by_public_id(
            public_id=checkout_public_id,
            customer_id=customer_id,
        )

        if checkout is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        self._validate_checkout_expiry(checkout)

        if checkout.status != "created":
            raise HTTPException(
                status_code=400,
                detail="Checkout is not available for address selection.",
            )

        address = self.checkout_repository.get_customer_address(
            address_public_id=address_public_id,
            customer_id=customer_id,
        )

        if address is None:
            raise HTTPException(
                status_code=404,
                detail="Address not found.",
            )

        checkout.selected_address_id = address.id
        self.checkout_repository.save()

        return checkout

    def _validate_checkout_expiry(
        self,
        checkout: Checkout,
    ) -> None:
        now = datetime.now(timezone.utc)

        # Handle databases that return naive datetimes.
        expires_at = checkout.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            if checkout.status == "created":
                checkout.status = "expired"
                self.checkout_repository.save()

            raise HTTPException(
                status_code=400,
                detail="Checkout has expired.",
            )

    def confirm_checkout(
        self,
        checkout_public_id: str,
        customer_id: int,
    ) -> Checkout:
        checkout = self.checkout_repository.get_by_public_id(
            public_id=checkout_public_id,
            customer_id=customer_id,
        )

        if checkout is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        self._validate_checkout_expiry(checkout)

        if checkout.status != "created":
            raise HTTPException(
                status_code=400,
                detail="Checkout cannot be confirmed in its current state.",
            )

        if not checkout.items:
            raise HTTPException(
                status_code=400,
                detail="Cannot confirm checkout with no items.",
            )

        if checkout.selected_address_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Please select a delivery address before "
                    "confirming checkout."
                ),
            )

        address = self.checkout_repository.get_customer_address_by_id(
            address_id=checkout.selected_address_id,
            customer_id=customer_id,
        )

        if address is None:
            raise HTTPException(
                status_code=400,
                detail="Selected delivery address is no longer available.",
            )

        calculated_subtotal = sum(
            (
                Decimal(str(item.unit_price)) * item.quantity
                for item in checkout.items
            ),
            Decimal("0.00"),
        )

        if calculated_subtotal != checkout.subtotal:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Checkout pricing has changed. "
                    "Please create a new checkout."
                ),
            )

        calculated_total = (
            checkout.subtotal
            - checkout.discount_amount
            + checkout.shipping_amount
            + checkout.tax_amount
        )

        if calculated_total != checkout.total_amount:
            raise HTTPException(
                status_code=409,
                detail="Checkout total is invalid.",
            )

        checkout.status = "pricing_locked"
        self.checkout_repository.save()

        return checkout
