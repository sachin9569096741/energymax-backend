import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.shop.cart.models.guest_cart import GuestCart
from app.modules.shop.cart.models.guest_cart_item import GuestCartItem
from app.modules.shop.cart.repositories.guest_cart import GuestCartRepository


GUEST_CART_EXPIRY_DAYS = 30
MAX_ITEM_QUANTITY = 100


class GuestCartService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = GuestCartRepository(db)

    # ===============================================================
    # TOKEN
    # ===============================================================

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    # ===============================================================
    # EXPIRY
    # ===============================================================

    @staticmethod
    def get_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            days=GUEST_CART_EXPIRY_DAYS
        )

    # ===============================================================
    # CREATE CART
    # ===============================================================

    def create_cart(self) -> tuple[GuestCart, str]:
        token = self.generate_token()

        cart = GuestCart(
            token_hash=self.hash_token(token),
            expires_at=self.get_expiry(),
        )

        self.repository.add_cart(cart)

        return cart, token

    # ===============================================================
    # GET CART
    # ===============================================================

    def get_cart(
        self,
        token: str,
    ) -> GuestCart:
        token_hash = self.hash_token(token)

        cart = self.repository.get_by_token_hash(
            token_hash
        )

        if cart is None:
            raise ValueError(
                "Invalid guest cart token."
            )

        if cart.expires_at <= datetime.now(timezone.utc):
            raise ValueError(
                "Guest cart has expired."
            )

        return cart

    # ===============================================================
    # ADD ITEM
    # ===============================================================

    def add_item(
        self,
        token: str,
        product_public_id: str,
        quantity: int,
    ) -> GuestCart:
        cart = self.get_cart(token)

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if quantity > MAX_ITEM_QUANTITY:
            raise ValueError(
                f"Maximum quantity is {MAX_ITEM_QUANTITY}."
            )

        product = self.repository.get_product_by_public_id(
            product_public_id
        )

        if product is None:
            raise ValueError(
                "Product not found."
            )

        if not product.is_active:
            raise ValueError(
                "This product is not available."
            )

        existing_item = next(
            (
                item
                for item in cart.items
                if item.product_id == product.id
            ),
            None,
        )

        if existing_item is not None:
            new_quantity = (
                existing_item.quantity + quantity
            )

            if new_quantity > MAX_ITEM_QUANTITY:
                raise ValueError(
                    f"Maximum quantity is {MAX_ITEM_QUANTITY}."
                )

            existing_item.quantity = new_quantity

        else:
            item = GuestCartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
            )

            cart.items.append(item)

        self.repository.save()

        return cart

    # ===============================================================
    # UPDATE ITEM
    # ===============================================================

    def update_item(
        self,
        token: str,
        item_public_id: str,
        quantity: int,
    ) -> GuestCart:
        cart = self.get_cart(token)

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if quantity > MAX_ITEM_QUANTITY:
            raise ValueError(
                f"Maximum quantity is {MAX_ITEM_QUANTITY}."
            )

        item = next(
            (
                item
                for item in cart.items
                if item.public_id == item_public_id
            ),
            None,
        )

        if item is None:
            raise ValueError(
                "Cart item not found."
            )

        item.quantity = quantity

        self.repository.save()

        return cart

    # ===============================================================
    # REMOVE ITEM
    # ===============================================================

    def remove_item(
        self,
        token: str,
        item_public_id: str,
    ) -> GuestCart:
        cart = self.get_cart(token)

        item = next(
            (
                item
                for item in cart.items
                if item.public_id == item_public_id
            ),
            None,
        )

        if item is None:
            raise ValueError(
                "Cart item not found."
            )

        cart.items.remove(item)

        self.repository.save()

        return cart

    # ===============================================================
    # CLEAR CART
    # ===============================================================

    def clear_cart(
        self,
        token: str,
    ) -> None:
        cart = self.get_cart(token)

        cart.items.clear()

        self.repository.save()

    # ===============================================================
    # CONSUME CART
    # ===============================================================

    def consume_cart(
        self,
        cart: GuestCart,
    ) -> None:
        """
        Permanently remove a guest cart after
        its contents have been successfully merged.
        """

        self.repository.delete_cart(cart)

        self.repository.save()