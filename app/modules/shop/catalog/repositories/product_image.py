from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.product_image import ProductImage


class ProductImageRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_public_id(
        self,
        public_id: str,
    ) -> ProductImage | None:

        statement = select(ProductImage).where(
            ProductImage.public_id == public_id
        )

        return self.db.scalar(statement)

    def get_by_product_id(
        self,
        product_id: int,
        *,
        active_only: bool = True,
    ) -> list[ProductImage]:

        statement = select(ProductImage).where(
            ProductImage.product_id == product_id
        )

        if active_only:
            statement = statement.where(
                ProductImage.is_active.is_(True)
            )

        statement = statement.order_by(
            ProductImage.display_order,
            ProductImage.id,
        )

        return list(
            self.db.scalars(statement).all()
        )

    def count_by_product_id(
        self,
        product_id: int,
        *,
        active_only: bool = True,
    ) -> int:

        images = self.get_by_product_id(
            product_id,
            active_only=active_only,
        )

        return len(images)

    def create(
        self,
        image: ProductImage,
    ) -> ProductImage:

        self.db.add(image)
        self.db.flush()
        self.db.refresh(image)

        return image

    def update(
        self,
        image: ProductImage,
        data: dict,
    ) -> ProductImage:

        for field, value in data.items():
            setattr(image, field, value)

        self.db.flush()
        self.db.refresh(image)

        return image

    def delete(
        self,
        image: ProductImage,
    ) -> None:

        self.db.delete(image)
        self.db.flush()

    def clear_primary_for_product(
        self,
        product_id: int,
    ) -> None:

        images = self.get_by_product_id(
            product_id,
            active_only=True,
        )

        for image in images:
            if image.is_primary:
                image.is_primary = False

        self.db.flush()