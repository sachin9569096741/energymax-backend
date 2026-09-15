from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.shop.cart.models.customer_cart import CustomerCart
from app.modules.shop.cart.models.customer_cart_item import CustomerCartItem


class CustomerCartRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===============================================================
    # CART
    # ===============================================================

    def get_cart_by_customer_id(
        self,
        customer_id: int,
    ) -> CustomerCart | None:
        statement = (
            select(CustomerCart)
            .options(
                joinedload(CustomerCart.items)
                .joinedload(CustomerCartItem.product)
            )
            .where(
                CustomerCart.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_cart_by_public_id(
        self,
        public_id: str,
        customer_id: int,
    ) -> CustomerCart | None:
        statement = (
            select(CustomerCart)
            .options(
                joinedload(CustomerCart.items)
                .joinedload(CustomerCartItem.product)
            )
            .where(
                CustomerCart.public_id == public_id,
                CustomerCart.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def create_cart(
        self,
        cart: CustomerCart,
    ) -> CustomerCart:
        self.db.add(cart)
        self.db.flush()

        return cart

    def get_or_create_cart(
        self,
        customer_id: int,
    ) -> CustomerCart:
        cart = self.get_cart_by_customer_id(
            customer_id,
        )

        if cart is not None:
            return cart

        cart = CustomerCart(
            public_id=str(uuid4()),
            customer_id=customer_id,
        )

        return self.create_cart(cart)

    # ===============================================================
    # CART ITEMS
    # ===============================================================

    def get_item_by_product_id(
        self,
        cart_id: int,
        product_id: int,
    ) -> CustomerCartItem | None:
        statement = select(CustomerCartItem).where(
            CustomerCartItem.cart_id == cart_id,
            CustomerCartItem.product_id == product_id,
        )

        return self.db.scalar(statement)

    def get_item_by_public_id(
        self,
        item_public_id: str,
        cart_id: int,
    ) -> CustomerCartItem | None:
        statement = select(CustomerCartItem).where(
            CustomerCartItem.public_id == item_public_id,
            CustomerCartItem.cart_id == cart_id,
        )

        return self.db.scalar(statement)

    def create_item(
        self,
        item: CustomerCartItem,
    ) -> CustomerCartItem:
        self.db.add(item)
        self.db.flush()

        return item

    def delete_item(
        self,
        item: CustomerCartItem,
    ) -> None:
        self.db.delete(item)
        self.db.flush()

    # ===============================================================
    # PERSISTENCE
    # ===============================================================

    def save(self) -> None:
        self.db.flush()