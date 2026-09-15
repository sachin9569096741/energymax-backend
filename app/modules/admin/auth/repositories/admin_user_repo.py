from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.admin_user import AdminUser


class AdminUserRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        user_id: int,
    ) -> AdminUser | None:

        statement = select(AdminUser).where(
            AdminUser.id == user_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> AdminUser | None:

        statement = select(AdminUser).where(
            AdminUser.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY USERNAME
    # ---------------------------------------------------------

    def get_by_username(
        self,
        username: str,
    ) -> AdminUser | None:

        statement = select(AdminUser).where(
            AdminUser.username == username
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST STAFF
    # ---------------------------------------------------------

    def list(
        self,
        *,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AdminUser], int]:

        statement = select(AdminUser)
        count_statement = select(
            func.count()
        ).select_from(AdminUser)

        if is_active is not None:

            statement = statement.where(
                AdminUser.is_active == is_active
            )

            count_statement = count_statement.where(
                AdminUser.is_active == is_active
            )

        statement = (
            statement
            .order_by(AdminUser.id)
            .offset(offset)
            .limit(limit)
        )

        users = list(
            self.db.scalars(statement).all()
        )

        total = (
            self.db.scalar(count_statement)
            or 0
        )

        return users, total

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        user: AdminUser,
    ) -> AdminUser:

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)

        return user

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        user: AdminUser,
        data: dict,
    ) -> AdminUser:

        for field, value in data.items():
            setattr(user, field, value)

        self.db.flush()
        self.db.refresh(user)

        return user

    # ---------------------------------------------------------
# DELETE
# ---------------------------------------------------------

    def delete(
        self,
        user: AdminUser,
    ) -> None:

        self.db.delete(user)
        self.db.flush()