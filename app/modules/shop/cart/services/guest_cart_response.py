from decimal import Decimal

from fastapi import HTTPException

from app.modules.shop.cart.models.guest_cart import GuestCart
from app.modules.shop.cart.schemas.guest_cart import (
    GuestCartItemResponse,
    GuestCartResponse,
)


def build_guest_cart_response(
    cart: GuestCart,
    guest_cart_token: str | None = None,
) -> GuestCartResponse:
    items = []

    total_items = 0
    total_amount = Decimal("0")

    for item in cart.items:

        # -----------------------------------------------------------
        # Variant is now mandatory for cart pricing
        # -----------------------------------------------------------

        if item.variant is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cart contains an item without a product variant. "
                    "Please remove the item and add it again."
                ),
            )

        # -----------------------------------------------------------
        # Variant price is the actual selling price
        # -----------------------------------------------------------

        unit_price = Decimal(
            str(item.variant.price)
        )

        subtotal = (
            unit_price * item.quantity
        )

        # -----------------------------------------------------------
        # Build item response
        # -----------------------------------------------------------

        items.append(
            GuestCartItemResponse(
                public_id=item.public_id,
                product_public_id=item.product.public_id,
                variant_public_id=item.variant.public_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )
        )

        total_items += item.quantity
        total_amount += subtotal

    # ---------------------------------------------------------------
    # Build cart response
    # ---------------------------------------------------------------

    return GuestCartResponse(
        public_id=cart.public_id,
        guest_cart_token=guest_cart_token,
        items=items,
        total_items=total_items,
        total_amount=total_amount,
        expires_at=cart.expires_at,
    )