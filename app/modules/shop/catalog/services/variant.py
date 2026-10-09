from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.product_variant import ProductVariant
from app.modules.shop.catalog.repositories.product import ProductRepository
from app.modules.shop.catalog.repositories.variant import VariantRepository


class VariantService:

    def __init__(self, db: Session):
        self.variant_repository = VariantRepository(db)
        self.product_repository = ProductRepository(db)

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_variant(
        self,
        *,
        product_id: int,
        flavour: str,
        sku: str,
        price: Decimal,
        mrp: Decimal | None = None,
        cost_price: Decimal | None = None,
        is_active: bool = True,
    ) -> ProductVariant:

        # --------------------------------------------------------------
        # Validate product
        # --------------------------------------------------------------

        product = self.product_repository.get_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"Product with id '{product_id}' does not exist."
            )

        # --------------------------------------------------------------
        # Validate SKU uniqueness
        # --------------------------------------------------------------

        existing_variant = (
            self.variant_repository.get_by_sku(sku)
        )

        if existing_variant is not None:
            raise ValueError(
                f"Variant with SKU '{sku}' already exists."
            )

        # --------------------------------------------------------------
        # Validate pricing
        # --------------------------------------------------------------

        if mrp is not None and price > mrp:
            raise ValueError(
                "Variant price cannot be greater than MRP."
            )

        variant = ProductVariant(
            product_id=product_id,
            flavour=flavour.strip(),
            sku=sku.strip(),
            price=price,
            mrp=mrp,
            cost_price=cost_price,
            is_active=is_active,
        )

        return self.variant_repository.create(
            variant
        )

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def get_variant(
        self,
        *,
        public_id: str,
    ) -> ProductVariant:

        variant = (
            self.variant_repository.get_by_public_id(
                public_id
            )
        )

        if variant is None:
            raise ValueError(
                f"Variant with public_id "
                f"'{public_id}' does not exist."
            )

        return variant

    # ------------------------------------------------------------------
    # LIST BY PRODUCT
    # ------------------------------------------------------------------

    def list_variants(
        self,
        *,
        product_id: int,
        active_only: bool = False,
    ) -> list[ProductVariant]:

        product = self.product_repository.get_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"Product with id '{product_id}' does not exist."
            )

        return self.variant_repository.list_by_product(
            product_id=product_id,
            active_only=active_only,
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_variant(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> ProductVariant:

        variant = (
            self.variant_repository.get_by_public_id(
                public_id
            )
        )

        if variant is None:
            raise ValueError(
                f"Variant with public_id "
                f"'{public_id}' does not exist."
            )

        # --------------------------------------------------------------
        # Validate SKU if changed
        # --------------------------------------------------------------

        if "sku" in data:

            sku = data["sku"].strip()

            existing_variant = (
                self.variant_repository.get_by_sku(sku)
            )

            if (
                existing_variant is not None
                and existing_variant.id != variant.id
            ):
                raise ValueError(
                    f"Variant with SKU '{sku}' already exists."
                )

            data["sku"] = sku

        # --------------------------------------------------------------
        # Normalize flavour
        # --------------------------------------------------------------

        if "flavour" in data:
            data["flavour"] = data["flavour"].strip()

        # --------------------------------------------------------------
        # Validate pricing
        # --------------------------------------------------------------

        final_price = data.get(
            "price",
            variant.price,
        )

        final_mrp = data.get(
            "mrp",
            variant.mrp,
        )

        if (
            final_mrp is not None
            and final_price > final_mrp
        ):
            raise ValueError(
                "Variant price cannot be greater than MRP."
            )

        if "price" in data:
            if data["price"] <= 0:
                raise ValueError(
                    "Variant price must be greater than 0."
                )

        if "mrp" in data:
            if (
                data["mrp"] is not None
                and data["mrp"] <= 0
            ):
                raise ValueError(
                    "Variant MRP must be greater than 0."
                )

        if "cost_price" in data:
            if (
                data["cost_price"] is not None
                and data["cost_price"] <= 0
            ):
                raise ValueError(
                    "Variant cost price must be greater than 0."
                )

        return self.variant_repository.update(
            variant,
            data,
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_variant(
        self,
        *,
        public_id: str,
    ) -> None:

        variant = (
            self.variant_repository.get_by_public_id(
                public_id
            )
        )

        if variant is None:
            raise ValueError(
                f"Variant with public_id "
                f"'{public_id}' does not exist."
            )

        self.variant_repository.delete(
            variant
        )