from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.admin.auth.models.admin_user import AdminUser

from app.modules.admin.auth.schemas.admin_user import (
    AdminUserCreate,
    AdminUserPasswordUpdate,
    AdminUserUpdate,
)

from app.modules.admin.auth.schemas.user import (
    AdminUserResponse,
)

from app.modules.admin.auth.security.dependencies import (
    require_super_admin,
)

from app.modules.admin.auth.services.admin_user import (
    AdminUserService,
)


router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Staff"],
)


# =========================================================
# CREATE STAFF
# =========================================================


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_staff(
    payload: AdminUserCreate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        return service.create_staff(
            username=payload.username,
            password=payload.password,
            staff_type=payload.staff_type,
            role_name=payload.role_name,
            is_active=payload.is_active,
            created_by_id=current_user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# LIST STAFF
# =========================================================


@router.get(
    "",
    response_model=list[AdminUserResponse],
)
def list_staff(
    is_active: bool | None = Query(
        default=None,
    ),
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        users, _ = service.list_staff(
            is_active=is_active,
        )

        return users

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# GET STAFF
# =========================================================


@router.get(
    "/{public_id}",
    response_model=AdminUserResponse,
)
def get_staff(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        return service.get_staff(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# UPDATE STAFF
# =========================================================


@router.patch(
    "/{public_id}",
    response_model=AdminUserResponse,
)
def update_staff(
    public_id: str,
    payload: AdminUserUpdate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    data = payload.model_dump(
        exclude_unset=True,
    )

    try:
        return service.update_staff(
            public_id=public_id,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# CHANGE STAFF PASSWORD
# =========================================================


@router.patch(
    "/{public_id}/password",
    response_model=AdminUserResponse,
)
def change_staff_password(
    public_id: str,
    payload: AdminUserPasswordUpdate,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        return service.change_password(
            public_id=public_id,
            password=payload.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTIVATE / DEACTIVATE STAFF
# =========================================================


@router.patch(
    "/{public_id}/status",
    response_model=AdminUserResponse,
)
def update_staff_status(
    public_id: str,
    is_active: bool,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        return service.set_active_status(
            public_id=public_id,
            is_active=is_active,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DELETE STAFF
# =========================================================


@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_staff(
    public_id: str,
    current_user: AdminUser = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminUserService(db)

    try:
        service.delete_staff(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc