
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.shop.customer.repositories.wishlist import WishlistRepository


class WishlistService:
    def __init__(self, db: Session):
        self.repository = WishlistRepository(db)

    def get_wishlist(self, customer_id: int):
        return self.repository.list_items(customer_id)

    def add_product(self, customer_id: int, product_id: int):
        product = self.repository.get_active_product(product_id)

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or unavailable.",
            )

        existing = self.repository.get_item(customer_id, product_id)
        if existing is not None:
            return existing

        return self.repository.add_item(customer_id, product)

    def remove_product(self, customer_id: int, product_id: int) -> None:
        item = self.repository.get_item(customer_id, product_id)

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found in wishlist.",
            )

        self.repository.delete_item(item)
