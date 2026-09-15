from uuid import uuid4

from fastapi import HTTPException

from app.modules.shop.cart.models.customer_cart import CustomerCart
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.cart.models.customer_cart_item import CustomerCartItem
from app.modules.shop.cart.models.guest_cart import GuestCart
from app.modules.shop.cart.services.guest_cart import GuestCartService
from app.modules.shop.cart.repositories.customer_cart import (
    CustomerCartRepository,
)
from app.modules.shop.catalog.models.product import Product


MAX_ITEM_QUANTITY = 100


class CustomerCartService:
    def __init__(
        self,
        repository: CustomerCartRepository,
    ):
        self.repository = repository

    # ===============================================================
    # GET / CREATE CART
    # ===============================================================

    def get_or_create_cart(
        self,
        customer_id: int,
    ) -> CustomerCart:
        return self.repository.get_or_create_cart(
            customer_id,
        )

    # ===============================================================
    # GET CART
    # ===============================================================

    def get_cart(
        self,
        customer_id: int,
    ) -> CustomerCart:
        return self.get_or_create_cart(
            customer_id,
        )

    # ===============================================================
    # ADD ITEM
    # ===============================================================

    def add_item(
        self,
        customer_id: int,
        product: Product,
        quantity: int,
    ) -> CustomerCart:

        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be greater than zero.",
            )

        if quantity > MAX_ITEM_QUANTITY:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum quantity is {MAX_ITEM_QUANTITY}.",
            )

        cart = self.get_or_create_cart(
            customer_id,
        )

        item = self.repository.get_item_by_product_id(
            cart_id=cart.id,
            product_id=product.id,
        )

        # -----------------------------------------------------------
        # Product does not exist in cart
        # -----------------------------------------------------------

        if item is None:
            item = CustomerCartItem(
                public_id=str(uuid4()),
                cart_id=cart.id,
                product_id=product.id,
                quantity=quantity,
            )

            self.repository.create_item(
                item,
            )

        # -----------------------------------------------------------
        # Product already exists
        # -----------------------------------------------------------

        else:
            new_quantity = item.quantity + quantity

            if new_quantity > MAX_ITEM_QUANTITY:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum quantity is {MAX_ITEM_QUANTITY}.",
                )

            item.quantity = new_quantity

        self.repository.save()

        return self.get_cart(
            customer_id,
        )

    # ===============================================================
    # UPDATE ITEM QUANTITY
    # ===============================================================

    def update_item_quantity(
        self,
        customer_id: int,
        item_public_id: str,
        quantity: int,
    ) -> CustomerCart:

        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be greater than zero.",
            )

        if quantity > MAX_ITEM_QUANTITY:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum quantity is {MAX_ITEM_QUANTITY}.",
            )

        cart = self.get_or_create_cart(
            customer_id,
        )

        item = self.repository.get_item_by_public_id(
            item_public_id=item_public_id,
            cart_id=cart.id,
        )

        if item is None:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found.",
            )

        item.quantity = quantity

        self.repository.save()

        return self.get_cart(
            customer_id,
        )

    # ===============================================================
    # REMOVE ITEM
    # ===============================================================

    def remove_item(
        self,
        customer_id: int,
        item_public_id: str,
    ) -> CustomerCart:

        cart = self.get_or_create_cart(
            customer_id,
        )

        item = self.repository.get_item_by_public_id(
            item_public_id=item_public_id,
            cart_id=cart.id,
        )

        if item is None:
            raise HTTPException(
                status_code=404,
                detail="Cart item not found.",
            )

        self.repository.delete_item(
            item,
        )

        self.repository.save()

        return self.get_cart(
            customer_id,
        )

    # ===============================================================
    # CLEAR CART
    # ===============================================================

    def clear_cart(
        self,
        customer_id: int,
    ) -> None:

        cart = self.get_or_create_cart(
            customer_id,
        )

        for item in list(cart.items):
            self.repository.delete_item(
                item,
            )

        self.repository.save()


        # ===============================================================
    # MERGE GUEST CART
    # ===============================================================

    def merge_guest_cart(
        self,
        customer_id: int,
        guest_cart: GuestCart,
    ) -> CustomerCart:
        """
        Merge all items from a guest cart into the
        authenticated customer's cart.

        If a product already exists in the customer cart,
        quantities are added together.

        Maximum quantity per product is 100.
        """

        customer_cart = self.get_or_create_cart(
            customer_id,
        )

        for guest_item in guest_cart.items:
            customer_item = self.repository.get_item_by_product_id(
                cart_id=customer_cart.id,
                product_id=guest_item.product_id,
            )

            # -------------------------------------------------------
            # Product doesn't exist in customer cart
            # -------------------------------------------------------

            if customer_item is None:
                quantity = min(
                    guest_item.quantity,
                    MAX_ITEM_QUANTITY,
                )

                customer_item = CustomerCartItem(
                    public_id=str(uuid4()),
                    cart_id=customer_cart.id,
                    product_id=guest_item.product_id,
                    quantity=quantity,
                )

                self.repository.create_item(
                    customer_item,
                )

            # -------------------------------------------------------
            # Product already exists
            # -------------------------------------------------------

            else:
                merged_quantity = (
                    customer_item.quantity
                    + guest_item.quantity
                )

                customer_item.quantity = min(
                    merged_quantity,
                    MAX_ITEM_QUANTITY,
                )

        self.repository.save()

        return self.get_cart(
            customer_id,
        )