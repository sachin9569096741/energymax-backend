from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.permission import Permission


class PermissionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        permission_id: int,
    ) -> Permission | None:

        statement = select(Permission).where(
            Permission.id == permission_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Permission | None:

        statement = select(Permission).where(
            Permission.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY NAME
    # ---------------------------------------------------------

    def get_by_name(
        self,
        name: str,
    ) -> Permission | None:

        statement = select(Permission).where(
            Permission.name == name
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list(
        self,
        *,
        is_active: bool | None = None,
    ) -> list[Permission]:

        statement = select(Permission)

        if is_active is not None:
            statement = statement.where(
                Permission.is_active == is_active
            )

        statement = statement.order_by(
            Permission.name
        )

        return list(
            self.db.scalars(statement).all()
        )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        permission: Permission,
    ) -> Permission:

        self.db.add(permission)
        self.db.flush()
        self.db.refresh(permission)

        return permission

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        permission: Permission,
        data: dict,
    ) -> Permission:

        for field, value in data.items():
            setattr(permission, field, value)

        self.db.flush()
        self.db.refresh(permission)

        return permission

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        permission: Permission,
    ) -> None:

        self.db.delete(permission)
        self.db.flush()