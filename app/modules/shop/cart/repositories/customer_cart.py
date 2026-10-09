from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.cart.models.customer_cart import CustomerCart
from app.modules.shop.cart.models.customer_cart_item import CustomerCartItem
from app.modules.shop.catalog.models.product import Product
from app.modules.shop.catalog.models.product_variant import ProductVariant


class CustomerCartRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===============================================================
    # CUSTOMER CART
    # ===============================================================

    def get_by_customer_id(
        self,
        customer_id: int,
    ) -> CustomerCart | None:
        statement = (
            select(CustomerCart)
            .where(
                CustomerCart.customer_id == customer_id,
            )
            .options(
                selectinload(CustomerCart.items)
                .selectinload(CustomerCartItem.product),

                selectinload(CustomerCart.items)
                .selectinload(CustomerCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    def get_or_create_cart(
        self,
        customer_id: int,
    ) -> CustomerCart:
        cart = self.get_by_customer_id(
            customer_id,
        )

        if cart is not None:
            return cart

        cart = CustomerCart(
            customer_id=customer_id,
        )

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
    # CART ITEMS
    # ===============================================================

    def get_item_by_public_id(
        self,
        item_public_id: str,
        cart_id: int,
    ) -> CustomerCartItem | None:
        statement = (
            select(CustomerCartItem)
            .where(
                CustomerCartItem.public_id == item_public_id,
                CustomerCartItem.cart_id == cart_id,
            )
            .options(
                selectinload(CustomerCartItem.product),
                selectinload(CustomerCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    def get_item_by_product_id(
        self,
        cart_id: int,
        product_id: int,
    ) -> CustomerCartItem | None:
        """
        Legacy product-based lookup.

        Keep this temporarily for backward compatibility,
        but new cart logic should use get_item_by_variant_id().
        """

        statement = (
            select(CustomerCartItem)
            .where(
                CustomerCartItem.cart_id == cart_id,
                CustomerCartItem.product_id == product_id,
            )
            .options(
                selectinload(CustomerCartItem.product),
                selectinload(CustomerCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    def get_item_by_variant_id(
        self,
        cart_id: int,
        variant_id: int,
    ) -> CustomerCartItem | None:
        statement = (
            select(CustomerCartItem)
            .where(
                CustomerCartItem.cart_id == cart_id,
                CustomerCartItem.variant_id == variant_id,
            )
            .options(
                selectinload(CustomerCartItem.product),
                selectinload(CustomerCartItem.variant),
            )
        )

        return self.db.scalar(statement)

    # ===============================================================
    # CREATE ITEM
    # ===============================================================

    def create_item(
        self,
        item: CustomerCartItem,
    ) -> CustomerCartItem:
        self.db.add(item)
        self.db.flush()

        return item

    # ===============================================================
    # DELETE ITEM
    # ===============================================================

    def delete_item(
        self,
        item: CustomerCartItem,
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
            CustomerCartItem
        ).where(
            CustomerCartItem.cart_id == cart_id,
        )

        self.db.execute(statement)
        self.db.flush()

    # ===============================================================
    # PERSISTENCE
    # ===============================================================

    def save(self) -> None:
        self.db.flush()