from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.admin_session import AdminSession


class AdminSessionRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        session: AdminSession,
    ) -> AdminSession:
        self.db.add(session)
        self.db.flush()
        self.db.refresh(session)

        return session

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        session_id: int,
    ) -> AdminSession | None:

        statement = select(AdminSession).where(
            AdminSession.id == session_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> AdminSession | None:

        statement = select(AdminSession).where(
            AdminSession.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY REFRESH TOKEN HASH
    # ---------------------------------------------------------

    def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
    ) -> AdminSession | None:

        statement = select(AdminSession).where(
            AdminSession.refresh_token_hash
            == refresh_token_hash
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET ACTIVE SESSION
    # ---------------------------------------------------------

    def get_active_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
    ) -> AdminSession | None:

        now = datetime.now(timezone.utc)

        statement = select(AdminSession).where(
            AdminSession.refresh_token_hash
            == refresh_token_hash,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > now,
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST USER SESSIONS
    # ---------------------------------------------------------

    def list_by_user_id(
        self,
        user_id: int,
        *,
        include_revoked: bool = False,
    ) -> list[AdminSession]:

        statement = select(AdminSession).where(
            AdminSession.user_id == user_id
        )

        if not include_revoked:
            statement = statement.where(
                AdminSession.revoked_at.is_(None)
            )

        statement = statement.order_by(
            AdminSession.created_at.desc()
        )

        return list(
            self.db.scalars(statement).all()
        )

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        session: AdminSession,
        data: dict,
    ) -> AdminSession:

        for field, value in data.items():
            setattr(session, field, value)

        self.db.flush()
        self.db.refresh(session)

        return session

    # ---------------------------------------------------------
    # REVOKE
    # ---------------------------------------------------------

    def revoke(
        self,
        session: AdminSession,
    ) -> AdminSession:

        session.revoked_at = datetime.now(timezone.utc)

        self.db.flush()
        self.db.refresh(session)

        return session

    # ---------------------------------------------------------
    # REVOKE ALL USER SESSIONS
    # ---------------------------------------------------------

    def revoke_all_for_user(
        self,
        user_id: int,
    ) -> int:

        sessions = self.list_by_user_id(
            user_id,
            include_revoked=False,
        )

        now = datetime.now(timezone.utc)

        for session in sessions:
            session.revoked_at = now

        self.db.flush()

        return len(sessions)

    # ---------------------------------------------------------
    # UPDATE LAST USED
    # ---------------------------------------------------------

    def update_last_used(
        self,
        session: AdminSession,
    ) -> AdminSession:

        session.last_used_at = datetime.now(timezone.utc)

        self.db.flush()
        self.db.refresh(session)

        return session

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        session: AdminSession,
    ) -> None:

        self.db.delete(session)
        self.db.flush()