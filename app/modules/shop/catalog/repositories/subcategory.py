from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.subcategory import Subcategory


class SubcategoryRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        subcategory_id: int,
    ) -> Subcategory | None:

        statement = select(Subcategory).where(
            Subcategory.id == subcategory_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET ACTIVE BY ID
    # ---------------------------------------------------------

    def get_active_by_id(
        self,
        subcategory_id: int,
    ) -> Subcategory | None:

        statement = select(Subcategory).where(
            Subcategory.id == subcategory_id,
            Subcategory.is_active.is_(True),
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Subcategory | None:

        statement = select(Subcategory).where(
            Subcategory.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY NAME WITHIN CATEGORY
    # ---------------------------------------------------------

    def get_by_name(
        self,
        *,
        category_id: int,
        name: str,
    ) -> Subcategory | None:

        statement = select(Subcategory).where(
            Subcategory.category_id == category_id,
            Subcategory.name == name,
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY SLUG WITHIN CATEGORY
    # ---------------------------------------------------------

    def get_by_slug(
        self,
        *,
        category_id: int,
        slug: str,
    ) -> Subcategory | None:

        statement = select(Subcategory).where(
            Subcategory.category_id == category_id,
            Subcategory.slug == slug,
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list(
        self,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Subcategory], int]:

        statement = select(Subcategory)

        count_statement = (
            select(func.count())
            .select_from(Subcategory)
        )

        if category_id is not None:
            statement = statement.where(
                Subcategory.category_id == category_id
            )

            count_statement = count_statement.where(
                Subcategory.category_id == category_id
            )

        if is_active is not None:
            statement = statement.where(
                Subcategory.is_active == is_active
            )

            count_statement = count_statement.where(
                Subcategory.is_active == is_active
            )

        statement = (
            statement
            .order_by(
                Subcategory.display_order,
                Subcategory.id,
            )
            .offset(offset)
            .limit(limit)
        )

        subcategories = list(
            self.db.scalars(statement).all()
        )

        total = (
            self.db.scalar(count_statement)
            or 0
        )

        return subcategories, total

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        subcategory: Subcategory,
    ) -> Subcategory:

        self.db.add(subcategory)
        self.db.flush()
        self.db.refresh(subcategory)

        return subcategory

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        subcategory: Subcategory,
        data: dict,
    ) -> Subcategory:

        for field, value in data.items():
            setattr(subcategory, field, value)

        self.db.flush()
        self.db.refresh(subcategory)

        return subcategory

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        subcategory: Subcategory,
    ) -> None:

        self.db.delete(subcategory)
        self.db.flush()