from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.repositories.admin_user_repo import (
    AdminUserRepository,
)
from app.modules.admin.auth.security.jwt import (
    JWTError,
    decode_access_token,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


# =========================================================
# CURRENT ADMIN
# =========================================================

def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> AdminUser:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        payload = decode_access_token(
            credentials.credentials
        )

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    try:
        user_id = int(payload["sub"])

    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    repository = AdminUserRepository(db)

    user = repository.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin user does not exist.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive.",
        )

    return user


# =========================================================
# SUPER ADMIN
# =========================================================

def require_super_admin(
    current_user: AdminUser = Depends(
        get_current_admin
    ),
) -> AdminUser:

    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin permission required.",
        )

    return current_user


# =========================================================
# PERMISSION CHECK
# =========================================================

# =========================================================
# PERMISSION CHECK
# =========================================================

def require_permission(
    permission_name: str,
) -> Callable:

    def permission_dependency(
        current_user: AdminUser = Depends(
            get_current_admin
        ),
        db: Session = Depends(get_db),
    ) -> AdminUser:

        # -------------------------------------------------
        # SUPER ADMIN BYPASS
        # -------------------------------------------------

        if current_user.is_super_admin:
            return current_user

        # -------------------------------------------------
        # FIND PERMISSION
        # -------------------------------------------------

        from sqlalchemy import select

        from app.modules.admin.auth.models.permission import (
            Permission,
        )
        from app.modules.admin.auth.models.role_permission import (
            RolePermission,
        )
        from app.modules.admin.auth.models.user_permission import (
            UserPermission,
        )

        permission = db.scalar(
            select(Permission).where(
                Permission.name == permission_name,
                Permission.is_active.is_(True),
            )
        )

        if permission is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission '{permission_name}' "
                    "does not exist or is inactive."
                ),
            )

        # -------------------------------------------------
        # DIRECT USER OVERRIDE
        # -------------------------------------------------

        user_permission = db.scalar(
            select(UserPermission).where(
                UserPermission.user_id == current_user.id,
                UserPermission.permission_id == permission.id,
            )
        )

        if user_permission is not None:

            # Explicit allow
            if user_permission.is_allowed:
                return current_user

            # Explicit deny overrides role permission
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission required: "
                    f"{permission_name}"
                ),
            )

        # -------------------------------------------------
        # ROLE PERMISSION
        # -------------------------------------------------

        if current_user.role_id is not None:

            role_permission = db.scalar(
                select(RolePermission).where(
                    RolePermission.role_id
                    == current_user.role_id,
                    RolePermission.permission_id
                    == permission.id,
                )
            )

            if role_permission is not None:
                return current_user

        # -------------------------------------------------
        # DENIED
        # -------------------------------------------------

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Permission required: "
                f"{permission_name}"
            ),
        )

    return permission_dependency