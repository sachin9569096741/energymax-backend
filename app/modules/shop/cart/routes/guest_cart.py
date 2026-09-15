from fastapi import APIRouter, Header, HTTPException, Response, status
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.session import get_db
from app.modules.shop.cart.schemas.guest_cart import (
    GuestCartItemAdd,
    GuestCartItemUpdate,
    GuestCartResponse,
)
from app.modules.shop.cart.services.guest_cart import (
    GuestCartService,
)
from app.modules.shop.cart.services.guest_cart_response import (
    build_guest_cart_response,
)


router = APIRouter(
    prefix="/cart",
    tags=["Shop - Cart"],
)


@router.get(
    "",
    response_model=GuestCartResponse,
)
def get_cart(
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    db: Session = Depends(get_db),
):
    service = GuestCartService(db)

    # No token → create a new guest cart.
    if not x_guest_cart_token:
        cart, token = service.create_cart()

        return build_guest_cart_response(
            cart=cart,
            guest_cart_token=token,
        )

    try:
        cart = service.get_cart(
            token=x_guest_cart_token
        )

        return build_guest_cart_response(
            cart=cart,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post(
    "/items",
    response_model=GuestCartResponse,
    status_code=status.HTTP_200_OK,
)
def add_cart_item(
    payload: GuestCartItemAdd,
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    db: Session = Depends(get_db),
):
    if not x_guest_cart_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest cart token is required.",
        )

    service = GuestCartService(db)

    try:
        cart = service.add_item(
            token=x_guest_cart_token,
            product_public_id=payload.product_public_id,
            quantity=payload.quantity,
        )

        return build_guest_cart_response(
            cart=cart,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.patch(
    "/items/{item_public_id}",
    response_model=GuestCartResponse,
)
def update_cart_item(
    item_public_id: str,
    payload: GuestCartItemUpdate,
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    db: Session = Depends(get_db),
):
    if not x_guest_cart_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest cart token is required.",
        )

    service = GuestCartService(db)

    try:
        cart = service.update_item(
            token=x_guest_cart_token,
            item_public_id=item_public_id,
            quantity=payload.quantity,
        )

        return build_guest_cart_response(
            cart=cart,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/items/{item_public_id}",
    response_model=GuestCartResponse,
)
def remove_cart_item(
    item_public_id: str,
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    db: Session = Depends(get_db),
):
    if not x_guest_cart_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest cart token is required.",
        )

    service = GuestCartService(db)

    try:
        cart = service.remove_item(
            token=x_guest_cart_token,
            item_public_id=item_public_id,
        )

        return build_guest_cart_response(
            cart=cart,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_cart(
    x_guest_cart_token: str | None = Header(
        default=None,
        alias="X-Guest-Cart-Token",
    ),
    db: Session = Depends(get_db),
):
    if not x_guest_cart_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest cart token is required.",
        )

    service = GuestCartService(db)

    try:
        service.clear_cart(
            token=x_guest_cart_token
        )

        return Response(
            status_code=status.HTTP_204_NO_CONTENT
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )