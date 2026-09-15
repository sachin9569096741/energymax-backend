from sqlalchemy.orm import Session

from app.modules.admin.auth.models.role import Role
from app.modules.admin.auth.models.role_permission import RolePermission

from app.modules.admin.auth.repositories.role_repo import (
    RoleRepository,
)
from app.modules.admin.auth.repositories.permission_repo import (
    PermissionRepository,
)


class RoleService:

    def __init__(self, db: Session):
        self.role_repository = RoleRepository(db)
        self.permission_repository = PermissionRepository(db)

    # =========================================================
    # LIST ROLES
    # =========================================================

    def list_roles(
        self,
        *,
        is_active: bool | None = True,
    ) -> list[Role]:

        return self.role_repository.list(
            is_active=is_active,
        )

    # =========================================================
    # GET ROLE
    # =========================================================

    def get_role(
        self,
        *,
        public_id: str,
    ) -> Role:

        role = self.role_repository.get_by_public_id(
            public_id
        )

        if role is None:
            raise ValueError(
                f"Role with public_id "
                f"'{public_id}' does not exist."
            )

        return role

    # =========================================================
    # CREATE ROLE
    # =========================================================

    def create_role(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> Role:

        existing = self.role_repository.get_by_name(
            name
        )

        if existing is not None:
            raise ValueError(
                f"Role '{name}' already exists."
            )

        role = Role(
            name=name,
            description=description,
            is_active=True,
        )

        return self.role_repository.create(role)

    # =========================================================
    # UPDATE ROLE
    # =========================================================

    def update_role(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> Role:

        role = self.role_repository.get_by_public_id(
            public_id
        )

        if role is None:
            raise ValueError(
                f"Role with public_id "
                f"'{public_id}' does not exist."
            )

        if "name" in data:

            existing = self.role_repository.get_by_name(
                data["name"]
            )

            if (
                existing is not None
                and existing.id != role.id
            ):
                raise ValueError(
                    f"Role '{data['name']}' already exists."
                )

        return self.role_repository.update(
            role,
            data,
        )

    # =========================================================
    # DELETE ROLE
    # =========================================================

    def delete_role(
        self,
        *,
        public_id: str,
    ) -> None:

        role = self.role_repository.get_by_public_id(
            public_id
        )

        if role is None:
            raise ValueError(
                f"Role with public_id "
                f"'{public_id}' does not exist."
            )

        self.role_repository.delete(role)

    # =========================================================
    # ASSIGN PERMISSION TO ROLE
    # =========================================================

    def assign_permission(
        self,
        *,
        role_id: int,
        permission_id: int,
    ) -> RolePermission:

        role = self.role_repository.get_by_id(
            role_id
        )

        if role is None:
            raise ValueError(
                "Role does not exist."
            )

        permission = self.permission_repository.get_by_id(
            permission_id
        )

        if permission is None:
            raise ValueError(
                "Permission does not exist."
            )

        # Prevent duplicate role-permission assignment
        for role_permission in role.role_permissions:

            if (
                role_permission.permission_id
                == permission_id
            ):
                return role_permission

        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
        )

        self.role_repository.db.add(
            role_permission
        )

        self.role_repository.db.flush()
        self.role_repository.db.refresh(
            role_permission
        )

        return role_permission

    # =========================================================
    # REMOVE PERMISSION FROM ROLE
    # =========================================================

    def remove_permission(
        self,
        *,
        role_id: int,
        permission_id: int,
    ) -> None:

        role = self.role_repository.get_by_id(
            role_id
        )

        if role is None:
            raise ValueError(
                "Role does not exist."
            )

        for role_permission in role.role_permissions:

            if (
                role_permission.permission_id
                == permission_id
            ):

                self.role_repository.db.delete(
                    role_permission
                )

                self.role_repository.db.flush()

                return

    # =========================================================
    # GET ROLE PERMISSIONS
    # =========================================================

    def get_role_permissions(
        self,
        *,
        role_id: int,
    ) -> list[RolePermission]:

        role = self.role_repository.get_by_id(
            role_id
        )

        if role is None:
            raise ValueError(
                "Role does not exist."
            )

        return role.role_permissions