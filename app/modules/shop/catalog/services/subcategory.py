from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.subcategory import Subcategory
from app.modules.shop.catalog.repositories.category import (
    CategoryRepository,
)
from app.modules.shop.catalog.repositories.subcategory import (
    SubcategoryRepository,
)


class SubcategoryService:

    def __init__(self, db: Session):
        self.category_repository = CategoryRepository(db)
        self.subcategory_repository = SubcategoryRepository(db)

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create_subcategory(
        self,
        *,
        category_public_id: str,
        name: str,
        slug: str,
        description: str | None = None,
        image_url: str | None = None,
        display_order: int = 0,
        is_active: bool = True,
    ) -> Subcategory:

        # -----------------------------------------------------
        # Validate parent category using public_id
        # -----------------------------------------------------

        category = (
            self.category_repository.get_by_public_id(
                category_public_id
            )
        )

        if category is None or not category.is_active:
            raise ValueError(
                f"Active category with public_id "
                f"'{category_public_id}' does not exist."
            )

        # Internal database ID
        category_id = category.id

        # -----------------------------------------------------
        # Validate name uniqueness inside category
        # -----------------------------------------------------

        existing_subcategory = (
            self.subcategory_repository.get_by_name(
                category_id=category_id,
                name=name,
            )
        )

        if existing_subcategory is not None:
            raise ValueError(
                f"Subcategory with name '{name}' "
                f"already exists in this category."
            )

        # -----------------------------------------------------
        # Validate slug uniqueness inside category
        # -----------------------------------------------------

        existing_subcategory = (
            self.subcategory_repository.get_by_slug(
                category_id=category_id,
                slug=slug,
            )
        )

        if existing_subcategory is not None:
            raise ValueError(
                f"Subcategory with slug '{slug}' "
                f"already exists in this category."
            )

        # -----------------------------------------------------
        # Create
        # -----------------------------------------------------

        subcategory = Subcategory(
            category_id=category_id,
            name=name,
            slug=slug,
            description=description,
            image_url=image_url,
            display_order=display_order,
            is_active=is_active,
        )

        return self.subcategory_repository.create(
            subcategory
        )

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get_subcategory(
        self,
        *,
        public_id: str,
    ) -> Subcategory:

        subcategory = (
            self.subcategory_repository.get_by_public_id(
                public_id
            )
        )

        if subcategory is None:
            raise ValueError(
                f"Subcategory with public_id "
                f"'{public_id}' does not exist."
            )

        return subcategory

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list_subcategories(
        self,
        *,
        category_public_id: str | None = None,
        is_active: bool | None = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Subcategory], int]:

        # -----------------------------------------------------
        # Validate pagination
        # -----------------------------------------------------

        if page < 1:
            raise ValueError(
                "Page must be greater than 0."
            )

        if page_size < 1 or page_size > 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        # -----------------------------------------------------
        # Resolve category public_id to internal category_id
        # -----------------------------------------------------

        category_id: int | None = None

        if category_public_id is not None:

            category = (
                self.category_repository.get_by_public_id(
                    category_public_id
                )
            )

            if category is None:
                raise ValueError(
                    f"Category with public_id "
                    f"'{category_public_id}' does not exist."
                )

            category_id = category.id

        # -----------------------------------------------------
        # Pagination
        # -----------------------------------------------------

        offset = (page - 1) * page_size

        # -----------------------------------------------------
        # Fetch subcategories
        # -----------------------------------------------------

        return self.subcategory_repository.list(
            category_id=category_id,
            is_active=is_active,
            offset=offset,
            limit=page_size,
        )

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update_subcategory(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> Subcategory:

        # -----------------------------------------------------
        # Get existing subcategory
        # -----------------------------------------------------

        subcategory = (
            self.subcategory_repository.get_by_public_id(
                public_id
            )
        )

        if subcategory is None:
            raise ValueError(
                f"Subcategory with public_id "
                f"'{public_id}' does not exist."
            )

        # -----------------------------------------------------
        # Determine resulting category
        # -----------------------------------------------------

        category_id = subcategory.category_id

        if "category_public_id" in data:

            category_public_id = data["category_public_id"]

            category = (
                self.category_repository.get_by_public_id(
                    category_public_id
                )
            )

            if category is None or not category.is_active:
                raise ValueError(
                    f"Active category with public_id "
                    f"'{category_public_id}' does not exist."
                )

            category_id = category.id

            # Remove public_id before sending data to repository
            data = data.copy()
            data.pop("category_public_id")

            # Set internal database category_id
            data["category_id"] = category_id

        else:

            # Keep existing category
            category = (
                self.category_repository.get_active_by_id(
                    category_id
                )
            )

            if category is None:
                raise ValueError(
                    f"Active category with id "
                    f"'{category_id}' does not exist."
                )

        # -----------------------------------------------------
        # Validate name if changed
        # -----------------------------------------------------

        if "name" in data:

            existing_subcategory = (
                self.subcategory_repository.get_by_name(
                    category_id=category_id,
                    name=data["name"],
                )
            )

            if (
                existing_subcategory is not None
                and existing_subcategory.id
                != subcategory.id
            ):
                raise ValueError(
                    f"Subcategory with name "
                    f"'{data['name']}' already exists "
                    f"in this category."
                )

        # -----------------------------------------------------
        # Validate slug if changed
        # -----------------------------------------------------

        if "slug" in data:

            existing_subcategory = (
                self.subcategory_repository.get_by_slug(
                    category_id=category_id,
                    slug=data["slug"],
                )
            )

            if (
                existing_subcategory is not None
                and existing_subcategory.id
                != subcategory.id
            ):
                raise ValueError(
                    f"Subcategory with slug "
                    f"'{data['slug']}' already exists "
                    f"in this category."
                )

        # -----------------------------------------------------
        # Update
        # -----------------------------------------------------

        return self.subcategory_repository.update(
            subcategory,
            data,
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete_subcategory(
        self,
        *,
        public_id: str,
    ) -> None:

        subcategory = (
            self.subcategory_repository.get_by_public_id(
                public_id
            )
        )

        if subcategory is None:
            raise ValueError(
                f"Subcategory with public_id "
                f"'{public_id}' does not exist."
            )

        self.subcategory_repository.delete(
            subcategory
        )