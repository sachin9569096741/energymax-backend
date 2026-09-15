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
    total_amount = 0

    for item in cart.items:
        unit_price = item.product.price
        subtotal = unit_price * item.quantity

        items.append(
            GuestCartItemResponse(
                public_id=item.public_id,
                product_public_id=item.product.public_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )
        )

        total_items += item.quantity
        total_amount += subtotal

    return GuestCartResponse(
        public_id=cart.public_id,
        guest_cart_token=guest_cart_token,
        items=items,
        total_items=total_items,
        total_amount=total_amount,
        expires_at=cart.expires_at,
    )