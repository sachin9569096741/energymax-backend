from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.product_variant import ProductVariant


class VariantRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> ProductVariant | None:

        statement = (
            select(ProductVariant)
            .where(
                ProductVariant.public_id == public_id
            )
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY SKU
    # ---------------------------------------------------------

    def get_by_sku(
        self,
        sku: str,
    ) -> ProductVariant | None:

        statement = (
            select(ProductVariant)
            .where(
                ProductVariant.sku == sku
            )
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PRODUCT
    # ---------------------------------------------------------

    def list_by_product(
        self,
        product_id: int,
        *,
        active_only: bool = False,
    ) -> list[ProductVariant]:

        statement = (
            select(ProductVariant)
            .where(
                ProductVariant.product_id == product_id
            )
            .order_by(
                ProductVariant.id
            )
        )

        if active_only:
            statement = statement.where(
                ProductVariant.is_active.is_(True)
            )

        return list(
            self.db.scalars(statement).all()
        )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        variant: ProductVariant,
    ) -> ProductVariant:

        self.db.add(variant)
        self.db.flush()
        self.db.refresh(variant)

        return variant

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        variant: ProductVariant,
        data: dict,
    ) -> ProductVariant:

        for field, value in data.items():
            setattr(
                variant,
                field,
                value,
            )

        self.db.flush()
        self.db.refresh(variant)

        return variant

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        variant: ProductVariant,
    ) -> None:

        self.db.delete(variant)
        self.db.flush()