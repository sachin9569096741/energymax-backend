from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.user_permission import (
    UserPermission,
)


class UserPermissionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get(
        self,
        *,
        user_id: int,
        permission_id: int,
    ) -> UserPermission | None:

        statement = select(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission_id,
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY USER
    # ---------------------------------------------------------

    def get_by_user(
        self,
        user_id: int,
    ) -> list[UserPermission]:

        statement = (
            select(UserPermission)
            .where(
                UserPermission.user_id == user_id
            )
            .order_by(UserPermission.id)
        )

        return list(
            self.db.scalars(statement).all()
        )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        user_permission: UserPermission,
    ) -> UserPermission:

        self.db.add(user_permission)
        self.db.flush()
        self.db.refresh(user_permission)

        return user_permission

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        user_permission: UserPermission,
        data: dict,
    ) -> UserPermission:

        for field, value in data.items():
            setattr(user_permission, field, value)

        self.db.flush()
        self.db.refresh(user_permission)

        return user_permission

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        user_permission: UserPermission,
    ) -> None:

        self.db.delete(user_permission)
        self.db.flush()