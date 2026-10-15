from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate_application import (
    AffiliateApplication,
)


class AffiliateApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **values) -> AffiliateApplication:
        application = AffiliateApplication(**values)
        self.db.add(application)
        self.db.flush()
        return application

    def get_by_public_id(
        self, public_id: str
    ) -> AffiliateApplication | None:
        return self.db.scalar(
            select(AffiliateApplication).where(
                AffiliateApplication.public_id == public_id
            )
        )

    def get_by_public_id_for_update(
        self, public_id: str
    ) -> AffiliateApplication | None:
        stmt = (
            select(AffiliateApplication)
            .where(AffiliateApplication.public_id == public_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def get_pending_by_email(
        self, email: str
    ) -> AffiliateApplication | None:
        return self.db.scalar(
            select(AffiliateApplication).where(
                AffiliateApplication.email == email,
                AffiliateApplication.status == "pending",
            )
        )

    def list(
        self,
        status_filter: str | None,
        limit: int,
        offset: int,
    ) -> list[AffiliateApplication]:
        query = select(AffiliateApplication)

        if status_filter:
            query = query.where(
                AffiliateApplication.status == status_filter
            )

        query = (
            query
            .order_by(AffiliateApplication.submitted_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(query).all())