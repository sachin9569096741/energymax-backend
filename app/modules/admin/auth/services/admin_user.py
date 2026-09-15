from sqlalchemy.orm import Session

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.repositories.admin_user_repo import (
    AdminUserRepository,
)
from app.modules.admin.auth.repositories.role_repo import (
    RoleRepository,
)
from app.modules.admin.auth.security.password import (
    hash_password,
)


class AdminUserService:

    def __init__(self, db: Session):
        self.db = db

        self.user_repository = AdminUserRepository(db)

        self.role_repository = RoleRepository(db)

    # =========================================================
    # CREATE STAFF
    # =========================================================

    def create_staff(
        self,
        *,
        username: str,
        password: str,
        staff_type: str,
        role_name: str | None = None,
        is_active: bool = True,
        created_by_id: int,
    ) -> AdminUser:

        # -----------------------------------------------------
        # Username must be unique
        # -----------------------------------------------------

        existing_user = (
            self.user_repository.get_by_username(
                username
            )
        )

        if existing_user is not None:
            raise ValueError(
                f"Username '{username}' already exists."
            )

        # -----------------------------------------------------
        # Resolve role using public_id
        # -----------------------------------------------------

        role_id = None

        if role_name is not None:

            role = (
                self.role_repository.get_by_name(
                    role_name
                )
            )

            if role is None:
                raise ValueError(
                    f"Role "
                    f"'{role_name}' does not exist."
                )

            if not role.is_active:
                raise ValueError(
                    f"Role '{role.name}' is inactive."
                )

            # Internal database ID.
            # This stays inside
            #  the backend.
            role_id = role.id

        # -----------------------------------------------------
        # Create staff
        # -----------------------------------------------------

        staff = AdminUser(
            username=username,
            password_hash=hash_password(password),
            staff_type=staff_type,
            role_id=role_id,
            is_super_admin=False,
            is_active=is_active,
            created_by_id=created_by_id,
        )

        return self.user_repository.create(staff)

    # =========================================================
    # GET STAFF
    # =========================================================

    def get_staff(
        self,
        *,
        public_id: str,
    ) -> AdminUser:

        staff = (
            self.user_repository.get_by_public_id(
                public_id
            )
        )

        if staff is None:
            raise ValueError(
                f"Staff with public_id "
                f"'{public_id}' does not exist."
            )

        return staff

    # =========================================================
    # LIST STAFF
    # =========================================================

    def list_staff(
        self,
        *,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AdminUser], int]:

        if page < 1:
            raise ValueError(
                "Page must be greater than 0."
            )

        if page_size < 1 or page_size > 100:
            raise ValueError(
                "Page size must be between 1 and 100."
            )

        offset = (page - 1) * page_size

        return self.user_repository.list(
            is_active=is_active,
            offset=offset,
            limit=page_size,
        )

    # =========================================================
    # UPDATE STAFF
    # =========================================================

    def update_staff(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> AdminUser:

        staff = (
            self.user_repository.get_by_public_id(
                public_id
            )
        )

        if staff is None:
            raise ValueError(
                f"Staff with public_id "
                f"'{public_id}' does not exist."
            )

        # -----------------------------------------------------
        # Never modify super admin through staff management
        # -----------------------------------------------------

        if staff.is_super_admin:
            raise ValueError(
                "Super admin cannot be modified through "
                "staff management."
            )

        # -----------------------------------------------------
        # Username uniqueness
        # -----------------------------------------------------

        if "username" in data:

            existing_user = (
                self.user_repository.get_by_username(
                    data["username"]
                )
            )

            if (
                existing_user is not None
                and existing_user.id != staff.id
            ):
                raise ValueError(
                    f"Username "
                    f"'{data['username']}' already exists."
                )

        # -----------------------------------------------------
        # Resolve role using public_id
        # -----------------------------------------------------

        if "role_public_id" in data:

            role_public_id = data.pop(
                "role_public_id"
            )

            # None means remove the current role.
            if role_public_id is None:

                data["role_id"] = None

            else:

                role = self.role_repository.get_by_name(
                    data["role_name"]
                )
                

                if role is None:
                    raise ValueError(
                        f"Role with public_id "
                        f"'{role_public_id}' does not exist."
                    )

                if not role.is_active:
                    raise ValueError(
                        f"Role '{role.name}' is inactive."
                    )

                data["role_id"] = role.id

        return self.user_repository.update(
            staff,
            data,
        )

    # =========================================================
    # CHANGE PASSWORD
    # =========================================================

    def change_password(
        self,
        *,
        public_id: str,
        password: str,
    ) -> AdminUser:

        staff = (
            self.user_repository.get_by_public_id(
                public_id
            )
        )

        if staff is None:
            raise ValueError(
                f"Staff with public_id "
                f"'{public_id}' does not exist."
            )

        if staff.is_super_admin:
            raise ValueError(
                "Super admin password cannot be changed "
                "through staff management."
            )

        return self.user_repository.update(
            staff,
            {
                "password_hash": hash_password(
                    password
                )
            },
        )

    # =========================================================
    # ACTIVATE / DEACTIVATE STAFF
    # =========================================================

    def set_active_status(
        self,
        *,
        public_id: str,
        is_active: bool,
    ) -> AdminUser:

        staff = (
            self.user_repository.get_by_public_id(
                public_id
            )
        )

        if staff is None:
            raise ValueError(
                f"Staff with public_id "
                f"'{public_id}' does not exist."
            )

        if staff.is_super_admin:
            raise ValueError(
                "Super admin status cannot be changed "
                "through staff management."
            )

        return self.user_repository.update(
            staff,
            {
                "is_active": is_active,
            },
        )

    # =========================================================
    # DELETE STAFF
    # =========================================================

    def delete_staff(
        self,
        *,
        public_id: str,
    ) -> None:

        staff = (
            self.user_repository.get_by_public_id(
                public_id
            )
        )

        if staff is None:
            raise ValueError(
                f"Staff with public_id "
                f"'{public_id}' does not exist."
            )

        if staff.is_super_admin:
            raise ValueError(
                "Super admin cannot be deleted "
                "through staff management."
            )

        self.user_repository.delete(staff)