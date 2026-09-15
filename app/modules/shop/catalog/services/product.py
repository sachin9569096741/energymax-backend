from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.product import Product
from app.modules.shop.catalog.repositories.product import ProductRepository
from app.modules.shop.catalog.repositories.subcategory import (
    SubcategoryRepository,
)


class ProductService:

    def __init__(self, db: Session):
        self.product_repository = ProductRepository(db)
        self.subcategory_repository = SubcategoryRepository(db)

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_product(
        self,
        *,
        subcategory_id: int,
        name: str,
        slug: str,
        short_description: str | None = None,
        description: str | None = None,
        brand_name: str | None = None,
        price: Decimal,
        mrp: Decimal | None = None,
        cost_price: Decimal | None = None,
        seo_title: str | None = None,
        seo_description: str | None = None,
        is_active: bool = True,
        is_featured: bool = False,
        display_order: int = 0,
    ) -> Product:

        # Validate subcategory
        subcategory = (
            self.subcategory_repository.get_active_by_id(
                subcategory_id
            )
        )

        if subcategory is None:
            raise ValueError(
                f"Active subcategory with id "
                f"'{subcategory_id}' does not exist."
            )

        # Validate slug uniqueness
        existing_product = (
            self.product_repository.get_by_slug(slug)
        )

        if existing_product is not None:
            raise ValueError(
                f"Product with slug '{slug}' already exists."
            )

                # --------------------------------------------------------------
        # Validate pricing
        # --------------------------------------------------------------

        if mrp is not None and price > mrp:
            raise ValueError(
                "Product price cannot be greater than MRP."
            )

        product = Product(
            subcategory_id=subcategory_id,
            name=name,
            slug=slug,
            short_description=short_description,
            description=description,
            brand_name=brand_name,
            price=price,
            mrp=mrp,
            cost_price=cost_price,
            seo_title=seo_title,
            seo_description=seo_description,
            is_active=is_active,
            is_featured=is_featured,
            display_order=display_order,
        )

        return self.product_repository.create(product)

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get_product(
        self,
        *,
        public_id: str,
    ) -> Product:

        product = (
            self.product_repository.get_by_public_id(
                public_id
            )
        )

        if product is None:
            raise ValueError(
                f"Product with public_id "
                f"'{public_id}' does not exist."
            )

        return product

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list_products(
        self,
        *,
        subcategory_id: int | None = None,
        is_active: bool | None = True,
        is_featured: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:

        if page < 1:
            raise ValueError(
                "Page must be greater than 0."
            )

        if page_size < 1 or page_size > 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        offset = (page - 1) * page_size

        return self.product_repository.list(
            subcategory_id=subcategory_id,
            is_active=is_active,
            is_featured=is_featured,
            offset=offset,
            limit=page_size,
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_product(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> Product:

        product = (
            self.product_repository.get_by_public_id(
                public_id
            )
        )

        if product is None:
            raise ValueError(
                f"Product with public_id "
                f"'{public_id}' does not exist."
            )

        # --------------------------------------------------------------
        # Validate subcategory if it is being changed
        # --------------------------------------------------------------

        if "subcategory_id" in data:

            subcategory_id = data["subcategory_id"]

            subcategory = (
                self.subcategory_repository.get_active_by_id(
                    subcategory_id
                )
            )

            if subcategory is None:
                raise ValueError(
                    f"Active subcategory with id "
                    f"'{subcategory_id}' does not exist."
                )

        # --------------------------------------------------------------
        # Validate slug if it is being changed
        # --------------------------------------------------------------

        if "slug" in data:

            slug = data["slug"]

            existing_product = (
                self.product_repository.get_by_slug(slug)
            )

            if (
                existing_product is not None
                and existing_product.id != product.id
            ):
                raise ValueError(
                    f"Product with slug '{slug}' already exists."
                )

        # return self.product_repository.update(
        #     product,
        #     data,
        # )
            # --------------------------------------------------------------
        # Validate pricing
        # --------------------------------------------------------------

        if "price" in data:

            price = data["price"]

            if price <= 0:
                raise ValueError(
                    "Product price must be greater than 0."
                )

        if "mrp" in data:

            mrp = data["mrp"]

            if mrp is not None and mrp <= 0:
                raise ValueError(
                    "Product MRP must be greater than 0."
                )

        if "cost_price" in data:

            cost_price = data["cost_price"]

            if cost_price is not None and cost_price <= 0:
                raise ValueError(
                    "Product cost price must be greater than 0."
                )

        # --------------------------------------------------------------
        # Validate selling price <= MRP
        # --------------------------------------------------------------

        final_price = data.get(
            "price",
            product.price,
        )

        final_mrp = data.get(
            "mrp",
            product.mrp,
        )

        if (
            final_mrp is not None
            and final_price > final_mrp
        ):
            raise ValueError(
                "Product price cannot be greater than MRP."
            )
        return self.product_repository.update(
            product,
            data,
        ) 
    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_product(
        self,
        *,
        public_id: str,
    ) -> None:

        product = (
            self.product_repository.get_by_public_id(
                public_id
            )
        )

        if product is None:
            raise ValueError(
                f"Product with public_id "
                f"'{public_id}' does not exist."
            )

        self.product_repository.delete(product)