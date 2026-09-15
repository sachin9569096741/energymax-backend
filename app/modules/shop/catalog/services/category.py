from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.category import Category
from app.modules.shop.catalog.repositories.category import (
    CategoryRepository,
)


class CategoryService:

    def __init__(self, db: Session):
        self.category_repository = CategoryRepository(db)

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create_category(
        self,
        *,
        name: str,
        slug: str,
        description: str | None = None,
        image_url: str | None = None,
        display_order: int = 0,
        is_active: bool = True,
    ) -> Category:

        # -----------------------------------------------------
        # Validate name uniqueness
        # -----------------------------------------------------

        existing_category = (
            self.category_repository.get_by_name(name)
        )

        if existing_category is not None:
            raise ValueError(
                f"Category with name '{name}' already exists."
            )

        # -----------------------------------------------------
        # Validate slug uniqueness
        # -----------------------------------------------------

        existing_category = (
            self.category_repository.get_by_slug(slug)
        )

        if existing_category is not None:
            raise ValueError(
                f"Category with slug '{slug}' already exists."
            )

        # -----------------------------------------------------
        # Create
        # -----------------------------------------------------

        category = Category(
            name=name,
            slug=slug,
            description=description,
            image_url=image_url,
            display_order=display_order,
            is_active=is_active,
        )

        return self.category_repository.create(category)

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get_category(
        self,
        *,
        public_id: str,
    ) -> Category:

        category = (
            self.category_repository.get_by_public_id(
                public_id
            )
        )

        if category is None:
            raise ValueError(
                f"Category with public_id "
                f"'{public_id}' does not exist."
            )

        return category

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list_categories(
        self,
        *,
        is_active: bool | None = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Category], int]:

        if page < 1:
            raise ValueError(
                "Page must be greater than 0."
            )

        if page_size < 1 or page_size > 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        offset = (page - 1) * page_size

        return self.category_repository.list(
            is_active=is_active,
            offset=offset,
            limit=page_size,
        )

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update_category(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> Category:

        category = (
            self.category_repository.get_by_public_id(
                public_id
            )
        )

        if category is None:
            raise ValueError(
                f"Category with public_id "
                f"'{public_id}' does not exist."
            )

        # -----------------------------------------------------
        # Validate name if changed
        # -----------------------------------------------------

        if "name" in data:

            name = data["name"]

            existing_category = (
                self.category_repository.get_by_name(name)
            )

            if (
                existing_category is not None
                and existing_category.id != category.id
            ):
                raise ValueError(
                    f"Category with name "
                    f"'{name}' already exists."
                )

        # -----------------------------------------------------
        # Validate slug if changed
        # -----------------------------------------------------

        if "slug" in data:

            slug = data["slug"]

            existing_category = (
                self.category_repository.get_by_slug(slug)
            )

            if (
                existing_category is not None
                and existing_category.id != category.id
            ):
                raise ValueError(
                    f"Category with slug "
                    f"'{slug}' already exists."
                )

        return self.category_repository.update(
            category,
            data,
        )

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete_category(
        self,
        *,
        public_id: str,
    ) -> None:

        category = (
            self.category_repository.get_by_public_id(
                public_id
            )
        )

        if category is None:
            raise ValueError(
                f"Category with public_id "
                f"'{public_id}' does not exist."
            )

        self.category_repository.delete(category)