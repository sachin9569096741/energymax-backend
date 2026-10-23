from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_commision_policy import (
    AffiliateCommissionPolicy,
)
from app.modules.affiliate.schemas.commission import (
    CommissionPolicyCreate,
)


class CommissionPolicyService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise HTTPException(
                status_code=422,
                detail="Policy dates must include a timezone.",
            )
        return value.astimezone(timezone.utc)

    def create_policy(
        self,
        payload: CommissionPolicyCreate,
        admin_id: int,
    ) -> AffiliateCommissionPolicy:
        start = self._utc(payload.effective_from)
        end = (
            self._utc(payload.effective_until)
            if payload.effective_until is not None
            else None
        )

        affiliate_id = None

        if payload.affiliate_public_id is not None:
            affiliate = self.db.scalar(
                select(Affiliate).where(
                    Affiliate.public_id == payload.affiliate_public_id
                )
            )

            if affiliate is None:
                raise HTTPException(
                    status_code=404,
                    detail="Affiliate not found.",
                )

            affiliate_id = affiliate.id

        # Reject overlapping active policies in the same scope.
        # Global policies and affiliate-specific policies are separate scopes.
        conditions = [
            AffiliateCommissionPolicy.is_active.is_(True),
            AffiliateCommissionPolicy.affiliate_id == affiliate_id,
            or_(
                AffiliateCommissionPolicy.effective_until.is_(None),
                AffiliateCommissionPolicy.effective_until > start,
            ),
        ]

        if end is not None:
            conditions.append(
                AffiliateCommissionPolicy.effective_from < end
            )

        overlap = self.db.scalar(
            select(AffiliateCommissionPolicy.id)
            .where(*conditions)
            .limit(1)
        )

        if overlap is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An active commission policy already overlaps "
                    "this date range for the selected scope. "
                    "Deactivate or adjust the existing policy first."
                ),
            )

        policy = AffiliateCommissionPolicy(
            affiliate_id=affiliate_id,
            commission_rate=payload.commission_rate,
            is_active=True,
            effective_from=start,
            effective_until=end,
            created_by_admin_id=admin_id,
        )

        self.db.add(policy)
        self.db.flush()
        return policy

    def list_policies(
        self,
        *,
        affiliate_public_id: str | None = None,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AffiliateCommissionPolicy]:
        query = select(AffiliateCommissionPolicy)

        if affiliate_public_id is not None:
            affiliate = self.db.scalar(
                select(Affiliate).where(
                    Affiliate.public_id == affiliate_public_id
                )
            )

            if affiliate is None:
                raise HTTPException(
                    status_code=404,
                    detail="Affiliate not found.",
                )

            query = query.where(
                AffiliateCommissionPolicy.affiliate_id == affiliate.id
            )
        # When no affiliate filter is supplied, return global and
        # affiliate-specific policies.

        if active_only:
            query = query.where(
                AffiliateCommissionPolicy.is_active.is_(True)
            )

        query = query.order_by(
            AffiliateCommissionPolicy.effective_from.desc(),
            AffiliateCommissionPolicy.id.desc(),
        ).limit(limit).offset(offset)

        return list(self.db.scalars(query).all())

    def deactivate_policy(
        self,
        public_id: str,
    ) -> AffiliateCommissionPolicy:
        policy = self.db.scalar(
            select(AffiliateCommissionPolicy).where(
                AffiliateCommissionPolicy.public_id == public_id
            )
        )

        if policy is None:
            raise HTTPException(
                status_code=404,
                detail="Commission policy not found.",
            )

        if not policy.is_active:
            raise HTTPException(
                status_code=409,
                detail="Commission policy is already inactive.",
            )

        policy.is_active = False
        self.db.flush()
        return policy