from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.repositories.admin_user_repo import (
    AdminUserRepository,
)
from app.modules.admin.auth.schemas.login import (
    AdminLoginRequest,
)
from app.modules.admin.auth.schemas.token import (
    TokenResponse,
)
from app.modules.admin.auth.security.jwt import (
    JWTError,
    create_access_token,
    decode_refresh_token,
)
from app.modules.admin.auth.security.password import (
    needs_rehash,
    verify_password,
    hash_password,
)
from app.modules.admin.auth.services.session import (
    AdminSessionService,
)


class AdminAuthService:

    def __init__(self, db: Session):
        self.db = db
        self.user_repository = AdminUserRepository(db)
        self.session_service = AdminSessionService(db)

    # ---------------------------------------------------------
    # LOGIN
    # ---------------------------------------------------------

    def login(
        self,
        *,
        data: AdminLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AdminUser, TokenResponse]:

        user = self.user_repository.get_by_username(
            data.username
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is inactive.",
            )

        if not verify_password(
            data.password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        # Upgrade old Argon2 parameters automatically.
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(
                data.password
            )

        now = datetime.now(timezone.utc)

        user.last_login_at = now

        self.db.flush()

        # Create refresh session.
        session, refresh_token = (
            self.session_service.create_session(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

        access_token = create_access_token(
            user_id=user.id,
            public_id=user.public_id,
            username=user.username,
        )

        self.db.commit()

        return user, TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=(
                settings.jwt_access_token_expire_minutes
                * 60
            ),
        )

    # ---------------------------------------------------------
    # REFRESH
    # ---------------------------------------------------------

    def refresh(
        self,
        *,
        refresh_token: str,
    ) -> TokenResponse:

        try:
            payload = decode_refresh_token(
                refresh_token
            )

        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

        try:
            user_id = int(payload["sub"])
            session_public_id = payload["session_id"]

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            ) from exc

        session = (
            self.session_service.get_active_session(
                refresh_token
            )
        )

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is invalid or expired.",
            )

        if session.public_id != session_public_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session.",
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session user.",
            )

        user = self.user_repository.get_by_id(
            user_id
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin user does not exist.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account is inactive.",
            )

        # Update session usage.
        self.session_service.repository.update_last_used(
            session
        )

        access_token = create_access_token(
            user_id=user.id,
            public_id=user.public_id,
            username=user.username,
        )

        self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=(
                settings.jwt_access_token_expire_minutes
                * 60
            ),
        )

    # ---------------------------------------------------------
    # LOGOUT
    # ---------------------------------------------------------

    def logout(
        self,
        *,
        refresh_token: str,
    ) -> None:

        session = (
            self.session_service.get_active_session(
                refresh_token
            )
        )

        if session is not None:
            self.session_service.revoke_session(
                session
            )

        self.db.commit()

    # ---------------------------------------------------------
    # LOGOUT ALL
    # ---------------------------------------------------------

    def logout_all(
        self,
        *,
        user_id: int,
    ) -> int:

        count = (
            self.session_service.revoke_all_sessions(
                user_id
            )
        )

        self.db.commit()

        return count