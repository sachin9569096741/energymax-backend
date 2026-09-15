from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.category import Category


class CategoryRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        category_id: int,
    ) -> Category | None:

        statement = select(Category).where(
            Category.id == category_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Category | None:

        statement = select(Category).where(
            Category.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET ACTIVE BY ID
    # ---------------------------------------------------------

    def get_active_by_id(
        self,
        category_id: int,
    ) -> Category | None:

        statement = select(Category).where(
            Category.id == category_id,
            Category.is_active.is_(True),
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY SLUG
    # ---------------------------------------------------------

    def get_by_slug(
        self,
        slug: str,
    ) -> Category | None:

        statement = select(Category).where(
            Category.slug == slug
        )

        return self.db.scalar(statement)

    def get_by_name(
        self,
        name: str,
    ) -> Category | None:

        statement = select(Category).where(
            Category.name == name
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list(
        self,
        *,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Category], int]:

        statement = select(Category)

        count_statement = (
            select(func.count())
            .select_from(Category)
        )

        if is_active is not None:
            statement = statement.where(
                Category.is_active == is_active
            )

            count_statement = count_statement.where(
                Category.is_active == is_active
            )

        statement = (
            statement
            .order_by(
                Category.display_order,
                Category.id,
            )
            .offset(offset)
            .limit(limit)
        )

        categories = list(
            self.db.scalars(statement).all()
        )

        total = (
            self.db.scalar(count_statement)
            or 0
        )

        return categories, total

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        category: Category,
    ) -> Category:

        self.db.add(category)
        self.db.flush()
        self.db.refresh(category)

        return category

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        category: Category,
        data: dict,
    ) -> Category:

        for field, value in data.items():
            setattr(category, field, value)

        self.db.flush()
        self.db.refresh(category)

        return category

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        category: Category,
    ) -> None:

        self.db.delete(category)
        self.db.flush()