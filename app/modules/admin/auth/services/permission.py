from sqlalchemy.orm import Session

from app.modules.admin.auth.models.permission import Permission
from app.modules.admin.auth.models.user_permission import UserPermission

from app.modules.admin.auth.repositories.permission_repo import (
    PermissionRepository,
)
from app.modules.admin.auth.repositories.user_permission_repo import (
    UserPermissionRepository,
)


class PermissionService:

    def __init__(self, db: Session):
        self.permission_repository = PermissionRepository(db)
        self.user_permission_repository = UserPermissionRepository(db)

    # =========================================================
    # PERMISSION LIST
    # =========================================================

    def list_permissions(
        self,
        *,
        is_active: bool | None = True,
    ) -> list[Permission]:

        return self.permission_repository.list(
            is_active=is_active,
        )

    # =========================================================
    # GET PERMISSION
    # =========================================================

    def get_permission(
        self,
        *,
        public_id: str,
    ) -> Permission:

        permission = (
            self.permission_repository.get_by_public_id(
                public_id
            )
        )

        if permission is None:
            raise ValueError(
                f"Permission with public_id "
                f"'{public_id}' does not exist."
            )

        return permission

    # =========================================================
    # CREATE PERMISSION
    # =========================================================

    def create_permission(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> Permission:

        existing = (
            self.permission_repository.get_by_name(name)
        )

        if existing is not None:
            raise ValueError(
                f"Permission '{name}' already exists."
            )

        permission = Permission(
            name=name,
            description=description,
            is_active=True,
        )

        return self.permission_repository.create(
            permission
        )

    # =========================================================
    # UPDATE PERMISSION
    # =========================================================

    def update_permission(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> Permission:

        permission = (
            self.permission_repository.get_by_public_id(
                public_id
            )
        )

        if permission is None:
            raise ValueError(
                f"Permission with public_id "
                f"'{public_id}' does not exist."
            )

        if "name" in data:

            existing = (
                self.permission_repository.get_by_name(
                    data["name"]
                )
            )

            if (
                existing is not None
                and existing.id != permission.id
            ):
                raise ValueError(
                    f"Permission "
                    f"'{data['name']}' already exists."
                )

        return self.permission_repository.update(
            permission,
            data,
        )

    # =========================================================
    # DELETE PERMISSION
    # =========================================================

    def delete_permission(
        self,
        *,
        public_id: str,
    ) -> None:

        permission = (
            self.permission_repository.get_by_public_id(
                public_id
            )
        )

        if permission is None:
            raise ValueError(
                f"Permission with public_id "
                f"'{public_id}' does not exist."
            )

        self.permission_repository.delete(
            permission
        )

    # =========================================================
    # GET STAFF PERMISSIONS
    # =========================================================

    def get_user_permissions(
        self,
        *,
        user_id: int,
    ) -> list[UserPermission]:

        return self.user_permission_repository.get_by_user(
            user_id
        )

    # =========================================================
    # SET STAFF PERMISSION
    # =========================================================

    def set_user_permission(
        self,
        *,
        user_id: int,
        permission_id: int,
        is_allowed: bool,
    ) -> UserPermission:

        existing = self.user_permission_repository.get(
            user_id=user_id,
            permission_id=permission_id,
        )

        if existing is not None:

            return self.user_permission_repository.update(
                existing,
                {
                    "is_allowed": is_allowed,
                },
            )

        user_permission = UserPermission(
            user_id=user_id,
            permission_id=permission_id,
            is_allowed=is_allowed,
        )

        return self.user_permission_repository.create(
            user_permission
        )

    # =========================================================
    # REMOVE STAFF OVERRIDE
    # =========================================================

    def remove_user_permission(
        self,
        *,
        user_id: int,
        permission_id: int,
    ) -> None:

        existing = self.user_permission_repository.get(
            user_id=user_id,
            permission_id=permission_id,
        )

        if existing is None:
            return

        self.user_permission_repository.delete(
            existing
        )