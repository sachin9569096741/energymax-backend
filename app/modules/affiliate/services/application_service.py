import secrets
import string
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_application import (
    AffiliateApplication,
)
from app.modules.affiliate.repositories.affiliate_repo import (
    AffiliateRepository,
)
from app.modules.affiliate.repositories.application_repo import (
    AffiliateApplicationRepository,
)
from app.modules.shop.customer.models.customer import Customer
from app.modules.affiliate.schemas.application import (
    AffiliateApplicationCreate,
)


class AffiliateApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.applications = AffiliateApplicationRepository(db)
        self.affiliates = AffiliateRepository(db)

    def submit(
        self, payload: AffiliateApplicationCreate
    ) -> AffiliateApplication:
        email = str(payload.email).strip().lower()

        existing_pending = self.applications.get_pending_by_email(email)
        if existing_pending:
            raise HTTPException(
                status_code=409,
                detail="A pending affiliate application already exists for this email.",
            )

        if self.affiliates.get_by_email(email):
            raise HTTPException(
                status_code=409,
                detail="An affiliate account already exists for this email.",
            )

        return self.applications.create(
            full_name=payload.full_name.strip(),
            email=email,
            phone=payload.phone,
            promotion_channels=payload.promotion_channels.strip(),
            audience_description=payload.audience_description,
            website_url=(
                str(payload.website_url)
                if payload.website_url
                else None
            ),
            status="pending",
        )

    def list_applications(
        self,
        status_filter: str | None,
        limit: int,
        offset: int,
    ) -> list[AffiliateApplication]:
        if status_filter and status_filter not in {
            "pending", "approved", "rejected"
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid application status filter.",
            )
        return self.applications.list(status_filter, limit, offset)

    def approve(
        self, public_id: str, admin_id: int
    ) -> Affiliate:
        application = self.applications.get_by_public_id_for_update(public_id)
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Affiliate application not found.",
            )

        if application.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Only pending applications can be approved.",
            )

        if self.affiliates.get_by_email(application.email):
            raise HTTPException(
                status_code=409,
                detail="An affiliate account already exists for this email.",
            )

        customer = self.db.scalar(
            select(Customer).where(
                Customer.email == application.email
            )
        )

        code = self._generate_unique_code(application.full_name)
        now = datetime.now(timezone.utc)

        application.status = "approved"
        application.reviewed_by_admin_id = admin_id
        application.reviewed_at = now
        application.decision_reason = None

        affiliate = self.affiliates.create(
            application_id=application.id,
            customer_id=customer.id if customer else None,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            public_code=code,
            status="active",
            approved_by_admin_id=admin_id,
            approved_at=now,
        )

        self.db.flush()
        return affiliate

    def reject(
        self,
        public_id: str,
        admin_id: int,
        reason: str | None,
    ) -> AffiliateApplication:
        application = self.applications.get_by_public_id_for_update(public_id)
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Affiliate application not found.",
            )

        if application.status != "pending":
            raise HTTPException(
                status_code=409,
                detail="Only pending applications can be rejected.",
            )

        application.status = "rejected"
        application.reviewed_by_admin_id = admin_id
        application.reviewed_at = datetime.now(timezone.utc)
        application.decision_reason = (
            reason.strip() if reason and reason.strip() else None
        )

        self.db.flush()
        return application

    def list_affiliates(
        self,
        status_filter: str | None,
        limit: int,
        offset: int,
    ) -> list[Affiliate]:
        if status_filter and status_filter not in {
            "active", "suspended", "closed"
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid affiliate status filter.",
            )
        return self.affiliates.list(status_filter, limit, offset)

    def _generate_unique_code(self, full_name: str) -> str:
        stem = "".join(
            ch for ch in full_name.upper() if ch.isalnum()
        )[:8] or "ENERGY"

        alphabet = string.ascii_uppercase + string.digits

        for _ in range(12):
            suffix = "".join(
                secrets.choice(alphabet) for _ in range(6)
            )
            candidate = f"{stem}{suffix}"[:32]

            if self.affiliates.get_by_code(candidate) is None:
                return candidate

        raise HTTPException(
            status_code=503,
            detail="Could not generate a unique affiliate code. Please retry.",
        )