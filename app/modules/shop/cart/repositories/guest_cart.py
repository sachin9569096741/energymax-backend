from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.cart.models.guest_cart import GuestCart
from app.modules.shop.cart.models.guest_cart_item import GuestCartItem
from app.modules.shop.catalog.models.product import Product


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
                .selectinload(GuestCartItem.product)
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
    # GUEST CART ITEMS
    # ===============================================================

    def delete_cart_item(
        self,
        item: GuestCartItem,
    ) -> None:
        self.db.delete(item)
        self.db.flush()

    def clear_cart_items(
        self,
        cart_id: int,
    ) -> None:
        statement = delete(GuestCartItem).where(
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