from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi import APIRouter, Depends
from app.modules.shop.cart.services.guest_cart import GuestCartService
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.cart.repositories.customer_cart import (
    CustomerCartRepository,
)
from app.modules.shop.cart.schemas.customer_cart import (
    CustomerCartItemAddRequest,
    CustomerCartItemUpdateRequest,
    CustomerCartItemResponse,
    CustomerCartResponse,
)
from app.modules.shop.cart.services.customer_cart import (
    CustomerCartService,
)
from app.modules.shop.catalog.models.product import Product
from app.modules.shop.customer.security.dependencies import (
    get_current_customer,
)
from app.modules.shop.customer.models.customer import Customer


router = APIRouter(
    prefix="/customer/cart",
    tags=["Shop - Customer Cart"],
)


def _build_cart_response(cart):
    items = []

    subtotal = Decimal("0")
    total_items = 0

    for item in cart.items:
        unit_price = Decimal(str(item.product.price))

        subtotal += unit_price * item.quantity
        total_items += item.quantity

        items.append(
            CustomerCartItemResponse(
                public_id=item.public_id,
                product_public_id=item.product.public_id,
                quantity=item.quantity,
                unit_price=unit_price,
            )
        )

    return CustomerCartResponse(
        public_id=cart.public_id,
        items=items,
        total_items=total_items,
        subtotal=subtotal,
        created_at=cart.created_at,
        updated_at=cart.updated_at,
    )


@router.get(
    "",
    response_model=CustomerCartResponse,
)
def get_customer_cart(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerCartRepository(db)
    service = CustomerCartService(repository)

    cart = service.get_cart(current_customer.id)

    db.commit()

    return _build_cart_response(cart)


@router.post(
    "/items",
    response_model=CustomerCartResponse,
)
def add_customer_cart_item(
    data: CustomerCartItemAddRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerCartRepository(db)
    service = CustomerCartService(repository)

    product = db.query(Product).filter(
        Product.public_id == data.product_public_id
    ).first()

    if product is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Product not found.",
        )

    cart = service.add_item(
        customer_id=current_customer.id,
        product=product,
        quantity=data.quantity,
    )

    db.commit()

    return _build_cart_response(cart)


@router.patch(
    "/items/{item_public_id}",
    response_model=CustomerCartResponse,
)
def update_customer_cart_item(
    item_public_id: str,
    data: CustomerCartItemUpdateRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerCartRepository(db)
    service = CustomerCartService(repository)

    cart = service.update_item_quantity(
        customer_id=current_customer.id,
        item_public_id=item_public_id,
        quantity=data.quantity,
    )

    db.commit()

    return _build_cart_response(cart)


@router.delete(
    "/items/{item_public_id}",
    response_model=CustomerCartResponse,
)
def remove_customer_cart_item(
    item_public_id: str,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerCartRepository(db)
    service = CustomerCartService(repository)

    cart = service.remove_item(
        customer_id=current_customer.id,
        item_public_id=item_public_id,
    )

    db.commit()

    return _build_cart_response(cart)


@router.delete(
    "",
)
def clear_customer_cart(
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerCartRepository(db)
    service = CustomerCartService(repository)

    service.clear_cart(current_customer.id)

    db.commit()

    return {
        "message": "Customer cart cleared successfully."
    }


# ===============================================================
# MERGE GUEST CART
# ===============================================================

@router.post(
    "/merge",
    response_model=CustomerCartResponse,
)
def merge_guest_cart(
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if not x_guest_cart_token:
        raise HTTPException(
            status_code=400,
            detail="Guest cart token is required.",
        )

    guest_cart_service = GuestCartService(db)

    try:
        # -----------------------------------------------------------
        # Get and validate guest cart
        # -----------------------------------------------------------

        guest_cart = guest_cart_service.get_cart(
            x_guest_cart_token,
        )

        # -----------------------------------------------------------
        # Merge guest cart into customer cart
        # -----------------------------------------------------------

        customer_cart_repository = CustomerCartRepository(db)

        customer_cart_service = CustomerCartService(
            customer_cart_repository,
        )

        customer_cart = customer_cart_service.merge_guest_cart(
            customer_id=current_customer.id,
            guest_cart=guest_cart,
        )

        # -----------------------------------------------------------
        # Consume guest cart
        # -----------------------------------------------------------

        guest_cart_service.consume_cart(
            guest_cart,
        )

        # -----------------------------------------------------------
        # Commit everything together
        # -----------------------------------------------------------

        db.commit()

        # Refresh merged cart with product relationships
        customer_cart = customer_cart_service.get_cart(
            current_customer.id,
        )

        return _build_cart_response(
            customer_cart,
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )