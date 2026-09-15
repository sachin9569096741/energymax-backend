from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.admin.auth.models.admin_user import AdminUser

from app.modules.admin.auth.schemas.permission import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)

from app.modules.admin.auth.schemas.role import (
    RoleCreate,
    RolePermissionRequest,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
)

from app.modules.admin.auth.schemas.user_permission import (
    UserPermissionRequest,
    UserPermissionResponse,
)

from app.modules.admin.auth.security.dependencies import (
    require_super_admin,
)

from app.modules.admin.auth.services.permission import (
    PermissionService,
)

from app.modules.admin.auth.services.role import (
    RoleService,
)

from app.modules.admin.auth.services.admin_user import (
    AdminUserService,
)


# =========================================================
# PERMISSION ROUTER
# =========================================================

router = APIRouter(
    prefix="/admin/permissions",
    tags=["Admin Permissions"],
)


# =========================================================
# PERMISSIONS
# =========================================================


@router.get(
    "",
    response_model=list[PermissionResponse],
)
def list_permissions(
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = PermissionService(db)

    return service.list_permissions()


# =========================================================
# CREATE PERMISSION
# =========================================================


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission(
    payload: PermissionCreate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = PermissionService(db)

    try:
        return service.create_permission(
            name=payload.name,
            description=payload.description,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# GET PERMISSION
# =========================================================


@router.get(
    "/{public_id}",
    response_model=PermissionResponse,
)
def get_permission(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = PermissionService(db)

    try:
        return service.get_permission(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# UPDATE PERMISSION
# =========================================================


@router.patch(
    "/{public_id}",
    response_model=PermissionResponse,
)
def update_permission(
    public_id: str,
    payload: PermissionUpdate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = PermissionService(db)

    data = payload.model_dump(
        exclude_unset=True,
    )

    try:
        return service.update_permission(
            public_id=public_id,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DELETE PERMISSION
# =========================================================


@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_permission(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = PermissionService(db)

    try:
        service.delete_permission(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ROLE ROUTER
# =========================================================

roles_router = APIRouter(
    prefix="/admin/roles",
    tags=["Admin Roles"],
)


# =========================================================
# LIST ROLES
# =========================================================


@roles_router.get(
    "",
    response_model=list[RoleResponse],
)
def list_roles(
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    return service.list_roles()


# =========================================================
# CREATE ROLE
# =========================================================


@roles_router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    payload: RoleCreate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    try:
        return service.create_role(
            name=payload.name,
            description=payload.description,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# GET ROLE
# =========================================================


@roles_router.get(
    "/{public_id}",
    response_model=RoleResponse,
)
def get_role(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    try:
        return service.get_role(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# UPDATE ROLE
# =========================================================


@roles_router.patch(
    "/{public_id}",
    response_model=RoleResponse,
)
def update_role(
    public_id: str,
    payload: RoleUpdate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    data = payload.model_dump(
        exclude_unset=True,
    )

    try:
        return service.update_role(
            public_id=public_id,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DELETE ROLE
# =========================================================


@roles_router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_role(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    try:
        service.delete_role(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ROLE → PERMISSIONS
# =========================================================


@roles_router.post(
    "/{role_public_id}/permissions",
    response_model=RolePermissionResponse,
)
def assign_permission_to_role(
    role_public_id: str,
    payload: RolePermissionRequest,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)
    permission_service = PermissionService(db)

    try:
        # Resolve role using public ID.
        role = service.get_role(
            public_id=role_public_id,
        )

        # Resolve permission using public ID.
        permission = permission_service.get_permission(
            public_id=payload.permission_public_id,
        )

        # Use internal database IDs only inside backend.
        role_permission = service.assign_permission(
            role_id=role.id,
            permission_id=permission.id,
        )

        return RolePermissionResponse(
            permission_public_id=permission.public_id,
            permission_name=permission.name,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# REMOVE PERMISSION FROM ROLE
# =========================================================


@roles_router.delete(
    "/{role_public_id}/permissions/{permission_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_permission_from_role(
    role_public_id: str,
    permission_public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)
    permission_service = PermissionService(db)

    try:
        # Resolve role.
        role = service.get_role(
            public_id=role_public_id,
        )

        # Resolve permission.
        permission = permission_service.get_permission(
            public_id=permission_public_id,
        )

        # Remove using internal database IDs.
        service.remove_permission(
            role_id=role.id,
            permission_id=permission.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# GET ROLE PERMISSIONS
# =========================================================


@roles_router.get(
    "/{role_public_id}/permissions",
    response_model=list[RolePermissionResponse],
)
def get_role_permissions(
    role_public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = RoleService(db)

    try:
        # Resolve role using public ID.
        role = service.get_role(
            public_id=role_public_id,
        )

        role_permissions = service.get_role_permissions(
            role_id=role.id,
        )

        return [
            RolePermissionResponse(
                permission_public_id=role_permission.permission.public_id,
                permission_name=role_permission.permission.name,
            )
            for role_permission in role_permissions
        ]

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# STAFF PERMISSION OVERRIDES
# =========================================================

user_permissions_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin User Permissions"],
)


# =========================================================
# GET STAFF PERMISSIONS
# =========================================================


@user_permissions_router.get(
    "/{user_public_id}/permissions",
    response_model=list[UserPermissionResponse],
)
def get_user_permissions(
    user_public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    user_service = AdminUserService(db)
    permission_service = PermissionService(db)

    try:
        # Resolve staff using public ID.
        user = user_service.get_staff(
            public_id=user_public_id,
        )

        permissions = permission_service.get_user_permissions(
            user_id=user.id,
        )

        return [
            UserPermissionResponse(
                permission_public_id=permission.public_id,
                permission_name=permission.name,
                is_allowed=permission.is_allowed,
            )
            for permission in permissions
        ]

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# SET STAFF PERMISSION
# =========================================================


@user_permissions_router.put(
    "/{user_public_id}/permissions",
    response_model=UserPermissionResponse,
)
def set_user_permission(
    user_public_id: str,
    payload: UserPermissionRequest,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    user_service = AdminUserService(db)
    permission_service = PermissionService(db)

    try:
        # Resolve staff using public ID.
        user = user_service.get_staff(
            public_id=user_public_id,
        )

        # Resolve permission using public ID.
        permission = permission_service.get_permission(
            public_id=payload.permission_public_id,
        )

        user_permission = permission_service.set_user_permission(
            user_id=user.id,
            permission_id=permission.id,
            is_allowed=payload.is_allowed,
        )

        return UserPermissionResponse(
            permission_public_id=permission.public_id,
            permission_name=permission.name,
            is_allowed=user_permission.is_allowed,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# REMOVE STAFF PERMISSION OVERRIDE
# =========================================================


@user_permissions_router.delete(
    "/{user_public_id}/permissions/{permission_public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_permission(
    user_public_id: str,
    permission_public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    user_service = AdminUserService(db)
    permission_service = PermissionService(db)

    try:
        # Resolve staff using public ID.
        user = user_service.get_staff(
            public_id=user_public_id,
        )

        # Resolve permission using public ID.
        permission = permission_service.get_permission(
            public_id=permission_public_id,
        )

        permission_service.remove_user_permission(
            user_id=user.id,
            permission_id=permission.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc