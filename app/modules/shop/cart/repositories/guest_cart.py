from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.cart.models.guest_cart import GuestCart
from app.modules.shop.cart.models.guest_cart_item import GuestCartItem
from app.modules.shop.catalog.models.product import Product
from app.modules.shop.catalog.models.product_variant import ProductVariant


class GuestCartRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===============================================================
    # GUEST CART
    # ===============================================================

    def get_by_token_hash(
        self,
        token_hash: str,
    ) -> GuestCart | None:
        statement = (
            select(GuestCart)
            .where(
                GuestCart.token_hash == token_hash,
            )
            .options(
                selectinload(GuestCart.items)
                .selectinload(GuestCartItem.product),

                selectinload(GuestCart.items)
                .selectinload(GuestCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    def add_cart(
        self,
        cart: GuestCart,
    ) -> GuestCart:
        self.db.add(cart)
        self.db.flush()

        return cart

    # ===============================================================
    # PRODUCTS
    # ===============================================================

    def get_product_by_public_id(
        self,
        public_id: str,
    ) -> Product | None:
        statement = select(Product).where(
            Product.public_id == public_id,
        )

        return self.db.scalar(statement)

    # ===============================================================
    # VARIANTS
    # ===============================================================

    def get_variant_by_public_id(
        self,
        public_id: str,
    ) -> ProductVariant | None:
        statement = select(ProductVariant).where(
            ProductVariant.public_id == public_id,
        )

        return self.db.scalar(statement)

    # ===============================================================
    # GUEST CART ITEMS
    # ===============================================================

    def get_item_by_variant_id(
        self,
        cart_id: int,
        variant_id: int,
    ) -> GuestCartItem | None:
        statement = (
            select(GuestCartItem)
            .where(
                GuestCartItem.cart_id == cart_id,
                GuestCartItem.variant_id == variant_id,
            )
            .options(
                selectinload(GuestCartItem.product),
                selectinload(GuestCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    def get_item_by_public_id(
        self,
        item_public_id: str,
        cart_id: int,
    ) -> GuestCartItem | None:
        statement = (
            select(GuestCartItem)
            .where(
                GuestCartItem.public_id == item_public_id,
                GuestCartItem.cart_id == cart_id,
            )
            .options(
                selectinload(GuestCartItem.product),
                selectinload(GuestCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    # ===============================================================
    # DELETE ITEM
    # ===============================================================

    def delete_cart_item(
        self,
        item: GuestCartItem,
    ) -> None:
        self.db.delete(item)
        self.db.flush()

    # ===============================================================
    # CLEAR CART
    # ===============================================================

    def clear_cart_items(
        self,
        cart_id: int,
    ) -> None:
        statement = delete(
            GuestCartItem
        ).where(
            GuestCartItem.cart_id == cart_id,
        )

        self.db.execute(statement)
        self.db.flush()

    # ===============================================================
    # GUEST CART CONSUMPTION
    # ===============================================================

    def delete_cart(
        self,
        cart: GuestCart,
    ) -> None:
        self.db.delete(cart)
        self.db.flush()

    # ===============================================================
    # PERSISTENCE
    # ===============================================================

    def save(self) -> None:
        self.db.flush()