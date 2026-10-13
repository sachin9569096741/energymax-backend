
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.catalog.models.product import Product
from app.modules.shop.customer.models.wishlist_item import WishlistItem
from app.modules.shop.customer.schemas.wishlist import (
    WishlistItemResponse,
    WishlistMessageResponse,
    WishlistProductResponse,
    WishlistResponse,
)
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.customer.services.wishlist import WishlistService


router = APIRouter(
    prefix="/customer/wishlist",
    tags=["Shop - Customer Wishlist"],
)


def serialize_item(item: WishlistItem) -> WishlistItemResponse:
    product: Product = item.product

    active_images = sorted(
        (image for image in product.images if image.is_active),
        key=lambda image: (not image.is_primary, image.display_order),
    )

    primary_image_url = (
        active_images[0].image_url if active_images else None
    )

    return WishlistItemResponse(
        public_id=item.public_id,
        created_at=item.created_at,
        product=WishlistProductResponse(
            public_id=product.public_id,
            name=product.name,
            slug=product.slug,
            price=product.price,
            mrp=product.mrp,
            primary_image_url=primary_image_url,
        ),
    )


@router.get("/my", response_model=WishlistResponse)
def get_my_wishlist(
    db: Session = Depends(get_db),
    current_customer=Depends(get_current_customer),
):
    items = WishlistService(db).get_wishlist(current_customer.id)

    return WishlistResponse(
        items=[serialize_item(item) for item in items],
        total=len(items),
    )


@router.post(
    "/my/items/{product_id}",
    response_model=WishlistMessageResponse,
    status_code=status.HTTP_200_OK,
)
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_customer=Depends(get_current_customer),
):
    try:
        item = WishlistService(db).add_product(
            customer_id=current_customer.id,
            product_id=product_id,
        )
        db.commit()
        db.refresh(item)

        return WishlistMessageResponse(
            message="Product is in your wishlist.",
            item=serialize_item(item),
        )
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/my/items/{product_id}",
    response_model=WishlistMessageResponse,
)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_customer=Depends(get_current_customer),
):
    try:
        WishlistService(db).remove_product(
            customer_id=current_customer.id,
            product_id=product_id,
        )
        db.commit()

        return WishlistMessageResponse(
            message="Product removed from wishlist.",
        )
    except Exception:
        db.rollback()
        raise
