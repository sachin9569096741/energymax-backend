from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.catalog.models.product import Product


class ProductRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Product | None:

        statement = (
            select(Product)
            .options(
                selectinload(Product.images)
            )
            .where(
                Product.public_id == public_id
            )
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY SLUG
    # ---------------------------------------------------------

    def get_by_slug(
        self,
        slug: str,
    ) -> Product | None:

        statement = (
            select(Product)
            .options(
                selectinload(Product.images)
            )
            .where(
                Product.slug == slug
            )
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        product_id: int,
    ) -> Product | None:

        statement = (
            select(Product)
            .options(
                selectinload(Product.images)
            )
            .where(
                Product.id == product_id
            )
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list(
        self,
        *,
        subcategory_id: int | None = None,
        is_active: bool | None = None,
        is_featured: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:

        statement = (
            select(Product)
            .options(
                selectinload(Product.images)
            )
        )

        count_statement = (
            select(func.count())
            .select_from(Product)
        )

        # -----------------------------------------------------
        # Filter by subcategory
        # -----------------------------------------------------

        if subcategory_id is not None:

            statement = statement.where(
                Product.subcategory_id == subcategory_id
            )

            count_statement = count_statement.where(
                Product.subcategory_id == subcategory_id
            )

        # -----------------------------------------------------
        # Filter by active status
        # -----------------------------------------------------

        if is_active is not None:

            statement = statement.where(
                Product.is_active == is_active
            )

            count_statement = count_statement.where(
                Product.is_active == is_active
            )

        # -----------------------------------------------------
        # Filter by featured status
        # -----------------------------------------------------

        if is_featured is not None:

            statement = statement.where(
                Product.is_featured == is_featured
            )

            count_statement = count_statement.where(
                Product.is_featured == is_featured
            )

        # -----------------------------------------------------
        # Ordering + pagination
        # -----------------------------------------------------

        statement = (
            statement
            .order_by(
                Product.display_order,
                Product.id,
            )
            .offset(offset)
            .limit(limit)
        )

        # -----------------------------------------------------
        # Execute
        # -----------------------------------------------------

        products = list(
            self.db.scalars(statement).all()
        )

        total = (
            self.db.scalar(count_statement)
            or 0
        )

        return products, total

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        product: Product,
    ) -> Product:

        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)

        return product

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        product: Product,
        data: dict,
    ) -> Product:

        for field, value in data.items():
            setattr(
                product,
                field,
                value,
            )

        self.db.flush()
        self.db.refresh(product)

        return product

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        product: Product,
    ) -> None:

        self.db.delete(product)
        self.db.flush()