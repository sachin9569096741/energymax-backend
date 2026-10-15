from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_session import AffiliateSession


class AffiliateAuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Affiliate | None:
        return self.db.scalar(
            select(Affiliate)
            .where(Affiliate.email == email)
            .limit(1)
        )

    def get_by_public_id(self, public_id: str) -> Affiliate | None:
        return self.db.scalar(
            select(Affiliate).where(
                Affiliate.public_id == public_id
            )
        )

    def get_by_activation_hash(
        self, token_hash: str
    ) -> Affiliate | None:
        return self.db.scalar(
            select(Affiliate)
            .where(Affiliate.activation_token_hash == token_hash)
            .with_for_update()
        )

    def create_session(
        self, session: AffiliateSession
    ) -> AffiliateSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_session_by_hash(
        self, token_hash: str
    ) -> AffiliateSession | None:
        return self.db.scalar(
            select(AffiliateSession)
            .options(joinedload(AffiliateSession.affiliate))
            .where(AffiliateSession.token_hash == token_hash)
        )

    def revoke_session(self, token_hash: str) -> bool:
        session = self.get_session_by_hash(token_hash)

        if session is None or not session.is_active:
            return False

        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)
        self.db.flush()
        return True