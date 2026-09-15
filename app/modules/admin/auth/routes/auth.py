from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.admin.auth.schemas.login import AdminLoginRequest
from app.modules.admin.auth.schemas.token import TokenResponse
from app.modules.admin.auth.schemas.session import AdminSessionResponse
from app.modules.admin.auth.schemas.user import AdminUserResponse

from app.modules.admin.auth.security.dependencies import (
    get_current_admin,
)

from app.modules.admin.auth.services.auth import AdminAuthService
from app.modules.admin.auth.services.session import AdminSessionService

from app.modules.admin.auth.models.admin_user import AdminUser


router = APIRouter(
    prefix="/admin/auth",
    tags=["Admin Authentication"],
)


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    data: AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    service = AdminAuthService(db)

    user_agent = request.headers.get("user-agent")

    ip_address = (
        request.client.host
        if request.client
        else None
    )

    _, tokens = service.login(
        data=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return tokens


# =========================================================
# REFRESH TOKEN
# =========================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def refresh(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    service = AdminAuthService(db)

    return service.refresh(
        refresh_token=refresh_token,
    )


# =========================================================
# CURRENT ADMIN
# =========================================================

@router.get(
    "/me",
    response_model=AdminUserResponse,
    status_code=status.HTTP_200_OK,
)
def me(
    current_admin: AdminUser = Depends(
        get_current_admin
    ),
):
    return current_admin


# =========================================================
# LOGOUT
# =========================================================

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    service = AdminAuthService(db)

    service.logout(
        refresh_token=refresh_token,
    )

    return None


# =========================================================
# LOGOUT ALL SESSIONS
# =========================================================

@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
)
def logout_all(
    current_admin: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminAuthService(db)

    count = service.logout_all(
        user_id=current_admin.id,
    )

    return {
        "message": "All sessions revoked successfully.",
        "revoked_sessions": count,
    }


# =========================================================
# LIST SESSIONS
# =========================================================

@router.get(
    "/sessions",
    response_model=list[AdminSessionResponse],
    status_code=status.HTTP_200_OK,
)
def sessions(
    current_admin: AdminUser = Depends(
        get_current_admin
    ),
    db: Session = Depends(get_db),
):
    service = AdminSessionService(db)

    return service.list_sessions(
        user_id=current_admin.id,
        include_revoked=False,
    )