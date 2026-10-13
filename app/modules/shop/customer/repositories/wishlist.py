
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.catalog.models.product import Product
from app.modules.shop.customer.models.wishlist_item import WishlistItem


class WishlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_product(self, product_id: int) -> Product | None:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def get_item(
        self,
        customer_id: int,
        product_id: int,
    ) -> WishlistItem | None:
        stmt = (
            select(WishlistItem)
            .options(
                selectinload(WishlistItem.product)
                .selectinload(Product.images)
            )
            .where(
                WishlistItem.customer_id == customer_id,
                WishlistItem.product_id == product_id,
            )
        )
        return self.db.scalar(stmt)

    def list_items(self, customer_id: int) -> list[WishlistItem]:
        stmt = (
            select(WishlistItem)
            .join(WishlistItem.product)
            .options(
                selectinload(WishlistItem.product)
                .selectinload(Product.images)
            )
            .where(
                WishlistItem.customer_id == customer_id,
                Product.is_active.is_(True),
            )
            .order_by(WishlistItem.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def add_item(
        self,
        customer_id: int,
        product: Product,
    ) -> WishlistItem:
        item = WishlistItem(
            customer_id=customer_id,
            product_id=product.id,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def delete_item(self, item: WishlistItem) -> None:
        self.db.delete(item)
        self.db.flush()
