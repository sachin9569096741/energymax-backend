from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate


class AffiliateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **values) -> Affiliate:
        affiliate = Affiliate(**values)
        self.db.add(affiliate)
        self.db.flush()
        return affiliate

    def get_by_email(self, email: str) -> Affiliate | None:
        return self.db.scalar(
            select(Affiliate).where(Affiliate.email == email)
        )

    def get_by_code(self, code: str) -> Affiliate | None:
        return self.db.scalar(
            select(Affiliate).where(Affiliate.public_code == code)
        )

    def list(
        self,
        status_filter: str | None,
        limit: int,
        offset: int,
    ) -> list[Affiliate]:
        query = select(Affiliate)

        if status_filter:
            query = query.where(Affiliate.status == status_filter)

        query = (
            query
            .order_by(Affiliate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(query).all())