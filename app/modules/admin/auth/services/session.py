from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.admin.auth.models.admin_session import AdminSession
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.repositories.admin_session_repo import (
    AdminSessionRepository,
)
from app.modules.admin.auth.security.jwt import (
    create_refresh_token,
)


class AdminSessionService:

    def __init__(self, db: Session):
        self.db = db
        self.repository = AdminSessionRepository(db)

    # ---------------------------------------------------------
    # HASH TOKEN
    # ---------------------------------------------------------

    @staticmethod
    def hash_token(token: str) -> str:
        return sha256(
            token.encode("utf-8")
        ).hexdigest()

    # ---------------------------------------------------------
    # CREATE SESSION
    # ---------------------------------------------------------

    def create_session(
        self,
        *,
        user: AdminUser,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AdminSession, str]:

        session_public_id = str(uuid4())

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(
                days=settings.jwt_refresh_token_expire_days
            )
        )

        # Temporary token payload is created using the
        # session public ID. This token is what gets hashed.
        refresh_token = create_refresh_token(
            user_id=user.id,
            public_id=user.public_id,
            session_id=session_public_id,
        )

        refresh_token_hash = self.hash_token(
            refresh_token
        )

        session = AdminSession(
            public_id=session_public_id,
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        session = self.repository.create(session)

        return session, refresh_token

    # ---------------------------------------------------------
    # GET ACTIVE SESSION
    # ---------------------------------------------------------

    def get_active_session(
        self,
        refresh_token: str,
    ) -> AdminSession | None:

        token_hash = self.hash_token(
            refresh_token
        )

        return self.repository.get_active_by_refresh_token_hash(
            token_hash
        )

    # ---------------------------------------------------------
    # REVOKE SESSION
    # ---------------------------------------------------------

    def revoke_session(
        self,
        session: AdminSession,
    ) -> AdminSession:

        return self.repository.revoke(session)

    # ---------------------------------------------------------
    # REVOKE ALL USER SESSIONS
    # ---------------------------------------------------------

    def revoke_all_sessions(
        self,
        user_id: int,
    ) -> int:

        return self.repository.revoke_all_for_user(
            user_id
        )

    # ---------------------------------------------------------
    # LIST USER SESSIONS
    # ---------------------------------------------------------

    def list_sessions(
        self,
        user_id: int,
        *,
        include_revoked: bool = False,
    ) -> list[AdminSession]:

        return self.repository.list_by_user_id(
            user_id,
            include_revoked=include_revoked,
        )